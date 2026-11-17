"""Clean up text extracted from PDFs before it is chunked and indexed."""

import re
import unicodedata

# Romanian ș and ț are often encoded with a cedilla (ş, ţ) in older fonts and documents.
# The correct letters use a comma below. Without this, "ştiinţă" and "știință" would be
# different words for search.
_CEDILLA_TO_COMMA = str.maketrans({"ş": "ș", "Ş": "Ș", "ţ": "ț", "Ţ": "Ț"})

# Characters that carry no meaning in extracted text: soft hyphen, zero-width characters,
# byte order mark, NUL.
_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍﻿\x00"), None)

# A word split across two lines, e.g. "con-\ntract". [^\W\d_] means "a letter".
_LINE_BREAK_HYPHEN = re.compile(r"([^\W\d_]{2,})-\n([^\W\d_]+)")

_WHITESPACE = re.compile(r"\s+")


def _join_hyphenated(match: re.Match[str]) -> str:
    head, tail = match.group(1), match.group(2)
    # Rejoin only when the continuation is a lowercase fragment of at least three letters.
    # This keeps Romanian clitic forms such as "într-un", "s-a" or "dintr-o" intact when
    # they happen to fall at a line break.
    if len(tail) >= 3 and tail.islower():
        return head + tail
    return f"{head}-{tail}"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_CEDILLA_TO_COMMA).translate(_INVISIBLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _LINE_BREAK_HYPHEN.sub(_join_hyphenated, text)
    return _WHITESPACE.sub(" ", text).strip()
