"""Compute and store an embedding for every chunk that does not have one yet.

Work is done in small batches, each committed on its own. Interrupting the process loses at
most one batch, and running it again continues where it stopped.
"""

import logging
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import psycopg

from app.embeddings.base import Embedder
from app.embeddings.ratelimit import RateLimiter

logger = logging.getLogger(__name__)

# Romanian text averages roughly 3.5-4 characters per token. Dividing by 3 over-estimates on
# purpose, so batches stay under the per-minute token quota.
CHARS_PER_TOKEN = 3


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def to_vector_literal(vector: Sequence[float]) -> str:
    """pgvector accepts vectors written as text: '[0.1,-0.2,...]'."""
    return "[" + ",".join(f"{x:.7g}" for x in vector) + "]"


@dataclass(frozen=True)
class Row:
    id: int
    content: str


def plan_batches(rows: Sequence[Row], max_texts: int, max_tokens: int) -> list[list[Row]]:
    """Group rows in order, so that each batch has at most max_texts rows and max_tokens tokens."""
    batches: list[list[Row]] = []
    current: list[Row] = []
    tokens = 0
    for row in rows:
        size = estimate_tokens(row.content)
        if current and (len(current) == max_texts or tokens + size > max_tokens):
            batches.append(current)
            current, tokens = [], 0
        current.append(row)
        tokens += size
    if current:
        batches.append(current)
    return batches


@dataclass
class Progress:
    done: int
    total: int
    tokens: int
    elapsed: float

    @property
    def remaining_seconds(self) -> float | None:
        if self.done == 0:
            return None
        return self.elapsed / self.done * (self.total - self.done)


_PENDING = "embedding IS NULL OR embedding_model IS DISTINCT FROM %(model)s"


def count_pending(conn: psycopg.Connection, model: str) -> int:
    return conn.execute(
        f"SELECT count(*) FROM chunks WHERE {_PENDING}", {"model": model}
    ).fetchone()[0]


def embed_pending(
    conn: psycopg.Connection,
    embedder: Embedder,
    limiter: RateLimiter,
    max_texts: int,
    limit: int | None = None,
    on_progress: Callable[[Progress], None] | None = None,
) -> Progress:
    """Embed chunks with no vector, or with a vector from a different model.

    The connection must be in autocommit mode, so that each batch is committed as soon as its
    own transaction ends instead of being held in one long transaction until the very end.
    """
    if not conn.autocommit:
        raise ValueError("embed_pending needs a connection opened with autocommit=True")
    total = count_pending(conn, embedder.model)
    if limit is not None:
        total = min(total, limit)
    # A request must fit in the per-minute quota on its own; keep a 10% safety margin.
    max_tokens = int(limiter.tokens_per_minute * 0.9)
    progress = Progress(done=0, total=total, tokens=0, elapsed=0.0)
    started = time.monotonic()

    while progress.done < total:
        rows = [
            Row(*r)
            for r in conn.execute(
                f"SELECT id, content FROM chunks WHERE {_PENDING} ORDER BY id LIMIT %(n)s",
                {"model": embedder.model, "n": min(500, total - progress.done)},
            ).fetchall()
        ]
        if not rows:
            break
        for batch in plan_batches(rows, max_texts, max_tokens):
            tokens = sum(estimate_tokens(r.content) for r in batch)
            limiter.acquire(tokens)
            vectors = embedder.embed_documents([r.content for r in batch])
            if any(len(v) != embedder.dimensions for v in vectors):
                raise ValueError("embedding dimensions do not match the configured dimensions")
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.executemany(
                        "UPDATE chunks SET embedding = %s::vector, embedding_model = %s, "
                        "embedded_at = now() WHERE id = %s",
                        [
                            (to_vector_literal(v), embedder.model, r.id)
                            for r, v in zip(batch, vectors, strict=True)
                        ],
                    )
            progress.done += len(batch)
            progress.tokens += tokens
            progress.elapsed = time.monotonic() - started
            if on_progress:
                on_progress(progress)
    return progress
