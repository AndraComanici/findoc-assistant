import urllib.error

from app.ingestion import download
from app.ingestion.sources import Source


def make_source(source_id: str, url: str | None = "https://example.com/r.pdf") -> Source:
    return Source(
        id=source_id,
        company="Exemplu",
        ticker="EX",
        year=2025,
        title="Raport",
        url=url,
        file=f"{source_id}.pdf",
    )


def test_one_failure_does_not_stop_the_other_downloads(tmp_path, monkeypatch):
    def fake_fetch(url: str, timeout: float) -> bytes:
        if "blocked" in url:
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        return b"%PDF-1.7 content"

    monkeypatch.setattr(download, "_fetch", fake_fetch)
    sources = [
        make_source("a-2025", "https://blocked.example.com/a.pdf"),
        make_source("b-2025"),
        make_source("c-2025", url=None),
    ]

    report = download.download_missing(sources, tmp_path)

    assert report.downloaded == ["b-2025"]
    assert report.failed == {"a-2025": "HTTP 403 Forbidden", "c-2025": "no URL in sources.yaml"}
    assert (tmp_path / "b-2025.pdf").read_bytes().startswith(b"%PDF-")
    assert not (tmp_path / "a-2025.pdf").exists()


def test_a_response_that_is_not_a_pdf_is_not_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "_fetch", lambda url, timeout: b"<html>login</html>")

    report = download.download_missing([make_source("a-2025")], tmp_path)

    assert report.failed == {"a-2025": "the response is not a PDF"}
    assert list(tmp_path.iterdir()) == []


def test_files_already_on_disk_are_not_downloaded_again(tmp_path, monkeypatch):
    (tmp_path / "a-2025.pdf").write_bytes(b"%PDF-existing")

    def must_not_be_called(url: str, timeout: float) -> bytes:
        raise AssertionError("should not download")

    monkeypatch.setattr(download, "_fetch", must_not_be_called)

    report = download.download_missing([make_source("a-2025")], tmp_path)

    assert report.already_present == ["a-2025"]
