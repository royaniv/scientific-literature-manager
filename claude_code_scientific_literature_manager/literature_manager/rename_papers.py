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


def clean_input(value):
    return value.strip().strip('"')


def ask_yes_no(question, default):
    answer = input(question).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def input_folder_from_user():
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()

    folder = clean_input(input("Folder with PDF files: "))
    return Path(folder).expanduser().resolve()


def output_folder_from_user(input_dir):
    answer = clean_input(
        input("Output folder, or press Enter to use the same folder: "),
    )
    if not answer:
        return input_dir
    return Path(answer).expanduser().resolve()


def print_dependency_warnings():
    if not PDF_READER_AVAILABLE:
        print("Warning: pypdf is not installed, so PDF text extraction will be limited.")
    if not REQUESTS_AVAILABLE:
        print("Warning: requests is not installed, so online metadata lookup will be skipped.")


def print_records(records, dry_run):
    action = "Previewed" if dry_run else "Processed"
    print(f"{action} {len(records)} PDF file(s).")
    for record in records:
        print(f"{record.source_path.name} -> {record.destination_path}")


def main():
    input_dir = input_folder_from_user()
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input folder does not exist: {input_dir}")
        return

    output_dir = output_folder_from_user(input_dir)
    dry_run = ask_yes_no("Preview only, without changing files? [Y/n]: ", True)
    copy = ask_yes_no("Copy files instead of moving them? [Y/n]: ", True)
    recursive = ask_yes_no("Include PDFs in subfolders? [y/N]: ", False)

    print_dependency_warnings()
    records = process_papers(
        input_dir=input_dir,
        output_dir=output_dir,
        config=load_config(None),
        dry_run=dry_run,
        recursive=recursive,
        copy=copy,
    )

    if not records:
        print(f"No PDF files found in: {input_dir}")
        return

    print_records(records, dry_run)


if __name__ == "__main__":
    main()
