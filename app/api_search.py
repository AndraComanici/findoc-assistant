"""The /search endpoint."""

import logging
from collections.abc import Callable
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.embeddings import Embedder, get_embedder
from app.retrieval.semantic import SearchHit, semantic_search

logger = logging.getLogger(__name__)

router = APIRouter()

# A function that runs the search; injected so that tests can replace the database.
Searcher = Callable[..., list[SearchHit]]


def embedder_dependency(settings: Annotated[Settings, Depends(get_settings)]) -> Embedder:
    return get_embedder(settings)


def searcher_dependency(settings: Annotated[Settings, Depends(get_settings)]) -> Searcher:
    def search(**kwargs) -> list[SearchHit]:
        # One short-lived connection per request keeps things simple at this traffic level;
        # a connection pool is the next step if the API gets busy.
        with psycopg.connect(settings.database_url) as conn:
            return semantic_search(conn, **kwargs)

    return search


class SearchResult(BaseModel):
    score: float
    company: str
    ticker: str
    year: int
    page: int
    source_id: str
    chunk_id: int
    text: str


class SearchResponse(BaseModel):
    query: str
    model: str
    results: list[SearchResult]


@router.get("/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(min_length=3, max_length=500, description="The question")],
    embedder: Annotated[Embedder, Depends(embedder_dependency)],
    searcher: Annotated[Searcher, Depends(searcher_dependency)],
    k: Annotated[int, Query(ge=1, le=20, description="How many passages to return")] = 5,
    ticker: Annotated[
        str | None, Query(pattern=r"^[A-Z0-9]{1,6}$", description="e.g. TLV, H2O, M")
    ] = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> SearchResponse:
    """Return the passages whose meaning is closest to the question, best first."""
    try:
        query_vector = embedder.embed_query(q)
    except Exception as exc:
        logger.warning("embedding the query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="the embedding service is unavailable, try again shortly",
        ) from exc

    hits = searcher(query_vector=query_vector, model=embedder.model, k=k, ticker=ticker, year=year)
    return SearchResponse(
        query=q,
        model=embedder.model,
        results=[
            SearchResult(
                score=round(h.score, 4),
                company=h.company,
                ticker=h.ticker,
                year=h.year,
                page=h.page_number,
                source_id=h.source_id,
                chunk_id=h.chunk_id,
                text=h.content,
            )
            for h in hits
        ],
    )
