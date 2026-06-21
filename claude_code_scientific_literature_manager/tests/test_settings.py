"""Tests for loading configuration settings.

This test checks that a custom JSON config can change selected settings while
keeping the default settings that were not replaced.
"""

import json

from literature_manager.settings import load_config


def test_load_config_deep_merges_user_values(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "identifier_prefix": "OL",
                "categories": {
                    "Astrobiology": ["europa"],
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["identifier_prefix"] == "OL"
    assert config["categories"]["Astrobiology"] == ["europa"]
    assert "Micelles" in config["categories"]
