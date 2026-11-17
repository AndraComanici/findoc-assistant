from app.ingestion.chunking import chunk_document
from app.ingestion.pdf import extract_pages, file_sha256


def test_extracts_one_entry_per_page_numbered_from_one(sample_pdf):
    pages = extract_pages(sample_pdf)
    assert [p.number for p in pages] == [1, 2, 3]
    assert pages[1].text.strip() == ""


def test_extracted_text_keeps_romanian_letters(sample_pdf):
    first_page = extract_pages(sample_pdf)[0].text
    assert "exercițiului" in first_page


def test_sample_report_end_to_end(sample_pdf):
    chunks = chunk_document(extract_pages(sample_pdf), max_words=200, overlap_words=40)
    assert [c.page_number for c in chunks] == [1, 3]
    assert "contractelor noi" in chunks[0].text  # rejoined across a line break
    assert "60% din profitul net" in chunks[1].text


def test_file_hash_is_stable(sample_pdf):
    assert file_sha256(sample_pdf) == file_sha256(sample_pdf)
    assert len(file_sha256(sample_pdf)) == 64
