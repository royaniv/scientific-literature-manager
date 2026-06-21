"""
core.py — PDF reading, metadata retrieval, classification, and renaming.

Pipeline for each PDF:
  1. read_text()      — extract raw text from first N pages
  2. find_doi()       — regex search for a DOI
  3. fetch_crossref() — look up the DOI via the Crossref REST API
  4. guess_from_text()— fallback heuristics when no DOI / no network
  5. classify()       — assign a category and priority by keyword matching
  6. make_filename()  — format the new name from a template
"""

from __future__ import annotations

import html
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

# ── Optional third-party imports ─────────────────────────────────────────────

try:
    from pypdf import PdfReader as _PdfReader
    PDF_OK = True
except ImportError:
    _PdfReader = None
    PDF_OK = False

try:
    import requests as _requests
    NET_OK = True
except ImportError:
    _requests = None
    NET_OK = False

# ── Default categories and priority rules ────────────────────────────────────

DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Micelles":   ["micelle", "micellar", "amphiphile", "vesicle", "composome", "gard"],
    "Chiral":     ["chiral", "chirality", "enantiomer", "homochirality"],
    "Soup":       ["origin of life", "prebiotic", "primordial soup", "autocatalysis"],
    "Astro":      ["astrobiology", "biosignature", "enceladus", "europa", "icy moon", "mars"],
    "Light":      ["light", "photochemical", "photochemistry", "photolysis", "ultraviolet"],
    "OrganBactr": ["bacteria", "bacterial", "microbe", "microbial", "microorganism"],
    "General":    [],
}

PRIORITY_AUTHORS  = ["Lancet"]
PRIORITY_KEYWORDS = ["Doron Lancet", "GARD", "composome", "origin of life"]

# ── Regex helpers ─────────────────────────────────────────────────────────────

_DOI_RE  = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_YEAR_RE = re.compile(r"(19|20)\d{2}")
_UNSAFE  = re.compile(r'[\\/*?:"<>|]')

_LOWER_WORDS = frozenset([
    "a","an","and","at","by","for","from","in","of","on","or","the","to","with",
])
_JOURNAL_STOP = frozenset([
    "a","and","for","in","international","journal","of","on","the",
])


# ── Paper state ───────────────────────────────────────────────────────────────

class State(Enum):
    PENDING = auto()   # not yet processed
    PLANNED = auto()   # preview computed, not yet applied
    DONE    = auto()   # file copied / moved successfully
    FAILED  = auto()   # an error occurred


@dataclass
class Paper:
    """All information about one PDF file."""
    source:      Path
    title:       str       = "Unknown Title"
    author:      str       = "Unknown"
    journal:     str       = "Unknown Journal"
    year:        str       = "0000"
    doi:         str       = ""
    category:    str       = "General"
    priority:    str       = "normal"
    keywords:    list[str] = field(default_factory=list)
    new_name:    str       = ""
    destination: Path|None = None
    state:       State     = State.PENDING
    error:       str       = ""

    @property
    def is_high_priority(self) -> bool:
        return self.priority == "high"

    @property
    def year_short(self) -> str:
        return self.year[-2:] if len(self.year) >= 2 else "00"

    @property
    def status_label(self) -> str:
        return {
            State.PENDING: "—",
            State.PLANNED: "Preview",
            State.DONE:    "Done ✓",
            State.FAILED:  f"Error: {self.error}",
        }[self.state]


# ── Text cleaning helpers ─────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _safe(text: str) -> str:
    return _UNSAFE.sub("", _clean(text)).strip(" .")

def _title_case(text: str) -> str:
    words = _clean(text).lower().split()
    if not words:
        return "Unknown Title"
    return " ".join(
        w.capitalize() if (i == 0 or w not in _LOWER_WORDS) else w
        for i, w in enumerate(words)
    )

def _shorten(text: str, max_words: int = 8) -> str:
    return " ".join(_clean(text).split()[:max_words])

