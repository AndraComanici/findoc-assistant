from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ingestion.sources import load_sources

REPO_ROOT = Path(__file__).parent.parent


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text(text, encoding="utf-8")
    return path


ENTRY = """
  - id: {id}
    company: Exemplu
    ticker: EX
    year: 2025
    title: Raportul anual 2025
    file: {file}
"""


def test_the_committed_sources_file_is_valid():
    sources = load_sources(REPO_ROOT / "corpus" / "sources.yaml")
    assert len(sources) == 6


def test_duplicate_ids_are_rejected(tmp_path):
    text = (
        "documents:"
        + ENTRY.format(id="ex-2025", file="a.pdf")
        + ENTRY.format(id="ex-2025", file="b.pdf")
    )
    with pytest.raises(ValidationError, match="duplicate id"):
        load_sources(write(tmp_path, text))


@pytest.mark.parametrize("bad_file", ["../secret.pdf", "sub/dir.pdf", "report.docx"])
def test_file_must_be_a_bare_pdf_name(tmp_path, bad_file):
    text = "documents:" + ENTRY.format(id="ex-2025", file=bad_file)
    with pytest.raises(ValidationError):
        load_sources(write(tmp_path, text))
