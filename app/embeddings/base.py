"""The interface every embedding provider implements."""

import math
from collections.abc import Iterator, Sequence
from typing import Protocol


class Embedder(Protocol):
    """Turns text into fixed-length vectors.

    Documents and queries are embedded through separate methods because retrieval models
    may treat them differently: a question and the passage that answers it are not
    phrased alike.
    """

    model: str
    dimensions: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """1.0 for vectors pointing the same way, 0.0 for unrelated ones."""
    if len(a) != len(b):
        raise ValueError(f"vectors have different lengths: {len(a)} and {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def batched(items: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    if size < 1:
        raise ValueError("batch size must be at least 1")
    for start in range(0, len(items), size):
        yield items[start : start + size]
