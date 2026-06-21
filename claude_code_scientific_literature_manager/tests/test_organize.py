"""Tests for slm.organize — collect() and apply() mechanics."""
import shutil
import tempfile
from pathlib import Path

import pytest
from slm.config import Config
from slm.organize import apply, collect, plan
from slm.paper import Paper, PaperState


@pytest.fixture
def tmp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


def make_dummy_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4 dummy")


def test_collect_files(tmp_dir):
    pdf1 = tmp_dir / "a.pdf"
    pdf2 = tmp_dir / "b.pdf"
    txt  = tmp_dir / "c.txt"
    for f in (pdf1, pdf2, txt):
        make_dummy_pdf(f)
    result = collect([tmp_dir])
    assert len(result) == 2
    assert txt.resolve() not in result


def test_collect_deduplication(tmp_dir):
    pdf = tmp_dir / "a.pdf"
    make_dummy_pdf(pdf)
    result = collect([pdf, pdf, tmp_dir])
    assert len(result) == 1


def test_collect_recursive(tmp_dir):
    sub = tmp_dir / "sub"
    sub.mkdir()
    make_dummy_pdf(sub / "deep.pdf")
    assert len(collect([tmp_dir], recursive=False)) == 0
    assert len(collect([tmp_dir], recursive=True)) == 1


def test_apply_sets_done(tmp_dir):
    out = tmp_dir / "out"
    out.mkdir()
    pdf = tmp_dir / "a.pdf"
    make_dummy_pdf(pdf)

    paper = Paper(source=pdf, new_name="a_renamed.pdf",
                  destination=out / "a_renamed.pdf",
                  state=PaperState.PLANNED)
    apply([paper])
    assert paper.state == PaperState.DONE
    assert (out / "a_renamed.pdf").exists()


def test_apply_fails_on_duplicate_destination(tmp_dir):
    out = tmp_dir / "out"
    out.mkdir()
    pdf1 = tmp_dir / "a.pdf"
    pdf2 = tmp_dir / "b.pdf"
    make_dummy_pdf(pdf1)
    make_dummy_pdf(pdf2)

    dest = out / "same.pdf"
    p1 = Paper(source=pdf1, new_name="same.pdf", destination=dest, state=PaperState.PLANNED)
    p2 = Paper(source=pdf2, new_name="same.pdf", destination=dest, state=PaperState.PLANNED)

    apply([p1, p2])
    done = [p for p in (p1, p2) if p.state == PaperState.DONE]
    fail = [p for p in (p1, p2) if p.state == PaperState.FAILED]
    assert len(done) == 1
    assert len(fail) == 1
