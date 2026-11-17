"""Write documents and their chunks to PostgreSQL."""

from enum import StrEnum

import psycopg

from app.ingestion.chunking import Chunk
from app.ingestion.sources import Source


class StoreResult(StrEnum):
    INSERTED = "inserted"
    REPLACED = "replaced"
    UNCHANGED = "unchanged"


def is_unchanged(conn: psycopg.Connection, source_id: str, sha256: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM documents WHERE source_id = %s AND file_sha256 = %s", (source_id, sha256)
    ).fetchone()
    return row is not None


def store_document(
    conn: psycopg.Connection,
    source: Source,
    sha256: str,
    page_count: int,
    chunks: list[Chunk],
    force: bool = False,
) -> StoreResult:
    """Insert or replace a document and all its chunks in a single transaction.

    If a document with the same id and the same file hash is already stored, nothing is
    written unless force is set. Running ingestion twice therefore gives the same result.
    """
    with conn.transaction():
        row = conn.execute(
            "SELECT id, file_sha256 FROM documents WHERE source_id = %s FOR UPDATE",
            (source.id,),
        ).fetchone()
        if row is not None and row[1] == sha256 and not force:
            return StoreResult.UNCHANGED

        document_id = conn.execute(
            """
            INSERT INTO documents
                (source_id, company, ticker, year, title, source_url, file_sha256, page_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id) DO UPDATE SET
                company = EXCLUDED.company,
                ticker = EXCLUDED.ticker,
                year = EXCLUDED.year,
                title = EXCLUDED.title,
                source_url = EXCLUDED.source_url,
                file_sha256 = EXCLUDED.file_sha256,
                page_count = EXCLUDED.page_count,
                ingested_at = now()
            RETURNING id
            """,
            (
                source.id,
                source.company,
                source.ticker,
                source.year,
                source.title,
                str(source.url) if source.url else None,
                sha256,
                page_count,
            ),
        ).fetchone()[0]

        conn.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
        with conn.cursor() as cur:
            with cur.copy(
                "COPY chunks (document_id, chunk_index, page_number, content, word_count) "
                "FROM STDIN"
            ) as copy:
                for chunk in chunks:
                    copy.write_row(
                        (document_id, chunk.index, chunk.page_number, chunk.text, chunk.word_count)
                    )
    return StoreResult.INSERTED if row is None else StoreResult.REPLACED
