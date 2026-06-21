"""
Tests for paper_organizer/web.py (Flask routes).

Run from claude_code_scientific_literature_manager/:
    ..\.venv\Scripts\python.exe -m pytest tests/ -v
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_organizer.web import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(secret_key="test-secret-key")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestIndex:
    def test_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_contains_category_names(self, client):
        r = client.get("/")
        body = r.data.decode()
        assert "Micelles" in body
        assert "Chiral"   in body
        assert "General"  in body

    def test_html_content_type(self, client):
        r = client.get("/")
        assert "text/html" in r.content_type


# ── POST /scan ────────────────────────────────────────────────────────────────

class TestScan:
    def test_missing_source_returns_400(self, client):
        r = client.post("/scan",
                        data=json.dumps({"source": ""}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_nonexistent_folder_returns_400(self, client):
        r = client.post("/scan",
                        data=json.dumps({"source": "C:\\definitely\\does\\not\\exist"}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_valid_folder_returns_token(self, client, tmp_path):
        # We don't wait for the background thread; just check the token comes back.
        r = client.post("/scan",
                        data=json.dumps({"source": str(tmp_path)}),
                        content_type="application/json")
        assert r.status_code == 200
        body = r.get_json()
        assert "token" in body
        assert len(body["token"]) > 10     # UUID-like


# ── POST /apply ───────────────────────────────────────────────────────────────

class TestApply:
    def test_no_plan_returns_400(self, client):
        r = client.post("/apply",
                        data=json.dumps({"copy": True}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_apply_after_scan(self, client, tmp_path):
        from paper_organizer.core import Paper, State
        from paper_organizer.web import _save_plan

        src = tmp_path / "paper.pdf"
        src.write_bytes(b"%PDF fake content")
        dst = tmp_path / "out" / "CB001.pdf"

        paper = Paper(source=src, destination=dst, state=State.PLANNED, new_name="CB001.pdf")

        # Write a plan manually and inject the token into the session
        import uuid
        token = str(uuid.uuid4())
        _save_plan(token, [paper])

        with client.session_transaction() as sess:
            sess["plan_token"] = token

        r = client.post("/apply",
                        data=json.dumps({"copy": True}),
                        content_type="application/json")
        assert r.status_code == 200
        body = r.get_json()
        assert "done" in body
        assert "failed" in body
        assert body["done"] == 1
        assert body["failed"] == 0
        assert dst.exists()


# ── GET /progress/<token> ─────────────────────────────────────────────────────

class TestProgress:
    def test_unknown_token_returns_200(self, client):
        # Unknown token → empty stream, still a valid SSE response
        r = client.get("/progress/nonexistent-token")
        assert r.status_code == 200
        assert "text/event-stream" in r.content_type
