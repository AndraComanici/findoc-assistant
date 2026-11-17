import pytest

from app.ingestion.chunking import chunk_document, chunk_page, split_sentences
from app.ingestion.pdf import Page


def sentence(n_words: int, label: str) -> str:
    return " ".join([label.capitalize()] + [label] * (n_words - 1)) + "."


def test_split_sentences_on_terminal_punctuation():
    text = "Profitul a crescut. Veniturile au scăzut! Cât? 2025 a fost bun."
    assert split_sentences(text) == [
        "Profitul a crescut.",
        "Veniturile au scăzut!",
        "Cât?",
        "2025 a fost bun.",
    ]


def test_short_text_is_a_single_chunk():
    assert chunk_page("Profitul net a crescut.", max_words=50, overlap_words=10) == [
        "Profitul net a crescut."
    ]


def test_chunks_respect_the_word_limit():
    text = " ".join(sentence(30, f"w{i}") for i in range(10))
    chunks = chunk_page(text, max_words=100, overlap_words=0)
    assert all(len(c.split()) <= 100 for c in chunks)
    assert len(chunks) == 4  # 3 sentences (90 words) fit in each chunk


def test_sentences_are_never_cut_when_they_fit():
    text = " ".join(sentence(30, f"w{i}") for i in range(5))
    for chunk in chunk_page(text, max_words=70, overlap_words=0):
        assert chunk.endswith(".")


def test_consecutive_chunks_overlap_by_whole_sentences():
    text = " ".join(sentence(20, f"w{i}") for i in range(6))
    chunks = chunk_page(text, max_words=60, overlap_words=20)
    # The last sentence of each chunk starts the next one.
    for previous, current in zip(chunks, chunks[1:], strict=False):
        last_sentence = split_sentences(previous)[-1]
        assert current.startswith(last_sentence)


def test_a_sentence_longer_than_the_limit_is_cut():
    long_table_row = " ".join(["123"] * 250)
    chunks = chunk_page(long_table_row, max_words=100, overlap_words=10)
    assert [len(c.split()) for c in chunks] == [100, 100, 50]


def test_empty_text_gives_no_chunks():
    assert chunk_page("", max_words=100, overlap_words=10) == []


@pytest.mark.parametrize("overlap", [-1, 100, 150])
def test_invalid_overlap_is_rejected(overlap):
    with pytest.raises(ValueError):
        chunk_page("Text.", max_words=100, overlap_words=overlap)


def test_chunks_never_cross_pages_and_keep_page_numbers():
    pages = [
        Page(number=1, text="Prima pagină. Are două propoziții."),
        Page(number=2, text=""),
        Page(number=3, text="A treia pagină."),
    ]
    chunks = chunk_document(pages, max_words=100, overlap_words=10)
    assert [(c.index, c.page_number, c.text) for c in chunks] == [
        (0, 1, "Prima pagină. Are două propoziții."),
        (1, 3, "A treia pagină."),
    ]
