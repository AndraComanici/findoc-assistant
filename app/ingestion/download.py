"""Download source PDFs that are not yet on disk."""

import logging
import urllib.request
from pathlib import Path

from app.ingestion.sources import Source

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF-"


def download_missing(sources: list[Source], data_dir: Path, timeout: float = 60) -> list[str]:
    """Download every source that has a URL and no local file. Returns the ids downloaded."""
    data_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    for source in sources:
        target = source.path(data_dir)
        if target.exists():
            continue
        if source.url is None:
            logger.warning("%s: no URL and no local file %s; skipping", source.id, target)
            continue
        request = urllib.request.Request(
            str(source.url), headers={"User-Agent": "findoc-assistant/0.1"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
        if not body.startswith(_PDF_MAGIC):
            raise ValueError(f"{source.id}: {source.url} did not return a PDF")
        # Write to a temporary name first so an interrupted download never looks complete.
        partial = target.with_suffix(".part")
        partial.write_bytes(body)
        partial.replace(target)
        logger.info("%s: downloaded %d bytes", source.id, len(body))
        downloaded.append(source.id)
    return downloaded
