"""PDF text extraction, DOI detection, and Crossref lookup.

Differences from the original:
- Returns a single dict from get_metadata() instead of having many
  separate functions called at the call site.
- PYPDF_OK / REQUESTS_OK are booleans for clean feature detection.
- guess_from_text() is renamed from fallback_metadata() for clarity.
"""
from __future__ import annotations

import re
from pathlib import Path

try:
    import requests as _req
    REQUESTS_OK = True
except ImportError:
    _req = None  # type: ignore
    REQUESTS_OK = False

try:
    from pypdf import PdfReader as _PdfReader
    PYPDF_OK = True
except ImportError:
    _PdfReader = None  # type: ignore
    PYPDF_OK = False

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_YEAR_RE = re.compile(r"(19|20)\d{2}")


def read_pdf_text(path: Path, max_pages: int) -> str:
    if _PdfReader is None:
        return ""
    try:
        reader = _PdfReader(str(path))
    except Exception:
        return ""
    pages: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pass
    return "\n".join(pages)


def find_doi(text: str) -> str:
    m = _DOI_RE.search(text)
    return m.group(0).rstrip(").,;]") if m else ""


def lookup_crossref(doi: str) -> dict[str, str]:
    if not doi or _req is None:
        return {}
    try:
        resp = _req.get(
            f"https://api.crossref.org/works/{doi}",
            timeout=12,
            headers={"User-Agent": "slm/0.1 (scientific-literature-manager)"},
        )
        resp.raise_for_status()
        msg = resp.json().get("message", {})
    except Exception:
        return {}

    authors = msg.get("author", [])
    last = authors[-1] if authors else {}
    author = last.get("family") or last.get("name") or "Unknown"

    containers = msg.get("container-title") or []
    journal = containers[0] if containers else "Unknown Journal"

    titles = msg.get("title") or []
    title = titles[0] if titles else "Unknown Title"

    date_parts = msg.get("issued", {}).get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else "0000"

    return {"title": title, "journal": journal, "year": year, "author": author}


def guess_from_text(text: str) -> dict[str, str]:
    """Heuristic fallback when Crossref returns nothing."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = max(lines[:12], key=len) if lines else "Unknown Title"

    author = "Unknown"
    for line in lines[:12]:
        if "," in line and len(line.split()) <= 12:
            author = line.split(",")[-1].strip() or "Unknown"
            break

    m = _YEAR_RE.search(text)
    year = m.group(0) if m else "0000"

    return {"title": title, "journal": "Unknown Journal", "year": year, "author": author}


def get_metadata(path: Path, pages: int) -> dict[str, str]:
    """Extract metadata from a PDF, returning a flat dict with text included."""
    text = read_pdf_text(path, pages)
    doi = find_doi(text)
    meta = lookup_crossref(doi) or guess_from_text(text)
    meta["doi"] = doi
    meta["text"] = text
    return meta
