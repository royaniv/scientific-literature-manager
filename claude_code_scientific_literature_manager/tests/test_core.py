"""
Tests for paper_organizer/core.py.

Run from the claude_code_scientific_literature_manager/ folder:
    ..\\.venv\\Scripts\\python.exe -m pytest tests/ -v
"""
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make sure the package is importable when pytest is invoked from the
# project root (claude_code_scientific_literature_manager/).
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_organizer.core import (
    DEFAULT_CATEGORIES, Paper, State,
    apply_plan, classify, collect_pdfs, find_doi,
    guess_from_text, make_filename, plan_papers, read_text,
)


# ── find_doi ─────────────────────────────────────────────────────────────────

class TestFindDoi:
    def test_found_basic(self):
        text = "See https://doi.org/10.1038/nature12373 for details."
        assert find_doi(text) == "10.1038/nature12373"

    def test_found_with_slashes(self):
        text = "DOI: 10.1016/j.cell.2020.04.007"
        assert find_doi(text) == "10.1016/j.cell.2020.04.007"

    def test_strips_trailing_period(self):
        text = "Reference: 10.1073/pnas.1234567890."
        assert not find_doi(text).endswith(".")

    def test_strips_trailing_comma(self):
        text = "doi 10.1073/pnas.1234567890, see above"
        assert not find_doi(text).endswith(",")

    def test_not_found(self):
        assert find_doi("No DOI in this string.") == ""

    def test_empty_string(self):
        assert find_doi("") == ""


# ── guess_from_text ───────────────────────────────────────────────────────────

class TestGuessFromText:
    def test_extracts_year(self):
        text = "Published in 2021 by Nature."
        result = guess_from_text(text)
        assert result["year"] == "2021"

    def test_year_fallback(self):
        text = "No date here."
        result = guess_from_text(text)
        assert result["year"] == "0000"

    def test_longest_line_is_title(self):
        text = "Short\nThis is a much longer line that should be the title\nEnd"
        result = guess_from_text(text)
        assert "longer line" in result["title"]

    def test_returns_dict_keys(self):
        result = guess_from_text("Some text 2019.")
        assert {"title", "journal", "year", "author"} == set(result.keys())


# ── classify ─────────────────────────────────────────────────────────────────

class TestClassify:
    def _paper(self, title=""):
        return Paper(source=Path("x.pdf"), title=title)

    def test_micelles_keyword(self):
        # "micellar" is an exact word; "micelles" would NOT match keyword "micelle"
        # due to the word-boundary regex in _kw_match.
        p = self._paper("Micellar structures in amphiphilic systems")
        classify(p, "")
        assert p.category == "Micelles"

    def test_chiral_keyword(self):
        p = self._paper("Chirality in Amino Acids")
        classify(p, "")
        assert p.category == "Chiral"

    def test_soup_keyword_in_text(self):
        p = self._paper()
        classify(p, "origin of life hypothesis tested")
        assert p.category == "Soup"

    def test_astro_keyword(self):
        p = self._paper("Biosignatures on Enceladus")
        classify(p, "")
        assert p.category == "Astro"

    def test_light_keyword(self):
        p = self._paper("Photochemistry under UV light")
        classify(p, "")
        assert p.category == "Light"

    def test_organ_bactr_keyword(self):
        p = self._paper("Bacterial growth in saline")
        classify(p, "")
        assert p.category == "OrganBactr"

    def test_general_fallback(self):
        p = self._paper("Random unrelated title")
        classify(p, "no matching words here")
        assert p.category == "General"

    def test_priority_high_by_keyword(self):
        p = self._paper()
        classify(p, "GARD model for composome")
        assert p.priority == "high"

    def test_priority_high_by_author(self):
        p = Paper(source=Path("x.pdf"), author="Lancet")
        classify(p, "")
        assert p.priority == "high"

    def test_priority_normal_default(self):
        p = self._paper("Some paper")
        classify(p, "nothing special here")
        assert p.priority == "normal"

    def test_keywords_recorded(self):
        p = self._paper("Micellar structures")
        classify(p, "")
        assert "micellar" in p.keywords

    def test_custom_categories(self):
        cats = {"Cheese": ["cheddar", "gouda"], "General": []}
        p = self._paper("Gouda ripening process")
        classify(p, "", categories=cats)
        assert p.category == "Cheese"


# ── make_filename ─────────────────────────────────────────────────────────────

