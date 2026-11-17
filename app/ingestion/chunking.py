"""Split page text into overlapping chunks that never cross a page boundary.

Sizes are measured in words, a simple and model-independent proxy for tokens.
"""

import re
from dataclasses import dataclass

from app.ingestion.normalize import normalize_text
from app.ingestion.pdf import Page

# A sentence ends with . ! or ? followed by whitespace and an uppercase letter or a digit.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ0-9])")


@dataclass(frozen=True)
class Chunk:
    index: int
    page_number: int
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_END.split(text) if s]


def _units(text: str, max_words: int) -> list[list[str]]:
    """Sentences as word lists; a sentence longer than max_words (often a table) is cut."""
    units: list[list[str]] = []
    for sentence in split_sentences(text):
        words = sentence.split()
        for start in range(0, len(words), max_words):
            units.append(words[start : start + max_words])
    return units


def chunk_page(text: str, max_words: int, overlap_words: int) -> list[str]:
    """Pack whole sentences into chunks of at most max_words.

    Each new chunk starts with the last sentences of the previous one, up to overlap_words,
    so that information near a boundary is present in both chunks.
    """
    if not 0 <= overlap_words < max_words:
        raise ValueError("overlap_words must be at least 0 and smaller than max_words")

    chunks: list[str] = []
    current: list[list[str]] = []
    size = 0
    for unit in _units(text, max_words):
        if current and size + len(unit) > max_words:
            chunks.append(" ".join(word for u in current for word in u))
            # Carry over trailing sentences that fit in the overlap budget.
            carried: list[list[str]] = []
            carried_size = 0
            for previous in reversed(current):
                if carried_size + len(previous) > overlap_words:
                    break
                carried.insert(0, previous)
                carried_size += len(previous)
            # Never let the overlap alone fill the next chunk.
            if carried_size + len(unit) > max_words:
                carried, carried_size = [], 0
            current, size = carried, carried_size
        current.append(unit)
        size += len(unit)
    if current:
        chunks.append(" ".join(word for u in current for word in u))
    return chunks


def chunk_document(pages: list[Page], max_words: int, overlap_words: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        text = normalize_text(page.text)
        for piece in chunk_page(text, max_words, overlap_words):
            chunks.append(Chunk(index=len(chunks), page_number=page.number, text=piece))
    return chunks
