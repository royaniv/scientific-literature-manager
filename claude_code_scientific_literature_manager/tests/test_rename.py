"""Tests for slm.rename."""
from slm.rename import abbreviate, clean, safe, shorten, title_case


def test_clean_strips_tags():
    assert clean("<b>Hello</b> world") == "Hello world"


def test_clean_html_entities():
    assert clean("Caf&eacute; &amp; co") == "Café & co"


def test_safe_removes_illegal_chars():
    result = safe('test:file*name?.pdf')
    assert ':' not in result
    assert '*' not in result
    assert '?' not in result


def test_title_case_basic():
    assert title_case("the origin of life") == "The Origin of Life"


def test_title_case_preposition_not_capitalised():
    t = title_case("study of micelles in water")
    assert t.startswith("Study")
    words = t.split()
    assert "of" in words
    assert "in" in words


def test_shorten():
    text = "The quick brown fox jumped over the lazy dog"
    assert shorten(text, 4) == "The quick brown fox"


def test_abbreviate_known():
    result = abbreviate("Journal of Chemical Physics")
    assert len(result) < len("Journal of Chemical Physics")
    assert "Chem" in result or "Phys" in result


def test_abbreviate_empty():
    assert abbreviate("") == "Unknown"
