"""Tests for slm.config."""
import json
import tempfile
from pathlib import Path

import pytest
from slm.config import Config, NamingConfig


def test_defaults():
    cfg = Config()
    assert cfg.naming.prefix == "CB"
    assert cfg.naming.digits == 3
    assert "Micelles" in cfg.categories


def test_effective_prefix_per_category():
    cfg = Config()
    cfg.naming.per_category = True
    assert cfg.effective_prefix("Micelles") == "M"
    assert cfg.effective_prefix("Unknown") == cfg.naming.prefix


def test_effective_prefix_global():
    cfg = Config()
    cfg.naming.per_category = False
    assert cfg.effective_prefix("Micelles") == cfg.naming.prefix


def test_from_file_override():
    data = {"naming": {"prefix": "XY", "digits": 4}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        p = Path(f.name)
    try:
        cfg = Config.from_file(p)
        assert cfg.naming.prefix == "XY"
        assert cfg.naming.digits == 4
        assert cfg.naming.title_words == 8
    finally:
        p.unlink()


def test_from_file_missing():
    import tempfile
    d = Path(tempfile.mkdtemp())
    with pytest.raises(FileNotFoundError):
        Config.from_file(d / "nonexistent.json")
