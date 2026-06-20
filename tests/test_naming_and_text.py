from pathlib import Path

from literature_manager.core.models import PaperMetadata
from literature_manager.core.naming import build_filename, identifier_settings
from literature_manager.core.text import abbreviate_journal, sanitize_filename
from literature_manager.settings import load_config


def test_sanitize_filename_removes_windows_reserved_characters():
    assert sanitize_filename('A/B:C*D?"E|.pdf') == "ABCDE.pdf"


def test_abbreviate_journal_skips_common_words():
    assert abbreviate_journal("Journal of Biological Chemistry") == "Biol Chem"


def test_identifier_settings_can_use_category_prefix():
    config = load_config(None)
    config["numbering_mode"] = "category"
    metadata = PaperMetadata(source_path=Path("paper.pdf"), category="Astro")

    assert identifier_settings(metadata, config) == ("A", 1, 3)


def test_build_filename_uses_template_values():
    config = load_config(None)
    metadata = PaperMetadata(
        source_path=Path("paper.pdf"),
        title="the lipid world and origin of life",
        journal="Journal of Theoretical Biology",
        year="2026",
        last_author="Lancet",
        category="Soup",
    )

    filename = build_filename(metadata, "CB001", config)

    assert filename == "CB001 Lancet, The Lipid World and Origin of Life, Theo Biol 26.pdf"
