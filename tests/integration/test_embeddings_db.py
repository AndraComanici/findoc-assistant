"""Embedding storage against a real PostgreSQL with pgvector. Run with TEST_DATABASE_URL set."""

import os
import shutil
from pathlib import Path

import psycopg
import pytest

from app.embeddings.fake import FakeEmbedder
from app.embeddings.indexer import count_pending, embed_pending
from app.embeddings.ratelimit import RateLimiter
from app.ingestion.pipeline import ingest
from app.ingestion.sources import Source
from app.migrations import migrate

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATIONS = Path(__file__).parents[2] / "db" / "migrations"

if DATABASE_URL is None:
    pytest.skip("TEST_DATABASE_URL is not set", allow_module_level=True)

SOURCE = Source(
    id="ex-2025", company="Exemplu", ticker="EX", year=2025, title="Raport", file="ex-2025.pdf"
)


@pytest.fixture
def db(tmp_path, sample_pdf) -> str:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks, documents, schema_migrations")
    migrate(DATABASE_URL, MIGRATIONS)
    shutil.copy(sample_pdf, tmp_path / "ex-2025.pdf")
    ingest(DATABASE_URL, [SOURCE], tmp_path, max_words=10, overlap_words=0)
    return DATABASE_URL


def run(url: str, embedder: FakeEmbedder, limit: int | None = None):
    no_wait = RateLimiter(1000, 1_000_000, sleep=lambda s: None)
    with psycopg.connect(url, autocommit=True) as conn:
        return embed_pending(conn, embedder, no_wait, max_texts=2, limit=limit)


def test_every_chunk_gets_a_vector_and_the_model_name(db):
    embedder = FakeEmbedder(dimensions=1024)
    result = run(db, embedder)

    with psycopg.connect(db) as conn:
        rows = conn.execute("SELECT embedding_model, vector_dims(embedding) FROM chunks").fetchall()
    assert result.done == len(rows) > 2
    assert set(rows) == {("fake-bag-of-words", 1024)}


def test_a_second_run_has_nothing_to_do(db):
    embedder = FakeEmbedder(dimensions=1024)
    run(db, embedder)
    assert run(db, embedder).done == 0


def test_an_interrupted_run_resumes_where_it_stopped(db):
    embedder = FakeEmbedder(dimensions=1024)
    first = run(db, embedder, limit=2)
    with psycopg.connect(db) as conn:
        left = count_pending(conn, embedder.model)
    second = run(db, embedder)
    assert first.done == 2
    assert second.done == left > 0


def test_changing_the_model_marks_every_chunk_for_re_embedding(db):
    run(db, FakeEmbedder(dimensions=1024))
    other = FakeEmbedder(dimensions=1024, model="another-model")
    with psycopg.connect(db) as conn:
        assert count_pending(conn, "another-model") > 0
    run(db, other)
    with psycopg.connect(db) as conn:
        models = {r[0] for r in conn.execute("SELECT DISTINCT embedding_model FROM chunks")}
    assert models == {"another-model"}


def test_a_vector_without_a_model_is_rejected_by_the_database(db):
    with psycopg.connect(db) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE chunks SET embedding = %s::vector WHERE chunk_index = 0",
                ("[" + ",".join(["0"] * 1024) + "]",),
            )


def test_wrong_dimensions_are_rejected_before_writing(db):
    with pytest.raises(ValueError, match="dimensions"):
        run(db, _WrongSize())


class _WrongSize(FakeEmbedder):
    def __init__(self) -> None:
        super().__init__(dimensions=1024, model="wrong")

    def embed_documents(self, texts):
        return [[0.0] * 3 for _ in texts]
