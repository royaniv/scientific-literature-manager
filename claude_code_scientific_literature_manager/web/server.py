"""Flask web application.

Uses a Blueprint so the app factory can be tested independently.
Paper plan data is stored in a temp JSON file (not the session cookie)
to avoid the 4 KB cookie size limit when processing many PDFs.
The file path is referenced by a short token stored in the session.
"""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path

from flask import (Blueprint, Flask, redirect, render_template,
                   request, session, url_for)

from slm.config import Config
from slm.organize import apply, collect, plan
from slm.paper import Paper, PaperState

bp = Blueprint("slm", __name__)

_PLAN_TOKEN_KEY = "slm_plan_token"
_PLAN_DIR = Path(tempfile.gettempdir()) / "slm_plans"


def _plan_path(token: str) -> Path:
    _PLAN_DIR.mkdir(parents=True, exist_ok=True)
    return _PLAN_DIR / f"{token}.json"


def _serialise(papers: list[Paper]) -> list[dict]:
    return [
        {
            "source":      str(p.source),
            "new_name":    p.new_name,
            "destination": str(p.destination) if p.destination else "",
            "category":    p.category,
            "priority":    p.priority,
            "title":       p.title,
            "journal":     p.journal,
            "year":        p.year,
            "author":      p.author,
            "keywords":    p.keywords,
            "state":       p.state.name,
            "error":       p.error,
        }
        for p in papers
    ]


def _deserialise(rows: list[dict]) -> list[Paper]:
    papers: list[Paper] = []
    for r in rows:
        p = Paper(
            source=Path(r["source"]),
            new_name=r["new_name"],
            destination=Path(r["destination"]) if r.get("destination") else None,
            category=r.get("category", "General"),
            priority=r.get("priority", "normal"),
            title=r.get("title", "Unknown Title"),
            journal=r.get("journal", "Unknown Journal"),
            year=r.get("year", "0000"),
            author=r.get("author", "Unknown"),
            keywords=r.get("keywords", []),
            state=PaperState[r.get("state", "PENDING")],
            error=r.get("error", ""),
        )
        papers.append(p)
    return papers


def _save_plan(papers: list[Paper]) -> str:
    token = secrets.token_urlsafe(16)
    _plan_path(token).write_text(json.dumps(_serialise(papers)), encoding="utf-8")
    return token


def _load_plan(token: str) -> list[Paper] | None:
    path = _plan_path(token)
    if not path.exists():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return _deserialise(rows)
    except Exception:
        return None


@bp.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        src = request.form.get("source_dir", "").strip()
        out = request.form.get("output_dir", "").strip()
        sort = "sort" in request.form
        recursive = "recursive" in request.form

        if not src or not Path(src).is_dir():
            error = "Source folder does not exist or was not entered."
        else:
            return redirect(url_for("slm.preview",
                                    src=src,
                                    out=out or src,
                                    sort=int(sort),
                                    rec=int(recursive)))
    return render_template("index.html", error=error)


@bp.route("/preview")
def preview():
    src = request.args.get("src", "")
    out = request.args.get("out", "") or src
    sort = bool(int(request.args.get("sort", "0")))
    recursive = bool(int(request.args.get("rec", "0")))

    src_path = Path(src)
    out_path = Path(out)

    if not src_path.is_dir():
        return redirect(url_for("slm.index"))

    config = Config()
    pdfs = collect([src_path], recursive=recursive)
    papers = plan(pdfs, out_path, config, sort_into_folders=sort)

    token = _save_plan(papers)
    session[_PLAN_TOKEN_KEY] = token

    return render_template("preview.html", papers=papers,
                           src=src, out=out, sort=sort, count=len(papers))


@bp.route("/apply", methods=["POST"])
def apply_view():
    token = session.get(_PLAN_TOKEN_KEY)
    if not token:
        return redirect(url_for("slm.index"))

    papers = _load_plan(token)
    if papers is None:
        return redirect(url_for("slm.index"))

    copy = request.form.get("action") != "move"
    results = apply(papers, copy=copy)

    done = [p for p in results if p.state == PaperState.DONE]
    failed = [p for p in results if p.state == PaperState.FAILED]

    try:
        _plan_path(token).unlink(missing_ok=True)
    except Exception:
        pass

    return render_template("done.html", done=done, failed=failed)


def create_app(secret_key: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = secret_key or os.environ.get("SLM_SECRET", secrets.token_hex(16))
    app.register_blueprint(bp)
    return app