def _abbreviate_journal(journal: str) -> str:
    """Shorten a journal name: keep first 4 letters of each significant word."""
    words = [
        re.sub(r"[^A-Za-z0-9]", "", w)
        for w in re.sub(r"[^\w\s]", " ", _safe(journal)).split()
        if w.lower() not in _JOURNAL_STOP
    ]
    words = [w for w in words if len(w) >= 3]
    if not words:
        return "Unknown"
    return " ".join(
        w if (w.isupper() and len(w) <= 4) else w[:4].title()
        for w in words[:4]
    )


# ── Step 1: read PDF text ─────────────────────────────────────────────────────

def read_text(path: Path, max_pages: int = 3) -> str:
    """Extract plain text from the first max_pages pages of a PDF."""
    if _PdfReader is None:
        return ""
    try:
        reader = _PdfReader(str(path))
        pages  = []
        for page in reader.pages[:max_pages]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(pages)
    except Exception:
        return ""


# ── Step 2: find DOI ──────────────────────────────────────────────────────────

def find_doi(text: str) -> str:
    """Return the first DOI found in text, or empty string."""
    m = _DOI_RE.search(text)
    return m.group(0).rstrip(").,;]") if m else ""


# ── Step 3: Crossref lookup ───────────────────────────────────────────────────

def fetch_crossref(doi: str) -> dict[str, str]:
    """Return metadata dict from Crossref for the given DOI, or {}."""
    if not doi or _requests is None:
        return {}
    try:
        resp = _requests.get(
            f"https://api.crossref.org/works/{doi}",
            timeout=12,
            headers={"User-Agent": "paper-organizer/1.0 (weizmann course project)"},
        )
        resp.raise_for_status()
        msg = resp.json().get("message", {})
    except Exception:
        return {}

    authors    = msg.get("author", [])
    last       = authors[-1] if authors else {}
    author     = last.get("family") or last.get("name") or "Unknown"
    containers = msg.get("container-title") or []
    journal    = containers[0] if containers else "Unknown Journal"
    titles     = msg.get("title") or []
    title      = titles[0] if titles else "Unknown Title"
    parts      = msg.get("issued", {}).get("date-parts", [[]])
    year       = str(parts[0][0]) if parts and parts[0] else "0000"

    return {"title": title, "journal": journal, "year": year, "author": author}


# ── Step 4: fallback from text ────────────────────────────────────────────────

def guess_from_text(text: str) -> dict[str, str]:
    """Heuristic metadata when no DOI is available or Crossref has no entry."""
    lines  = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title  = max(lines[:12], key=len) if lines else "Unknown Title"
    author = "Unknown"
    for line in lines[:12]:
        if "," in line and len(line.split()) <= 12:
            author = line.split(",")[-1].strip() or "Unknown"
            break
    m    = _YEAR_RE.search(text)
    year = m.group(0) if m else "0000"
    return {"title": title, "journal": "Unknown Journal", "year": year, "author": author}


# ── Step 5: classify ─────────────────────────────────────────────────────────

def _kw_match(keyword: str, haystack: str) -> bool:
    parts   = [re.escape(p) for p in keyword.strip().lower().split()]
    pattern = r"[\s-]+".join(parts)
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", haystack))


def classify(
    paper: Paper,
    text: str,
    categories: dict[str, list[str]] = DEFAULT_CATEGORIES,
) -> None:
    """Assign paper.category, paper.keywords, and paper.priority in-place."""
    haystack = " ".join([paper.title, paper.journal, paper.author, text]).lower()

    # category: first match wins
    paper.category = "General"
    paper.keywords = []
    for cat, keywords in categories.items():
        if cat.lower() == "general":
            continue
        matched = [kw for kw in keywords if _kw_match(kw, haystack)]
        if matched:
            paper.category = cat
            paper.keywords = matched
            break

    # priority
    if any(a.lower() in paper.author.lower() for a in PRIORITY_AUTHORS):
        paper.priority = "high"
    elif any(_kw_match(kw, haystack) for kw in PRIORITY_KEYWORDS):
        paper.priority = "high"
    else:
        paper.priority = "normal"


# ── Step 6: build filename ────────────────────────────────────────────────────

