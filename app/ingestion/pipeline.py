"""Ingest source documents: extract, normalise, chunk and store."""

import logging
from pathlib import Path

import psycopg

from app.ingestion.chunking import chunk_document
from app.ingestion.pdf import extract_pages, file_sha256
from app.ingestion.sources import Source
from app.ingestion.store import StoreResult, is_unchanged, store_document

logger = logging.getLogger(__name__)


def ingest(
    database_url: str,
    sources: list[Source],
    data_dir: Path,
    max_words: int,
    overlap_words: int,
    force: bool = False,
) -> dict[str, StoreResult]:
    results: dict[str, StoreResult] = {}
    missing = [s.id for s in sources if not s.path(data_dir).exists()]
    if missing:
        raise FileNotFoundError(
            f"missing PDF files in {data_dir} for: {', '.join(missing)}. "
            "Download them first (see README)."
        )

    with psycopg.connect(database_url) as conn:
        for source in sources:
            path = source.path(data_dir)
            sha256 = file_sha256(path)
            # Cheap check first: skip PDF parsing entirely when the file has not changed.
            if not force and is_unchanged(conn, source.id, sha256):
                logger.info("%s: unchanged, skipped", source.id)
                results[source.id] = StoreResult.UNCHANGED
                continue
            pages = extract_pages(path)
            chunks = chunk_document(pages, max_words, overlap_words)
            empty_pages = sum(1 for p in pages if not p.text.strip())
            if empty_pages:
                # Usually scanned pages (images) or pages that are only charts.
                logger.warning(
                    "%s: %d of %d pages have no text", source.id, empty_pages, len(pages)
                )
            result = store_document(conn, source, sha256, len(pages), chunks, force)
            logger.info("%s: %s, %d pages, %d chunks", source.id, result, len(pages), len(chunks))
            results[source.id] = result
    return results
