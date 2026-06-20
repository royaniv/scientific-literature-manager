import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from literature_manager.core import (
    PDF_READER_AVAILABLE,
    REQUESTS_AVAILABLE,
    process_papers,
)
from literature_manager.settings import load_config


COMMAND_LINE_FLAGS = {
    "--help",
    "-h",
    "--cli",
    "--output-folder",
    "-o",
    "--config",
    "-c",
    "--prefix",
    "--start",
    "--digits",
    "--numbering-mode",
    "--category-prefix",
    "--recursive",
    "--copy",
    "--dry-run",
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Rename, classify, and organize scientific PDF files.",
    )
    parser.add_argument(
        "input_folder",
        nargs="?",
        help="Folder containing PDF files to process.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the graphical interface.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use command-line mode instead of opening the graphical interface.",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        help="Folder where renamed PDF files will be created.",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Optional JSON config file for categories, naming, and priority rules.",
    )
    parser.add_argument(
        "--prefix",
        help="Override the identifier prefix, for example CB.",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="Override the first identifier number.",
    )
    parser.add_argument(
        "--digits",
        type=int,
        help="Number of digits in the identifier number, for example 3 for CB001.",
    )
    parser.add_argument(
        "--numbering-mode",
        choices=["global", "category"],
        help="Use one sequence for all papers, or separate sequences by category.",
    )
    parser.add_argument(
        "--category-prefix",
        action="append",
        default=[],
        metavar="CATEGORY=PREFIX",
        help="Set a category prefix, for example Micelles=M or General=. Can be repeated.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan PDFs in subfolders too.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy PDFs instead of moving them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned changes without renaming or moving files.",
    )
    return parser


def apply_cli_overrides(config, args):
    if args.prefix:
        config["identifier_prefix"] = args.prefix
    if args.start is not None:
        config["start_number"] = args.start
    if args.digits is not None:
        config["identifier_digits"] = args.digits
    if args.numbering_mode:
        config["numbering_mode"] = args.numbering_mode
    for category_prefix in args.category_prefix:
        if "=" not in category_prefix:
            continue
        category, prefix = category_prefix.split("=", 1)
        category = category.strip()
        prefix = prefix.strip()
        if category:
            config.setdefault("category_identifiers", {}).setdefault(category, {})
            config["category_identifiers"][category]["prefix"] = prefix
    return config


def print_no_pdfs_message(input_dir, recursive):
    print(f"No PDF files found in: {input_dir}")
    if not recursive:
        print("Tip: add --recursive to scan subfolders too.")
    print("Tip: pass the folder that contains your PDFs as the first argument.")


def should_open_gui(raw_args):
    if "--gui" in raw_args:
        return True
    return not any(arg in COMMAND_LINE_FLAGS for arg in raw_args)


def gui_initial_paths(raw_args):
    return [
        Path(arg).expanduser()
        for arg in raw_args
        if arg != "--gui" and not arg.startswith("-")
    ]


def print_dependency_warnings():
    if not PDF_READER_AVAILABLE:
        print("Warning: pypdf is not installed, so PDF text extraction will be limited.")
        print(f'Install it for this Python with: "{sys.executable}" -m pip install pypdf')
    if not REQUESTS_AVAILABLE:
        print("Warning: requests is not installed, so Crossref lookup will be skipped.")
        print(f'Install it for this Python with: "{sys.executable}" -m pip install requests')


def main(argv=None):
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if should_open_gui(raw_args):
        from literature_manager.gui import run_gui

        run_gui(gui_initial_paths(raw_args))
        return

    parser = build_parser()
    args = parser.parse_args(raw_args)

    if args.gui:
        from literature_manager.gui import run_gui

        run_gui()
        return

    if args.input_folder is None:
        parser.error("input_folder is required in command-line mode.")

    config = apply_cli_overrides(load_config(args.config), args)

    input_dir = Path(args.input_folder).expanduser().resolve()
    output_dir = (
        Path(args.output_folder).expanduser().resolve()
        if args.output_folder
        else input_dir
    )

    if not input_dir.exists() or not input_dir.is_dir():
        parser.error(f"Input folder does not exist: {input_dir}")

    print_dependency_warnings()

    records = process_papers(
        input_dir=input_dir,
        output_dir=output_dir,
        config=config,
        dry_run=args.dry_run,
        recursive=args.recursive,
        copy=args.copy,
    )

    if not records:
        print_no_pdfs_message(input_dir, args.recursive)
        return

    action = "Previewed" if args.dry_run else "Processed"
    print(f"{action} {len(records)} PDF file(s).")
    for record in records:
        print(f"{record.source_path.name} -> {record.destination_path}")


if __name__ == "__main__":
    main()
