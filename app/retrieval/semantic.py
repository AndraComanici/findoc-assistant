"""Semantic search: rank chunks by the cosine similarity of their embedding to the question's."""

from collections.abc import Sequence
from dataclasses import dataclass

import psycopg

from app.embeddings.indexer import to_vector_literal


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    source_id: str
    company: str
    ticker: str
    year: int
    page_number: int
    content: str
    score: float  # cosine similarity: 1 = same direction, 0 = unrelated


# `<=>` is pgvector's cosine distance (1 - cosine similarity). Ordering by the distance itself,
# rather than by the computed score, lets PostgreSQL use a vector index if one is added later.
# Only vectors from the current model are compared: vectors from different models live in
# different spaces and their similarity would be meaningless.
_SQL = """
SELECT c.id, d.source_id, d.company, d.ticker, d.year, c.page_number, c.content,
       1 - (c.embedding <=> %(query)s::vector) AS score
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.embedding_model = %(model)s
  AND (%(ticker)s::text IS NULL OR d.ticker = %(ticker)s)
  AND (%(year)s::int IS NULL OR d.year = %(year)s)
ORDER BY c.embedding <=> %(query)s::vector
LIMIT %(k)s
"""


def semantic_search(
    conn: psycopg.Connection,
    query_vector: Sequence[float],
    model: str,
    k: int = 5,
    ticker: str | None = None,
    year: int | None = None,
) -> list[SearchHit]:
    rows = conn.execute(
        _SQL,
        {
            "query": to_vector_literal(query_vector),
            "model": model,
            "ticker": ticker,
            "year": year,
            "k": k,
        },
    ).fetchall()
    return [SearchHit(*row) for row in rows]
