"""Semantic search against a real PostgreSQL with pgvector. Run with TEST_DATABASE_URL set."""

import os
import shutil
from pathlib import Path

import psycopg
import pytest

from app.embeddings.fake import FakeEmbedder
from app.embeddings.indexer import embed_pending
from app.embeddings.ratelimit import RateLimiter
from app.ingestion.pipeline import ingest
from app.ingestion.sources import Source
from app.migrations import migrate
from app.retrieval.semantic import semantic_search

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATIONS = Path(__file__).parents[2] / "db" / "migrations"

if DATABASE_URL is None:
    pytest.skip("TEST_DATABASE_URL is not set", allow_module_level=True)

EMBEDDER = FakeEmbedder(dimensions=1024)


@pytest.fixture(scope="module")
def db(tmp_path_factory) -> str:
    sample = Path(__file__).parents[1] / "fixtures" / "sample-report.pdf"
    data_dir = tmp_path_factory.mktemp("raw")
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks, documents, schema_migrations")
    migrate(DATABASE_URL, MIGRATIONS)
    sources = []
    for ticker, year in [("EX", 2024), ("EX", 2025), ("OT", 2025)]:
        source_id = f"{ticker.lower()}-{year}"
        shutil.copy(sample, data_dir / f"{source_id}.pdf")
        sources.append(
            Source(
                id=source_id,
                company=f"Company {ticker}",
                ticker=ticker,
                year=year,
                title="Raport",
                file=f"{source_id}.pdf",
            )
        )
    ingest(DATABASE_URL, sources, data_dir, max_words=12, overlap_words=0)
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        embed_pending(conn, EMBEDDER, RateLimiter(1000, 10**7, sleep=lambda s: None), 16)
    return DATABASE_URL


def search(db: str, question: str, **kwargs):
    with psycopg.connect(db) as conn:
        return semantic_search(conn, EMBEDDER.embed_query(question), EMBEDDER.model, **kwargs)


def test_the_closest_passage_comes_first_with_its_page(db):
    hits = search(db, "dividende din profitul net", k=3)

    assert len(hits) == 3
    assert "dividende" in hits[0].content
    assert hits[0].page_number == 3
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_filters_by_company_and_year(db):
    hits = search(db, "profitul net", k=20, ticker="EX", year=2025)

    assert hits
    assert {(h.ticker, h.year) for h in hits} == {("EX", 2025)}


def test_an_unknown_company_returns_nothing(db):
    assert search(db, "profitul net", ticker="ZZZ") == []


def test_vectors_from_another_model_are_ignored(db):
    with psycopg.connect(db) as conn:
        assert semantic_search(conn, EMBEDDER.embed_query("profit"), "another-model") == []
