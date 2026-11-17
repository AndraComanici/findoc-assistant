"""Download source PDFs that are not yet on disk."""

import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from app.ingestion.sources import Source

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF-"


@dataclass
class DownloadReport:
    downloaded: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)  # source id -> reason


def _fetch(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "findoc-assistant/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def download_missing(sources: list[Source], data_dir: Path, timeout: float = 60) -> DownloadReport:
    """Download every source that has a URL and no local file.

    A failure on one source does not stop the others: some sites refuse requests that do not
    come from a browser, and those files have to be saved by hand.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    report = DownloadReport()
    for source in sources:
        target = source.path(data_dir)
        if target.exists():
            report.already_present.append(source.id)
            continue
        if source.url is None:
            report.failed[source.id] = "no URL in sources.yaml"
            continue
        try:
            body = _fetch(str(source.url), timeout)
        except urllib.error.HTTPError as exc:
            report.failed[source.id] = f"HTTP {exc.code} {exc.reason}"
            continue
        except (urllib.error.URLError, TimeoutError) as exc:
            report.failed[source.id] = f"network error: {exc}"
            continue
        if not body.startswith(_PDF_MAGIC):
            report.failed[source.id] = "the response is not a PDF"
            continue
        # Write to a temporary name first so an interrupted download never looks complete.
        partial = target.with_suffix(".part")
        partial.write_bytes(body)
        partial.replace(target)
        logger.info("%s: downloaded %d bytes", source.id, len(body))
        report.downloaded.append(source.id)
    return report
