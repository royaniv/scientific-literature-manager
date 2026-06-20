from pathlib import Path

import pytest

from literature_manager.core import files
from literature_manager.core.models import PaperMetadata
from literature_manager.settings import load_config


def test_collect_pdfs_from_paths_deduplicates_and_sorts(tmp_path):
    first = tmp_path / "a.pdf"
    second = tmp_path / "sub" / "b.PDF"
    ignored = tmp_path / "notes.txt"
    second.parent.mkdir()
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    ignored.write_text("ignore", encoding="utf-8")

    pdfs = files.collect_pdfs_from_paths([tmp_path, first], recursive=True)

    assert pdfs == sorted([first.resolve(), second.resolve()])


def test_plan_pdf_paths_uses_unique_destinations(monkeypatch, tmp_path):
    source_a = tmp_path / "a.pdf"
    source_b = tmp_path / "b.pdf"
    output_dir = tmp_path / "organized"
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")

    def fake_metadata_for_pdf(pdf_path, _config):
        return PaperMetadata(
            source_path=pdf_path,
            title="Same Title",
            journal="Journal of Testing",
            year="2026",
            last_author="Tester",
            category="General",
        )

    monkeypatch.setattr(files, "metadata_for_pdf", fake_metadata_for_pdf)
    config = load_config(None)
    config["identifier_prefix"] = "T"
    config["filename_template"] = "{last_author}, {title}.pdf"

    records = files.plan_pdf_paths([source_a, source_b], output_dir, config)

    assert records[0].destination_path == output_dir / "Tester, Same Title.pdf"
    assert records[1].destination_path == output_dir / "Tester, Same Title (2).pdf"
    assert all(record.action == "preview" for record in records)


def test_apply_planned_records_copies_files(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "out" / "renamed.pdf"
    source.write_text("content", encoding="utf-8")
    record = PaperMetadata(source_path=source, destination_path=destination)

    files.apply_planned_records([record], copy=True)

    assert source.exists()
    assert destination.read_text(encoding="utf-8") == "content"
    assert record.action == "copied"


def test_apply_planned_records_rejects_duplicate_destinations(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    destination = tmp_path / "same.pdf"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    records = [
        PaperMetadata(source_path=first, destination_path=destination),
        PaperMetadata(source_path=second, destination_path=destination),
    ]

    with pytest.raises(ValueError, match="same output"):
        files.apply_planned_records(records, copy=True)
