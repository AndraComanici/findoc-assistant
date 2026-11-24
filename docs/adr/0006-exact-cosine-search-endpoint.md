# 0006. Exact cosine search, filtered by model, company and year

- Status: accepted
- Date: 2026-11-24

## Context

The first user-facing feature: given a question, return the passages closest in meaning, with
company, year and page, so that later an LLM can answer from them and cite the page. The corpus
has about 6,100 vectors of 1,024 dimensions. Users will often ask about one company or year.

## Decision

- Embed the question with `input_type="query"` and rank chunks by pgvector's cosine distance
  (`<=>`), returning `1 - distance` as the score. Return the top `k` (default 5, at most 20).
- Compare every vector (exact search), without an approximate index.
- Compare only vectors produced by the current embedding model.
- Optional filters on ticker and year are applied in the same SQL query.
- Expose `GET /search` in FastAPI, with input validated before any external call. A failure of
  the embedding service returns HTTP 502; invalid input returns 422.
- Open one database connection per request.

## Alternatives considered

- **An HNSW index.** Approximate nearest-neighbour search is much faster on millions of vectors,
  but may miss some true neighbours and makes filtered queries harder to get right. At 6,100
  vectors exact search takes milliseconds; an index is added only if latency is measured to be a
  problem. Ordering by the distance expression keeps that option open.
- **Filtering in Python after the search.** Simpler SQL, but `k` results could all be filtered
  out, leaving none.
- **A connection pool.** Avoids opening a connection per request; not worth a dependency at
  this traffic.

## Consequences

- Results are exact and reproducible for a given model.
- Each search makes one call to the embedding API; on Voyage's free trial that is limited to
  3 requests per minute, shared with indexing.
- Scores are only comparable between results of the same model.