class TestMakeFilename:
    def _paper(self, **kw):
        defaults = dict(source=Path("x.pdf"), title="The Origin of Life",
                        author="Lancet", journal="Nature Chemistry",
                        year="2021", category="Soup")
        defaults.update(kw)
        return Paper(**defaults)

    def test_standard_template(self):
        p = self._paper()
        name = make_filename(p, "CB001", "{id} {author}, {title}, {journal} {year_short}.pdf")
        assert name.startswith("CB001 Lancet")
        assert name.endswith("21.pdf")
        # {journal} is abbreviated ("Nature Chemistry" → "Natu Chem");
        # check the abbreviated form rather than the full name.
        assert "Natu" in name

    def test_year_short(self):
        p = self._paper(year="2019")
        name = make_filename(p, "X01", "{year_short}.pdf")
        assert name == "19.pdf"

    def test_category_placeholder(self):
        p = self._paper()
        name = make_filename(p, "CB001", "{category}.pdf")
        assert name == "Soup.pdf"

    def test_appends_pdf_if_missing(self):
        p = self._paper()
        name = make_filename(p, "CB001", "{id}")
        assert name.endswith(".pdf")

    def test_strips_unsafe_chars(self):
        p = self._paper(title='Title: "With" <Special> Chars?')
        name = make_filename(p, "CB001", "{title}.pdf")
        assert "/" not in name
        assert "?" not in name
        assert ":" not in name

    def test_journal_abbreviated(self):
        p = self._paper(journal="Journal of Chemical Physics")
        name = make_filename(p, "CB001", "{journal}.pdf")
        # abbreviated — should NOT contain full "Journal of Chemical Physics"
        assert "Journal of Chemical Physics" not in name

    def test_journal_full(self):
        p = self._paper(journal="Nature Chemistry")
        name = make_filename(p, "CB001", "{journal_full}.pdf")
        assert "Nature Chemistry" in name


# ── collect_pdfs ──────────────────────────────────────────────────────────────

class TestCollectPdfs:
    def test_finds_pdfs_flat(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"")
        (tmp_path / "b.pdf").write_bytes(b"")
        (tmp_path / "note.txt").write_bytes(b"")
        result = collect_pdfs([tmp_path], recursive=False)
        names = {p.name for p in result}
        assert names == {"a.pdf", "b.pdf"}

    def test_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "top.pdf").write_bytes(b"")
        (sub / "nested.pdf").write_bytes(b"")
        result = collect_pdfs([tmp_path], recursive=True)
        names = {p.name for p in result}
        assert "top.pdf" in names and "nested.pdf" in names

    def test_not_recursive_ignores_subfolders(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "hidden.pdf").write_bytes(b"")
        result = collect_pdfs([tmp_path], recursive=False)
        assert result == []

    def test_deduplicates(self, tmp_path):
        f = tmp_path / "dup.pdf"
        f.write_bytes(b"")
        result = collect_pdfs([tmp_path, tmp_path], recursive=False)
        assert len(result) == 1

    def test_empty_folder(self, tmp_path):
        assert collect_pdfs([tmp_path]) == []

    def test_single_file_argument(self, tmp_path):
        f = tmp_path / "paper.pdf"
        f.write_bytes(b"")
        result = collect_pdfs([f])
        assert len(result) == 1 and result[0].name == "paper.pdf"


# ── apply_plan ────────────────────────────────────────────────────────────────

class TestApplyPlan:
    def _planned_paper(self, src: Path, dst: Path) -> Paper:
        p = Paper(source=src, destination=dst, state=State.PLANNED)
        return p

    def test_copy_marks_done(self, tmp_path):
        src = tmp_path / "input.pdf"
        src.write_bytes(b"%PDF-1.4 fake")
        dst = tmp_path / "out" / "result.pdf"
        p = self._planned_paper(src, dst)
        apply_plan([p], copy=True)
        assert p.state == State.DONE
        assert dst.exists()
        assert src.exists()        # original kept

    def test_move_marks_done(self, tmp_path):
        src = tmp_path / "input.pdf"
        src.write_bytes(b"%PDF-1.4 fake")
        dst = tmp_path / "out" / "result.pdf"
        p = self._planned_paper(src, dst)
        apply_plan([p], copy=False)
        assert p.state == State.DONE
        assert dst.exists()
        assert not src.exists()    # original gone

    def test_missing_source_marks_failed(self, tmp_path):
        src = tmp_path / "nonexistent.pdf"
        dst = tmp_path / "out" / "result.pdf"
        p = self._planned_paper(src, dst)
        apply_plan([p], copy=True)
        assert p.state == State.FAILED
        assert p.error != ""

    def test_creates_destination_directory(self, tmp_path):
        src = tmp_path / "in.pdf"
        src.write_bytes(b"%PDF fake")
        dst = tmp_path / "a" / "b" / "c" / "out.pdf"
        p = self._planned_paper(src, dst)
        apply_plan([p], copy=True)
        assert dst.parent.is_dir()

    def test_skips_non_planned(self, tmp_path):
        src = tmp_path / "in.pdf"
        src.write_bytes(b"%PDF fake")
        dst = tmp_path / "out.pdf"
        p = Paper(source=src, destination=dst, state=State.PENDING)
        apply_plan([p], copy=True)
        assert p.state == State.PENDING   # unchanged
        assert not dst.exists()


