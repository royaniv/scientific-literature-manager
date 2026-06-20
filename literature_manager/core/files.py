import shutil
from pathlib import Path

from literature_manager.core.metadata import metadata_for_pdf
from literature_manager.core.naming import build_filename, next_identifier
from literature_manager.core.text import sanitize_filename


def unique_path(path, reserved_paths=None):
    reserved_paths = reserved_paths or set()
    if not path.exists() and path not in reserved_paths:
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists() and candidate not in reserved_paths:
            return candidate
        counter += 1


def category_output_dir(output_dir, category):
    folder_name = sanitize_filename(category) or "General"
    return output_dir / folder_name


def collect_pdfs(input_dir, recursive):
    paths = input_dir.rglob("*") if recursive else input_dir.iterdir()
    return sorted(
        path
        for path in paths
        if path.is_file() and path.suffix.lower() == ".pdf"
    )


def collect_pdfs_from_paths(paths, recursive=False):
    pdf_paths = []
    seen_paths = set()

    for path in paths:
        if path.is_file() and path.suffix.lower() == ".pdf":
            candidates = [path]
        elif path.is_dir():
            candidates = collect_pdfs(path, recursive)
        else:
            candidates = []

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen_paths:
                seen_paths.add(resolved)
                pdf_paths.append(resolved)

    return sorted(pdf_paths)


def plan_pdf_paths(
    pdf_paths,
    output_dir,
    config,
    separate_category_folders=False,
    rename_files=True,
):
    reserved_destinations = set()
    records = []
    next_numbers = {}

    for pdf_path in pdf_paths:
        metadata = metadata_for_pdf(pdf_path, config)

        if rename_files:
            identifier = next_identifier(metadata, output_dir, config, next_numbers)
            metadata.new_filename = build_filename(metadata, identifier, config)
        else:
            metadata.new_filename = sanitize_filename(pdf_path.name) or pdf_path.name

        destination_dir = output_dir
        if separate_category_folders:
            destination_dir = category_output_dir(output_dir, metadata.category)

        destination = unique_path(
            destination_dir / metadata.new_filename,
            reserved_destinations,
        )
        reserved_destinations.add(destination)
        metadata.destination_path = destination
        metadata.action = "preview"

        records.append(metadata)

    return records


def apply_planned_records(records, copy=False):
    seen_destinations = {}

    for record in records:
        if record.destination_path is None:
            raise ValueError(f"Missing destination for {record.source_path.name}")

        destination = Path(record.destination_path)
        destination_key = str(destination.resolve()).lower()
        if destination_key in seen_destinations:
            first_source = seen_destinations[destination_key]
            raise ValueError(
                "Two files are planned for the same output: "
                f"{first_source.name} and {record.source_path.name}"
            )
        seen_destinations[destination_key] = record.source_path

        if destination.exists():
            raise FileExistsError(f"Destination already exists: {destination}")

    for record in records:
        destination = Path(record.destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if copy:
            shutil.copy2(record.source_path, destination)
            record.action = "copied"
        else:
            shutil.move(str(record.source_path), str(destination))
            record.action = "moved"

    return records


def process_pdf_paths(
    pdf_paths,
    output_dir,
    config,
    dry_run=False,
    copy=False,
    separate_category_folders=False,
    rename_files=True,
):
    records = plan_pdf_paths(
        pdf_paths,
        output_dir,
        config,
        separate_category_folders=separate_category_folders,
        rename_files=rename_files,
    )

    if dry_run:
        return records

    return apply_planned_records(records, copy=copy)


def process_papers(
    input_dir,
    output_dir,
    config,
    dry_run=False,
    recursive=False,
    copy=False,
    separate_category_folders=False,
    rename_files=True,
):
    pdf_paths = collect_pdfs(input_dir, recursive)
    return process_pdf_paths(
        pdf_paths,
        output_dir,
        config,
        dry_run=dry_run,
        copy=copy,
        separate_category_folders=separate_category_folders,
        rename_files=rename_files,
    )
