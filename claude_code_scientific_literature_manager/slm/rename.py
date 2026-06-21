"""Filename and identifier generation.

Design differences from the original:
- Text helpers (clean, safe, title_case, shorten, abbreviate) live here
  rather than in a separate text.py — they're only needed for renaming.
- `next_id()` takes a Config object, not unpacked individual settings.
- `build_name()` uses `{journal}` as the short abbreviation in the default
  template, so `journal` maps to the abbreviated form.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from slm.config import NamingConfig
from slm.paper import Paper

_LOWER_WORDS = frozenset({
    "a", "an", "and", "at", "by", "for", "from",
    "in", "of", "on", "or", "the", "to", "with",
})
_JOURNAL_STOP = frozenset({
    "a", "and", "for", "in", "international", "journal", "of", "on", "the",
})
_UNSAFE_CHARS = re.compile(r'[\\/*?:"<>|]')


def clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def safe(text: str) -> str:
    return _UNSAFE_CHARS.sub("", clean(text)).strip(" .")


def title_case(text: str) -> str:
    words = clean(text).lower().split()
    if not words:
        return "Unknown Title"
    return " ".join(
        w.capitalize() if i == 0 or w not in _LOWER_WORDS else w
        for i, w in enumerate(words)
    )


def shorten(text: str, max_words: int) -> str:
    words = clean(text).split()
    return " ".join(words[:max_words]) if words else "Unknown Title"


def abbreviate(journal: str) -> str:
    journal = safe(journal)
    if not journal:
        return "Unknown"
    words = [
        re.sub(r"[^A-Za-z0-9]", "", w)
        for w in re.sub(r"[^\w\s]", " ", journal).split()
        if w.lower() not in _JOURNAL_STOP
    ]
    words = [w for w in words if len(w) >= 3]
    if not words:
        return "Unknown"
    parts = [w if (w.isupper() and len(w) <= 4) else w[:4].title() for w in words[:4]]
    return " ".join(parts)


def _scan_existing(output_dir: Path, prefix: str) -> list[int]:
    pat = re.compile(rf"^{re.escape(prefix)}(\d+)\b")
    return [
        int(m.group(1))
        for p in output_dir.rglob("*.pdf")
        if (m := pat.match(p.name))
    ]


def next_id(paper: Paper, output_dir: Path, cfg: NamingConfig, counters: dict[str, int]) -> str:
    prefix = cfg.category_prefixes.get(paper.category, cfg.prefix) if cfg.per_category else cfg.prefix
    if prefix not in counters:
        existing = _scan_existing(output_dir, prefix) if output_dir.exists() else []
        counters[prefix] = max(existing, default=cfg.start - 1) + 1
    number = counters[prefix]
    counters[prefix] += 1
    return f"{prefix}{number:0{cfg.digits}d}"


def build_name(paper: Paper, identifier: str, cfg: NamingConfig) -> str:
    short_title = title_case(shorten(paper.title, cfg.title_words))
    values = {
        "id": identifier,
        "author": safe(paper.author) or "Unknown",
        "title": safe(short_title) or "Unknown Title",
        "journal": abbreviate(paper.journal),
        "journal_full": safe(paper.journal) or "Unknown Journal",
        "year": paper.year,
        "year_short": paper.year_short,
        "category": safe(paper.category),
        "priority": paper.priority,
    }
    name = cfg.template.format(**values)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return safe(name)
