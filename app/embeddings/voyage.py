"""Embeddings from the Voyage AI REST API."""

import json
import logging
import random
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from typing import Literal

from app.embeddings.base import batched

logger = logging.getLogger(__name__)

API_URL = "https://api.voyageai.com/v1/embeddings"
_RETRYABLE = {429, 500, 502, 503, 504}

InputType = Literal["document", "query"]


class VoyageError(RuntimeError):
    pass


class VoyageEmbedder:
    def __init__(
        self,
        api_key: str,
        model: str = "voyage-4",
        dimensions: int = 1024,
        batch_size: int = 64,
        timeout: float = 60,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise VoyageError(
                "VOYAGE_API_KEY is not set. Add it to .env, or set EMBEDDING_PROVIDER=fake."
            )
        self._api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries
        self._sleep = sleep
        self.tokens_used = 0

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(texts, self.batch_size):
            vectors.extend(self._embed_batch(batch, "document"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text], "query")[0]

    def _embed_batch(self, texts: Sequence[str], input_type: InputType) -> list[list[float]]:
        payload = {
            "input": list(texts),
            "model": self.model,
            "input_type": input_type,
            "output_dimension": self.dimensions,
        }
        body = self._post(payload)
        items = sorted(body["data"], key=lambda item: item["index"])
        if len(items) != len(texts):
            raise VoyageError(f"asked for {len(texts)} embeddings, got {len(items)}")
        vectors = [item["embedding"] for item in items]
        if any(len(v) != self.dimensions for v in vectors):
            raise VoyageError(f"expected vectors of length {self.dimensions}")
        self.tokens_used += body.get("usage", {}).get("total_tokens", 0)
        return vectors

    def _post(self, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(
                API_URL,
                data=data,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    raise VoyageError("Voyage rejected the API key (HTTP 401)") from exc
                if exc.code not in _RETRYABLE or attempt == self.max_retries:
                    detail = exc.read().decode("utf-8", errors="replace")[:300]
                    raise VoyageError(f"Voyage API error HTTP {exc.code}: {detail}") from exc
                delay = self._retry_delay(attempt, exc.headers.get("Retry-After"))
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == self.max_retries:
                    raise VoyageError(f"cannot reach the Voyage API: {exc}") from exc
                delay = self._retry_delay(attempt, None)
            logger.warning("Voyage request failed, retrying in %.1fs", delay)
            self._sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _retry_delay(attempt: int, retry_after: str | None) -> float:
        if retry_after and retry_after.isdigit():
            return float(retry_after)
        # Exponential backoff with jitter: 1s, 2s, 4s, ... plus up to 1s of randomness, so
        # that many clients failing at once do not all retry at the same moment.
        return min(2**attempt, 30) + random.random()
