from literature_manager.core.classifier import (
    classify_paper,
    keyword_matches,
    metadata_haystack,
    prioritize_paper,
)
from literature_manager.core.files import (
    apply_planned_records,
    category_output_dir,
    collect_pdfs,
    collect_pdfs_from_paths,
    plan_pdf_paths,
    process_papers,
    process_pdf_paths,
    unique_path,
)
from literature_manager.core.metadata import (
    PDF_READER_AVAILABLE,
    REQUESTS_AVAILABLE,
    extract_text,
    find_doi,
    metadata_for_pdf,
    query_crossref,
)
from literature_manager.core.models import PaperMetadata
from literature_manager.core.naming import (
    build_filename,
    find_existing_numbers,
    identifier_settings,
    next_identifier,
    positive_int,
)
from literature_manager.core.text import (
    abbreviate_journal,
    clean_text,
    sanitize_filename,
    shorten_title,
    title_case_smart,
)
