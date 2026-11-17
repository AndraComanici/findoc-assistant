"""Tests that need a real PostgreSQL with pgvector. Run with TEST_DATABASE_URL set."""

import os
import shutil
from pathlib import Path

import psycopg
import pytest

from app.ingestion.pipeline import ingest
from app.ingestion.sources import Source
from app.ingestion.store import StoreResult
from app.migrations import migrate

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATIONS = Path(__file__).parents[2] / "db" / "migrations"

if DATABASE_URL is None:
    pytest.skip("TEST_DATABASE_URL is not set", allow_module_level=True)


@pytest.fixture
def db() -> str:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks, documents, schema_migrations")
    migrate(DATABASE_URL, MIGRATIONS)
    return DATABASE_URL


@pytest.fixture
def data_dir(tmp_path, sample_pdf) -> Path:
    shutil.copy(sample_pdf, tmp_path / "ex-2025.pdf")
    return tmp_path


SOURCE = Source(
    id="ex-2025", company="Exemplu", ticker="EX", year=2025, title="Raport", file="ex-2025.pdf"
)


def count_chunks(url: str) -> int:
    with psycopg.connect(url) as conn:
        return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]


def test_migrations_run_once(db):
    assert migrate(db, MIGRATIONS) == []


def test_ingest_stores_chunks_with_pages(db, data_dir):
    result = ingest(db, [SOURCE], data_dir, max_words=200, overlap_words=40)

    assert result == {"ex-2025": StoreResult.INSERTED}
    with psycopg.connect(db) as conn:
        rows = conn.execute(
            "SELECT chunk_index, page_number FROM chunks ORDER BY chunk_index"
        ).fetchall()
        page_count = conn.execute("SELECT page_count FROM documents").fetchone()[0]
    assert rows == [(0, 1), (1, 3)]
    assert page_count == 3


def test_ingesting_the_same_file_twice_changes_nothing(db, data_dir):
    ingest(db, [SOURCE], data_dir, max_words=200, overlap_words=40)
    result = ingest(db, [SOURCE], data_dir, max_words=200, overlap_words=40)

    assert result == {"ex-2025": StoreResult.UNCHANGED}
    assert count_chunks(db) == 2


def test_force_replaces_chunks_instead_of_duplicating_them(db, data_dir):
    ingest(db, [SOURCE], data_dir, max_words=200, overlap_words=40)
    result = ingest(db, [SOURCE], data_dir, max_words=5, overlap_words=0, force=True)

    assert result == {"ex-2025": StoreResult.REPLACED}
    with psycopg.connect(db) as conn:
        indexes = [r[0] for r in conn.execute("SELECT chunk_index FROM chunks ORDER BY 1")]
    assert indexes == list(range(len(indexes)))
    assert len(indexes) > 2


def test_missing_files_fail_before_anything_is_written(db, tmp_path):
    with pytest.raises(FileNotFoundError, match="ex-2025"):
        ingest(db, [SOURCE], tmp_path, max_words=200, overlap_words=40)
    assert count_chunks(db) == 0
