import json
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"


def test_manifest_file_exists():
    assert MANIFEST.is_file(), f"missing manifest at {MANIFEST}"


def test_manifest_is_valid_json():
    json.loads(MANIFEST.read_text())


def test_manifest_required_fields():
    data = json.loads(MANIFEST.read_text())
    assert data["name"] == "grading"
    assert isinstance(data["description"], str) and data["description"]
    version = data["version"]
    parts = version.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), version


def test_manifest_author_present():
    data = json.loads(MANIFEST.read_text())
    assert "author" in data
