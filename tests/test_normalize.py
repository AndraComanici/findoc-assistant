import pytest

from app.ingestion.normalize import normalize_text


def test_cedilla_letters_become_comma_below():
    assert normalize_text("ştiinţă ŞI ŢARĂ") == "știință ȘI ȚARĂ"


def test_decomposed_characters_are_composed():
    decomposed = "ă"  # "a" followed by a combining breve
    assert normalize_text(decomposed) == "ă"


def test_invisible_characters_are_removed():
    assert normalize_text("pro­fit​ net\x00") == "profit net"


def test_words_split_across_lines_are_rejoined():
    assert normalize_text("semnarea con-\ntractelor noi") == "semnarea contractelor noi"


@pytest.mark.parametrize("text", ["într-\nun an", "s-\na semnat", "dintr-\no societate"])
def test_romanian_clitic_hyphens_are_kept(text):
    assert "-" in normalize_text(text)


def test_hyphen_before_a_capitalised_word_is_kept():
    assert normalize_text("Cluj-\nNapoca") == "Cluj-Napoca"


def test_whitespace_is_collapsed():
    assert normalize_text("  profit \n\n net\t2025  ") == "profit net 2025"
