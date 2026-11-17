"""Extract text from a PDF, one entry per page."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class Page:
    number: int  # 1-based position in the PDF, as shown by PDF viewers
    text: str


def extract_pages(path: Path) -> list[Page]:
    reader = PdfReader(path)
    return [
        Page(number=index + 1, text=page.extract_text() or "")
        for index, page in enumerate(reader.pages)
    ]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
