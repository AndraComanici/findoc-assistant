"""A deterministic embedder for tests and offline work. No network, no model download.

Each word is hashed to a position in the vector, so texts that share words get similar
vectors. This is a crude bag-of-words, not a language model: it does not know that
"profit" and "câștig" mean similar things. It exists so that the rest of the pipeline can
be tested quickly and without cost.
"""

import hashlib
import math
import re
from collections.abc import Sequence

_WORD = re.compile(r"\w+")


class FakeEmbedder:
    def __init__(self, dimensions: int = 256, model: str = "fake-bag-of-words") -> None:
        self.dimensions = dimensions
        self.model = model

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in _WORD.findall(text.lower()):
            digest = hashlib.blake2b(word.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm else vector

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
