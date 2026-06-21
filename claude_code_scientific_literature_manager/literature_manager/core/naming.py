import re

from literature_manager.core.text import (
    abbreviate_journal,
    sanitize_filename,
    shorten_title,
    title_case_smart,
)


def find_existing_numbers(output_dir, prefix):
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)\b")
    numbers = []

    if not output_dir.exists():
        return numbers

    for pdf_path in output_dir.rglob("*.pdf"):
        match = pattern.match(pdf_path.name)
        if match:
            numbers.append(int(match.group(1)))

    return numbers


def positive_int(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def identifier_settings(metadata, config):
    prefix = str(config.get("identifier_prefix", "CB"))
    start_number = positive_int(config.get("start_number"), 1)

    if config.get("numbering_mode") == "category":
        category_settings = config.get("category_identifiers", {}).get(
            metadata.category,
            {},
        )
        if "prefix" in category_settings:
            prefix = str(category_settings.get("prefix", ""))
        start_number = positive_int(
            category_settings.get("start_number", start_number),
            start_number,
        )

    digits = positive_int(config.get("identifier_digits"), 3)
    return prefix, start_number, digits


def next_identifier(metadata, output_dir, config, next_numbers):
    prefix, start_number, digits = identifier_settings(metadata, config)

    if prefix not in next_numbers:
        next_numbers[prefix] = max(
            find_existing_numbers(output_dir, prefix),
            default=start_number - 1,
        ) + 1

    number = next_numbers[prefix]
    next_numbers[prefix] += 1
    return f"{prefix}{number:0{digits}d}"


def build_filename(metadata, identifier, config):
    title = shorten_title(metadata.title, int(config["title_words"]))
    title = title_case_smart(title)

    year = str(metadata.year or "0000")
    year_short = year[-2:] if len(year) >= 2 else "00"

    values = {
        "identifier": identifier,
        "last_author": sanitize_filename(metadata.last_author) or "Unknown",
        "title": sanitize_filename(title) or "Unknown Title",
        "journal": sanitize_filename(metadata.journal) or "Unknown Journal",
        "journal_abbrev": abbreviate_journal(metadata.journal),
        "year": year,
        "year_short": year_short,
        "category": sanitize_filename(metadata.category),
        "priority": metadata.priority,
    }

    filename = config["filename_template"].format(**values)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    return sanitize_filename(filename)