# ── plan_papers (end-to-end, with mocked I/O) ────────────────────────────────

class TestPlanPapers:
    def test_returns_one_paper_per_pdf(self, tmp_path):
        pdfs = []
        for name in ("alpha.pdf", "beta.pdf", "gamma.pdf"):
            f = tmp_path / name
            f.write_bytes(b"")
            pdfs.append(f)

        with patch("paper_organizer.core.read_text", return_value=""), \
             patch("paper_organizer.core.fetch_crossref", return_value={}):
            results = plan_papers(pdfs, tmp_path / "out")

        assert len(results) == 3

    def test_identifiers_increment(self, tmp_path):
        pdfs = [tmp_path / f"{i}.pdf" for i in range(3)]
        for f in pdfs:
            f.write_bytes(b"")

        with patch("paper_organizer.core.read_text", return_value=""), \
             patch("paper_organizer.core.fetch_crossref", return_value={}):
            results = plan_papers(pdfs, tmp_path / "out", prefix="T", digits=2, start=1)

        ids = [r.new_name[:3] for r in results]   # e.g. "T01"
        assert ids == ["T01", "T02", "T03"]

    def test_state_is_planned(self, tmp_path):
        f = tmp_path / "paper.pdf"
        f.write_bytes(b"")
        with patch("paper_organizer.core.read_text", return_value=""), \
             patch("paper_organizer.core.fetch_crossref", return_value={}):
            results = plan_papers([f], tmp_path / "out")
        assert all(r.state == State.PLANNED for r in results)

    def test_crossref_metadata_used(self, tmp_path):
        f = tmp_path / "paper.pdf"
        f.write_bytes(b"")
        meta = {"title": "Deep Learning", "author": "LeCun",
                "journal": "Nature", "year": "2015"}
        with patch("paper_organizer.core.read_text", return_value="10.1038/fake"), \
             patch("paper_organizer.core.fetch_crossref", return_value=meta):
            results = plan_papers([f], tmp_path / "out")
        assert results[0].author == "LeCun"
        assert results[0].year   == "2015"

    def test_sort_into_folders(self, tmp_path):
        f = tmp_path / "micelle.pdf"
        f.write_bytes(b"")
        with patch("paper_organizer.core.read_text", return_value="micelle structure"), \
             patch("paper_organizer.core.fetch_crossref", return_value={}):
            results = plan_papers([f], tmp_path / "out", sort_into_folders=True)
        assert results[0].category == "Micelles"
        assert "Micelles" in str(results[0].destination)

    def test_progress_callback_called(self, tmp_path):
        pdfs = [tmp_path / f"{i}.pdf" for i in range(2)]
        for f in pdfs:
            f.write_bytes(b"")
        calls = []
        with patch("paper_organizer.core.read_text", return_value=""), \
             patch("paper_organizer.core.fetch_crossref", return_value={}):
            plan_papers(pdfs, tmp_path / "out", on_progress=lambda i, t, n: calls.append(i))
        # called once per file + once at the end
        assert len(calls) >= len(pdfs)


# ── Paper dataclass helpers ───────────────────────────────────────────────────

class TestPaperHelpers:
    def test_is_high_priority_true(self):
        p = Paper(source=Path("x.pdf"), priority="high")
        assert p.is_high_priority is True

    def test_is_high_priority_false(self):
        p = Paper(source=Path("x.pdf"), priority="normal")
        assert p.is_high_priority is False

    def test_year_short(self):
        p = Paper(source=Path("x.pdf"), year="2023")
        assert p.year_short == "23"

    def test_year_short_fallback(self):
        p = Paper(source=Path("x.pdf"), year="0")
        assert p.year_short == "00"

    def test_status_label_planned(self):
        p = Paper(source=Path("x.pdf"), state=State.PLANNED)
        assert p.status_label == "Preview"

    def test_status_label_done(self):
        p = Paper(source=Path("x.pdf"), state=State.DONE)
        assert "Done" in p.status_label

    def test_status_label_failed(self):
        p = Paper(source=Path("x.pdf"), state=State.FAILED, error="disk full")
        assert "disk full" in p.status_label
