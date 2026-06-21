"""Tests for paper classification.

These tests check that category keywords are found correctly in paper titles or
text, and that the first matching category is selected.
"""

from pathlib import Path

from literature_manager.core.classifier import classify_paper, keyword_matches
from literature_manager.core.models import PaperMetadata


def test_keyword_matches_handles_spaces_and_hyphens():
    assert keyword_matches("origin of life", "Origin-of-life chemistry")
    assert keyword_matches("ocean world", "an ocean world model")


def test_keyword_matches_uses_word_boundaries():
    assert keyword_matches("mars", "samples from Mars")
    assert not keyword_matches("mars", "marseille sample")


def test_classify_paper_returns_first_matching_category():
    metadata = PaperMetadata(
        source_path=Path("paper.pdf"),
        title="Micellar catalysis in origin of life chemistry",
        journal="Unknown Journal",
        last_author="Unknown",
    )
    categories = {
        "Micelles": ["micelle", "micellar"],
        "Soup": ["origin of life"],
        "General": [],
    }

    category, matches = classify_paper(metadata, "", categories)

    assert category == "Micelles"
    assert matches == ["micellar"]
