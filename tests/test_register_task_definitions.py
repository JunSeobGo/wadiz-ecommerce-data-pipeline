"""register_task_definitions.apply_image_override 테스트 (boto3 없이 순수 로직)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from register_task_definitions import apply_image_override  # noqa: E402


def test_override_replaces_all_container_images():
    payload = {
        "family": "wd-silver-etl",
        "containerDefinitions": [
            {"name": "c1", "image": "old:1"},
            {"name": "c2", "image": "old:2"},
        ],
    }
    result = apply_image_override(payload, "new-registry/repo:silver-abc123")
    assert all(c["image"] == "new-registry/repo:silver-abc123" for c in result["containerDefinitions"])


def test_no_image_keeps_original():
    payload = {"containerDefinitions": [{"name": "c1", "image": "old:1"}]}
    result = apply_image_override(payload, None)
    assert result["containerDefinitions"][0]["image"] == "old:1"


def test_missing_container_definitions_is_safe():
    assert apply_image_override({"family": "x"}, "img:1") == {"family": "x"}
