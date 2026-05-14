from pathlib import Path

import yaml

from plugins.grading.python.translate_sources import (
    _resolve_source_name,
    _is_already_translated,
)


def test_resolve_source_name_snake_cases_stem():
    assert _resolve_source_name(Path("Juzek Description v1-0-7.pdf"), None) \
        == "juzek_description_v1_0_7"


def test_resolve_source_name_respects_override():
    assert _resolve_source_name(Path("whatever.pdf"), "my_name") == "my_name"


def test_is_already_translated_false_when_missing(tmp_path):
    assert _is_already_translated(tmp_path / "nonexistent") is False


def test_is_already_translated_false_when_meta_invalid(tmp_path):
    dest = tmp_path / "src"
    dest.mkdir()
    (dest / "content.md").write_text("hi")
    (dest / "meta.yaml").write_text("not: a valid SourceMeta\n")
    assert _is_already_translated(dest) is False


def test_is_already_translated_true_when_valid(tmp_path):
    dest = tmp_path / "src"
    dest.mkdir()
    (dest / "content.md").write_text("hi")
    (dest / "meta.yaml").write_text(yaml.safe_dump({
        "format": "markdown", "courses": [], "topics": [],
        "extraction": None, "content_sha": "abcd1234",
        "figure_count": 0, "page_count": 0,
    }))
    assert _is_already_translated(dest) is True
