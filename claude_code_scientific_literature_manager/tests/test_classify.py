"""Tests for slm.classify."""
import pytest
from slm.classify import assign_category, assign_priority, keyword_hits
from slm.config import Config, PriorityConfig
from slm.paper import Paper


@pytest.fixture
def cfg() -> Config:
    return Config()


def test_keyword_hits_simple():
    assert keyword_hits("micelle", "The micelle formation is key.")


def test_keyword_hits_boundary():
    # Should NOT match "micelles" inside "micellesome"
    assert not keyword_hits("micelle", "micellesome compound")


def test_keyword_hits_multi_word():
    assert keyword_hits("origin of life", "Research on the origin of life is ongoing.")


def test_assign_category_matches(cfg):
    paper = Paper(source=__file__, title="Study of chiral amplification", journal="Nature")
    cat, kws = assign_category(paper, "", cfg.categories)
    assert cat == "Chiral"
    assert kws


def test_assign_category_general(cfg):
    paper = Paper(source=__file__, title="Quantum chromodynamics review", journal="Physics")
    cat, kws = assign_category(paper, "", cfg.categories)
    assert cat == "General"
    assert not kws


def test_assign_priority_author(cfg):
    paper = Paper(source=__file__, title="Some title", journal="Nature",
                  author="Doron Lancet")
    pri = assign_priority(paper, "", cfg.priority)
    assert pri == "high"


def test_assign_priority_keyword(cfg):
    paper = Paper(source=__file__, title="GARD model revisited", journal="Origin")
    pri = assign_priority(paper, "The GARD model proposes...", cfg.priority)
    assert pri == "high"


def test_assign_priority_normal(cfg):
    paper = Paper(source=__file__, title="Random crystal study", journal="Crystal")
    pri = assign_priority(paper, "", cfg.priority)
    assert pri == "normal"