def make_filename(paper: Paper, identifier: str, template: str) -> str:
    """
    Format a filename from a template string.

    Available placeholders:
      {id}           — the sequential identifier, e.g. CB001
      {author}       — last author family name
      {title}        — shortened, title-cased title (8 words)
      {journal}      — abbreviated journal name
      {journal_full} — full journal name
      {year}         — 4-digit year
      {year_short}   — 2-digit year
      {category}     — assigned category name
    """
    short_title = _title_case(_shorten(paper.title))
    values = {
        "id":           identifier,
        "author":       _safe(paper.author) or "Unknown",
        "title":        _safe(short_title) or "Unknown Title",
        "journal":      _abbreviate_journal(paper.journal),
        "journal_full": _safe(paper.journal) or "Unknown Journal",
        "year":         paper.year,
        "year_short":   paper.year_short,
        "category":     paper.category,
    }
    name = template.format(**values)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return _safe(name)


# ── File collection ───────────────────────────────────────────────────────────

def collect_pdfs(paths: list[Path], recursive: bool = False) -> list[Path]:
    """Return a sorted, deduplicated list of PDF paths from files and/or folders."""
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".pdf":
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(path.rglob("*.pdf") if recursive else path.glob("*.pdf"))
        else:
            candidates = []
        for c in candidates:
            r = c.resolve()
            if r not in seen:
                seen.add(r)
                result.append(r)
    return sorted(result)


# ── Planning ──────────────────────────────────────────────────────────────────

ProgressCallback = Callable[[int, int, str], None]


def plan_papers(
    pdfs:             list[Path],
    output_dir:       Path,
    prefix:           str  = "CB",
    digits:           int  = 3,
    start:            int  = 1,
    template:         str  = "{id} {author}, {title}, {journal} {year_short}.pdf",
    categories:       dict = DEFAULT_CATEGORIES,
    sort_into_folders: bool = False,
    on_progress:      ProgressCallback | None = None,
) -> list[Paper]:
    """
    Build a plan: one Paper object per PDF with a suggested destination.
    No files are changed — call apply_plan() to execute.
    """
    # Scan existing files to avoid re-using IDs already in the output folder
    pat = re.compile(rf"^{re.escape(prefix)}(\d+)\b")
    existing_ids = [
        int(m.group(1)) for p in output_dir.rglob("*.pdf")
        if output_dir.exists() and (m := pat.match(p.name))
    ]
    counter  = max(existing_ids, default=start - 1) + 1
    taken:   set[Path] = set()
    papers:  list[Paper] = []
    total = len(pdfs)

    for i, path in enumerate(pdfs):
        if on_progress:
            on_progress(i, total, path.name)

        text   = read_text(path)
        doi    = find_doi(text)
        meta   = fetch_crossref(doi) or guess_from_text(text)

        paper = Paper(
            source  = path,
            doi     = doi,
            title   = meta.get("title", "Unknown Title"),
            journal = meta.get("journal", "Unknown Journal"),
            year    = meta.get("year", "0000"),
            author  = meta.get("author", "Unknown"),
        )
        classify(paper, text, categories)

        identifier    = f"{prefix}{counter:0{digits}d}"
        counter      += 1
        paper.new_name = make_filename(paper, identifier, template)

        dest_dir = (output_dir / paper.category) if sort_into_folders else output_dir
        dest     = dest_dir / paper.new_name
        n = 2
        while dest.exists() or dest in taken:
            dest = dest_dir / f"{paper.new_name[:-4]} ({n}).pdf"
            n += 1

        paper.destination = dest
        taken.add(dest)
        paper.state = State.PLANNED
        papers.append(paper)

    if on_progress:
        on_progress(total, total, "")
    return papers


# ── Applying ──────────────────────────────────────────────────────────────────

def apply_plan(papers: list[Paper], copy: bool = True) -> None:
    """
    Execute the plan produced by plan_papers().
    Each paper is marked DONE or FAILED individually.
    """
    for paper in papers:
        if paper.state != State.PLANNED or paper.destination is None:
            continue
        try:
            paper.destination.parent.mkdir(parents=True, exist_ok=True)
            if copy:
                shutil.copy2(paper.source, paper.destination)
            else:
                shutil.move(str(paper.source), str(paper.destination))
            paper.state = State.DONE
        except Exception as exc:
            paper.state = State.FAILED
            paper.error = str(exc)
