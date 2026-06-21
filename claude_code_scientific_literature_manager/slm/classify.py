"""Keyword-based paper classification.

Functionally equivalent to the original but:
- Takes `Config` directly instead of raw category/priority dicts.
- The haystack builder is a module-level function, not nested.
- Type hints on all public functions.
"""
from __future__ import annotations

import re

from slm.config import Config, PriorityConfig
from slm.paper import Paper


def _haystack(paper: Paper, text: str) -> str:
    return " ".join([paper.title, paper.journal, paper.author, text or ""]).lower()


def keyword_hits(keyword: str, haystack: str) -> bool:
    parts = [re.escape(p) for p in keyword.strip().lower().split()]
    pattern = r"[\s-]+".join(parts)
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", haystack))


def assign_category(
    paper: Paper,
    text: str,
    categories: dict[str, list[str]],
) -> tuple[str, list[str]]:
    hay = _haystack(paper, text)
    for category, keywords in categories.items():
        if category.lower() == "general":
            continue
        matched = [kw for kw in keywords if keyword_hits(kw, hay)]
        if matched:
            return category, matched
    return "General", []


def assign_priority(paper: Paper, text: str, rules: PriorityConfig) -> str:
    hay = _haystack(paper, text)
    if any(a.lower() in paper.author.lower() for a in rules.authors):
        return "high"
    if any(j.lower() in paper.journal.lower() for j in rules.journals):
        return "high"
    if any(keyword_hits(kw, hay) for kw in rules.keywords):
        return "high"
    return "normal"


def classify(paper: Paper, text: str, config: Config) -> None:
    """Assign category and priority in-place."""
    paper.category, paper.keywords = assign_category(paper, text, config.categories)
    paper.priority = assign_priority(paper, text, config.priority)
