"""Command-line interface using argparse subcommands.

The original used interactive input() prompts.
Here every option is a flag so the tool is scriptable.

  python main.py preview /path/to/pdfs
  python main.py apply   /path/to/pdfs --output /path/to/out --move --sort
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from slm.config import Config
from slm.organize import apply, collect, plan
from slm.paper import PaperState


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="slm",
        description="Scientific Literature Manager — rename and sort PDFs.",
    )
    p.add_argument("--config", metavar="FILE", type=Path, help="Path to config JSON.")

    sub = p.add_subparsers(dest="command", required=True)

    _add_common = lambda s: (
        s.add_argument("sources", nargs="+", type=Path, metavar="PATH",
                       help="PDF files or directories to process."),
        s.add_argument("--output", "-o", type=Path, default=None,
                       metavar="DIR", help="Destination directory (default: source dir)."),
        s.add_argument("--sort", action="store_true",
                       help="Organise into per-category subfolders."),
        s.add_argument("--recursive", "-r", action="store_true",
                       help="Recurse into subdirectories."),
    )

    preview = sub.add_parser("preview", help="Show what would happen without moving anything.")
    _add_common(preview)

    apply_cmd = sub.add_parser("apply", help="Actually rename/copy/move files.")
    _add_common(apply_cmd)
    apply_cmd.add_argument("--move", action="store_true",
                           help="Move instead of copy (default: copy).")
    apply_cmd.add_argument("--no-rename", dest="rename", action="store_false",
                           help="Keep original filenames.")

    return p


def _progress(i: int, total: int, name: str) -> None:
    if not name:
        sys.stderr.write(f"\r  Done.                    \n")
        return
    bar_w = 30
    filled = int(bar_w * i / max(total, 1))
    bar = "#" * filled + "-" * (bar_w - filled)
    sys.stderr.write(f"\r  [{bar}] {i}/{total} {name[:50]:<50}")
    sys.stderr.flush()


def _fmt_row(paper) -> str:
    arrow = "→" if paper.destination else "?"
    dest = paper.destination.name if paper.destination else "?"
    flag = "[HIGH] " if paper.is_high_priority else ""
    return f"  {flag}{paper.source.name}\n      {arrow} {dest}  [{paper.category}]"


def run() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    config = Config.from_file(args.config) if args.config else Config()

    pdfs = collect(args.sources, recursive=args.recursive)
    if not pdfs:
        print("No PDFs found.")
        return 1

    output = args.output or pdfs[0].parent

    print(f"Planning {len(pdfs)} file(s)…")
    papers = plan(pdfs, output, config,
                  sort_into_folders=args.sort,
                  rename=getattr(args, "rename", True),
                  on_progress=_progress)

    if args.command == "preview":
        for paper in papers:
            print(_fmt_row(paper))
        done = sum(1 for p in papers if p.state == PaperState.PLANNED)
        print(f"\n{done}/{len(papers)} planned.  Run 'apply' to execute.")
        return 0

    # apply
    print("Applying…")
    results = apply(papers, copy=not args.move)

    done = [p for p in results if p.state == PaperState.DONE]
    failed = [p for p in results if p.state == PaperState.FAILED]

    for p in done:
        action = "moved" if args.move else "copied"
        print(f"  OK  {action} → {p.destination.name}")
    for p in failed:
        print(f"  FAIL {p.source.name}: {p.error}")

    print(f"\n{len(done)} succeeded, {len(failed)} failed.")
    return 0 if not failed else 2
