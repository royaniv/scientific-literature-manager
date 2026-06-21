"""
web.py — Flask web interface for Paper Organizer.

Server-Sent Events stream scan/apply progress.
Plan is stored as a JSON temp file (plan token kept in cookie).
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import (
    Blueprint, Flask, Response, jsonify, render_template,
    request, session, stream_with_context,
)

from paper_organizer.core import (
    DEFAULT_CATEGORIES, Paper, State,
    apply_plan, collect_pdfs, plan_papers,
)

# ── Temp plan storage ─────────────────────────────────────────────────────────

_PLAN_DIR = Path(os.environ.get("TEMP", "/tmp")) / "slm_plans"
_PLAN_DIR.mkdir(parents=True, exist_ok=True)

_PROGRESS: dict[str, queue.Queue] = {}  # token → progress event queue


def _plan_path(token: str) -> Path:
    return _PLAN_DIR / f"{token}.json"


def _save_plan(token: str, papers: list[Paper]) -> None:
    data = [_paper_to_dict(p) for p in papers]
    _plan_path(token).write_text(json.dumps(data, default=str), encoding="utf-8")


def _load_plan(token: str) -> list[Paper] | None:
    p = _plan_path(token)
    if not p.exists():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [_dict_to_paper(r) for r in raw]


def _paper_to_dict(p: Paper) -> dict:
    return {
        "source":      str(p.source),
        "title":       p.title,
        "author":      p.author,
        "journal":     p.journal,
        "year":        p.year,
        "doi":         p.doi,
        "category":    p.category,
        "priority":    p.priority,
        "keywords":    p.keywords,
        "new_name":    p.new_name,
        "destination": str(p.destination) if p.destination else None,
        "state":       p.state.name,
        "error":       p.error,
    }


def _dict_to_paper(d: dict) -> Paper:
    p = Paper(
        source      = Path(d["source"]),
        title       = d.get("title", "Unknown Title"),
        author      = d.get("author", "Unknown"),
        journal     = d.get("journal", "Unknown Journal"),
        year        = d.get("year", "0000"),
        doi         = d.get("doi", ""),
        category    = d.get("category", "General"),
        priority    = d.get("priority", "normal"),
        keywords    = d.get("keywords", []),
        new_name    = d.get("new_name", ""),
        destination = Path(d["destination"]) if d.get("destination") else None,
        state       = State[d.get("state", "PENDING")],
        error       = d.get("error", ""),
    )
    return p


# ── Blueprint ─────────────────────────────────────────────────────────────────

bp = Blueprint("organizer", __name__,
               template_folder="templates",
               static_folder=None)


@bp.route("/")
def index():
    return render_template("index.html",
                           categories=list(DEFAULT_CATEGORIES.keys()))


@bp.route("/scan", methods=["POST"])
def scan():
    data      = request.get_json(force=True)
    src       = data.get("source", "").strip()
    out       = data.get("output", "").strip()
    prefix    = data.get("prefix", "CB").strip() or "CB"
    digits    = max(1, int(data.get("digits", 3)))
    start     = max(1, int(data.get("start", 1)))
    template  = data.get("template", "{id} {author}, {title}, {journal} {year_short}.pdf")
    recursive = bool(data.get("recursive", True))
    sort_dirs = bool(data.get("sort_into_folders", False))

    if not src or not Path(src).is_dir():
        return jsonify(error="Source folder not found."), 400

    out_path = Path(out) if out else Path(src) / "organized_papers"

    token = str(uuid.uuid4())
    session["plan_token"] = token
    q: queue.Queue = queue.Queue()
    _PROGRESS[token] = q

    def _bg() -> None:
        try:
            pdfs = collect_pdfs([Path(src)], recursive=recursive)
            if not pdfs:
                q.put({"event": "done", "data": {"count": 0, "papers": []}})
                return

            results: list[Paper] = []

            def _prog(i, total, name):
                q.put({"event": "progress",
                       "data": {"i": i, "total": total, "name": name}})

            results = plan_papers(
                pdfs, out_path,
                prefix=prefix, digits=digits, start=start, template=template,
                categories=DEFAULT_CATEGORIES,
                sort_into_folders=sort_dirs,
                on_progress=_prog,
            )
            _save_plan(token, results)
            q.put({"event": "done", "data": {
                "count": len(results),
                "papers": [_paper_to_dict(p) for p in results],
            }})
        except Exception as exc:
            q.put({"event": "error", "data": {"message": str(exc)}})
        finally:
            _PROGRESS.pop(token, None)

    threading.Thread(target=_bg, daemon=True).start()
    return jsonify(token=token)


@bp.route("/progress/<token>")
def progress(token: str):
    q = _PROGRESS.get(token)
    if q is None:
        return Response("data: {}\n\n", mimetype="text/event-stream")

    @stream_with_context
    def _gen():
        while True:
            try:
                msg = q.get(timeout=30)
            except queue.Empty:
                yield "data: {\"event\":\"heartbeat\"}\n\n"
                continue
            payload = json.dumps(msg, default=str)
            yield f"data: {payload}\n\n"
            if msg.get("event") in ("done", "error"):
                break

    return Response(_gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@bp.route("/apply", methods=["POST"])
def apply():
    token = session.get("plan_token", "")
    papers = _load_plan(token)
    if papers is None:
        return jsonify(error="No plan found — run Scan first."), 400

    copy = request.get_json(force=True).get("copy", True)

    planned = [p for p in papers if p.state == State.PLANNED]
    apply_plan(planned, copy=copy)
    _save_plan(token, papers)

    done   = sum(1 for p in papers if p.state == State.DONE)
    failed = sum(1 for p in papers if p.state == State.FAILED)
    return jsonify(
        done=done,
        failed=failed,
        papers=[_paper_to_dict(p) for p in papers],
    )


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(secret_key: str | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = secret_key or os.urandom(24)
    app.register_blueprint(bp)
    return app
