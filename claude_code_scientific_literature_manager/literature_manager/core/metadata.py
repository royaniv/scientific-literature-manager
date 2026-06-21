import re

from literature_manager.core.classifier import classify_paper, prioritize_paper
from literature_manager.core.models import PaperMetadata
from literature_manager.core.text import abbreviate_journal, clean_text

try:
    import requests
except ImportError:
    requests = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


PDF_READER_AVAILABLE = PdfReader is not None
REQUESTS_AVAILABLE = requests is not None


def extract_text(pdf_path, max_pages):
    if PdfReader is None:
        return ""

    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return ""

    chunks = []
    for page in reader.pages[:max_pages]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(chunks)


def find_doi(text):
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text or "", re.IGNORECASE)
    if not match:
        return ""
    return match.group(0).rstrip(").,;]")


def first_value(data, key, default):
    values = data.get(key) or []
    if not values:
        return default
    return values[0] or default


def year_from_crossref(data):
    issued = data.get("issued", {})
    date_parts = issued.get("date-parts", [])
    if date_parts and date_parts[0]:
        return str(date_parts[0][0])
    return "0000"


def query_crossref(doi):
    if not doi or requests is None:
        return {}

    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "scientific-literature-manager/0.1"}

    try:
        response = requests.get(url, timeout=12, headers=headers)
        response.raise_for_status()
        data = response.json().get("message", {})
    except Exception:
        return {}

    authors = data.get("author", [])
    last_author = "Unknown"
    if authors:
        last_author = authors[-1].get("family") or authors[-1].get("name") or "Unknown"

    journal = first_value(data, "container-title", "Unknown Journal")
    return {
        "title": first_value(data, "title", "Unknown Title"),
        "journal": journal,
        "journal_abbrev": abbreviate_journal(journal),
        "year": year_from_crossref(data),
        "last_author": last_author,
    }


def fallback_metadata(text):
    lines = [clean_text(line) for line in (text or "").splitlines()]
    lines = [line for line in lines if line]

    title = "Unknown Title"
    if lines:
        title = max(lines[:12], key=len)

    last_author = "Unknown"
    for line in lines[:12]:
        if "," in line and len(line.split()) <= 12:
            last_author = line.split(",")[-1].strip() or "Unknown"
            break

    year_match = re.search(r"(19|20)\d{2}", text or "")
    year = year_match.group(0) if year_match else "0000"

    return {
        "title": title,
        "journal": "Unknown Journal",
        "journal_abbrev": "Unknown",
        "year": year,
        "last_author": last_author,
    }


def metadata_for_pdf(pdf_path, config):
    text = extract_text(pdf_path, int(config["text_pages"]))
    doi = find_doi(text)

    found = query_crossref(doi)
    if not found:
        found = fallback_metadata(text)

    metadata = PaperMetadata(
        source_path=pdf_path,
        doi=doi,
        title=found["title"],
        journal=found["journal"],
        journal_abbrev=found.get("journal_abbrev") or abbreviate_journal(found["journal"]),
        year=found["year"],
        last_author=found["last_author"],
    )

    metadata.category, metadata.matched_keywords = classify_paper(
        metadata,
        text,
        config["categories"],
    )
    metadata.priority = prioritize_paper(metadata, text, config["priority_rules"])
    return metadata
