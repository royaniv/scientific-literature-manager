"""File collection, planning, and execution.

Design differences from the original:
- `plan()` accepts an optional `on_progress` callback (index, total, filename)
  so any UI can report progress without knowing how planning works internally.
- `apply()` marks each paper with PaperState.DONE or PaperState.FAILED
  individually, so partial failures are visible in the results.
- `collect()` takes a list of Paths directly instead of separate
  file/folder collection functions.
"""
from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from slm.classify import classify
from slm.config import Config
from slm.extract import get_metadata
from slm.paper import Paper, PaperState
from slm.rename import build_name, next_id, safe

ProgressCallback = Callable[[int, int, str], None]


def collect(paths: list[Path], recursive: bool = False) -> list[Path]:
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
            resolved = c.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(resolved)
    return sorted(result)


def _unique(path: Path, taken: set[Path]) -> Path:
    if not path.exists() and path not in taken:
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    n = 2
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists() and candidate not in taken:
            return candidate
        n += 1


def _dest_dir(base: Path, category: str, sort: bool) -> Path:
    return base / (safe(category) or "General") if sort else base


def plan(
    pdf_paths: list[Path],
    output_dir: Path,
    config: Config,
    sort_into_folders: bool = False,
    rename: bool = True,
    on_progress: ProgressCallback | None = None,
) -> list[Paper]:
    counters: dict[str, int] = {}
    taken: set[Path] = set()
    papers: list[Paper] = []
    total = len(pdf_paths)

    for i, path in enumerate(pdf_paths):
        if on_progress:
            on_progress(i, total, path.name)

        meta = get_metadata(path, config.scan.pages)
        text = meta.pop("text", "")

        paper = Paper(
            source=path,
            doi=meta.get("doi", ""),
            title=meta.get("title", "Unknown Title"),
            journal=meta.get("journal", "Unknown Journal"),
            year=meta.get("year", "0000"),
            author=meta.get("author", "Unknown"),
        )

        classify(paper, text, config)

        if rename:
            identifier = next_id(paper, output_dir, config.naming, counters)
            paper.new_name = build_name(paper, identifier, config.naming)
        else:
            paper.new_name = safe(path.name) or path.name

        dest_dir = _dest_dir(output_dir, paper.category, sort_into_folders)
        paper.destination = _unique(dest_dir / paper.new_name, taken)
        taken.add(paper.destination)
        paper.state = PaperState.PLANNED
        papers.append(paper)

    if on_progress:
        on_progress(total, total, "")

    return papers


def apply(papers: list[Paper], copy: bool = True) -> list[Paper]:
    seen: dict[str, Path] = {}

    for paper in papers:
        if paper.state != PaperState.PLANNED or paper.destination is None:
            continue
        key = str(paper.destination.resolve()).lower()
        if key in seen:
            paper.state = PaperState.FAILED
            paper.error = f"Destination conflicts with {seen[key].name}"
            continue
        if paper.destination.exists():
            paper.state = PaperState.FAILED
            paper.error = "Destination already exists"
            continue
        seen[key] = paper.source

    for paper in papers:
        if paper.state != PaperState.PLANNED:
            continue
        assert paper.destination is not None
        try:
            paper.destination.parent.mkdir(parents=True, exist_ok=True)
            if copy:
                shutil.copy2(paper.source, paper.destination)
            else:
                shutil.move(str(paper.source), str(paper.destination))
            paper.state = PaperState.DONE
        except Exception as exc:
            paper.state = PaperState.FAILED
            paper.error = str(exc)

    return papers
