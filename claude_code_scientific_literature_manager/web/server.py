"""Flask web application.

Uses a Blueprint so the app factory can be tested independently.
State is kept in Flask's session for simplicity — no database.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import (Blueprint, Flask, redirect, render_template,
                   request, session, url_for)

from slm.config import Config
from slm.organize import apply, collect, plan
from slm.paper import Paper, PaperState

bp = Blueprint("slm", __name__)

_SESSION_KEY = "slm_papers"


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
            "state":       p.state.name,
            "state_label": p.state_label,
            "error":       p.error,
            "high":        p.is_high_priority,
        }
        for p in papers
    ]


def _deserialise(rows: list[dict]) -> list[Paper]:
    papers: list[Paper] = []
    for r in rows:
        p = Paper(
            source=Path(r["source"]),
            new_name=r["new_name"],
            destination=Path(r["destination"]) if r["destination"] else None,
            category=r["category"],
            priority=r["priority"],
            title=r["title"],
            journal=r["journal"],
            year=r["year"],
            author=r["author"],
            state=PaperState[r["state"]],
            error=r.get("error", ""),
        )
        papers.append(p)
    return papers


@bp.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        src = request.form.get("source_dir", "").strip()
        out = request.form.get("output_dir", "").strip()
        sort = "sort" in request.form
        recursive = "recursive" in request.form

        if not src or not Path(src).is_dir():
            error = "Source folder does not exist."
        else:
            return redirect(url_for("slm.preview",
                                    src=src, out=out,
                                    sort=int(sort), rec=int(recursive)))
    return render_template("index.html", error=error)


@bp.route("/preview")
def preview():
    src = request.args.get("src", "")
    out = request.args.get("out", "") or src
    sort = bool(int(request.args.get("sort", "0")))
    recursive = bool(int(request.args.get("rec", "0")))

    src_path = Path(src)
    out_path = Path(out)
    config = Config()

    pdfs = collect([src_path], recursive=recursive)
    papers = plan(pdfs, out_path, config, sort_into_folders=sort)

    session[_SESSION_KEY] = json.dumps(_serialise(papers))
    return render_template("preview.html", papers=papers,
                           src=src, out=out, sort=sort)


@bp.route("/apply", methods=["POST"])
def apply_view():
    raw = session.get(_SESSION_KEY)
    if not raw:
        return redirect(url_for("slm.index"))

    papers = _deserialise(json.loads(raw))
    copy = request.form.get("action") == "copy"
    results = apply(papers, copy=copy)

    done = [p for p in results if p.state == PaperState.DONE]
    failed = [p for p in results if p.state == PaperState.FAILED]
    return render_template("done.html", done=done, failed=failed)


def create_app(secret_key: str = "change-me") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = secret_key
    app.register_blueprint(bp)
    return app
