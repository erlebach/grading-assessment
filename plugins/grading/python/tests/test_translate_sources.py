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


from plugins.grading.python.translate_sources import (
    _rewrite_image_links,
    _ingest_marker_single_output,
)


def test_rewrite_image_links_prefixes_local_images():
    md = "text\n![cap](fig_1.png)\nmore ![](sub/fig_2.jpeg)\n"
    out = _rewrite_image_links(md)
    assert "![cap](figures/fig_1.png)" in out
    assert "![](figures/fig_2.jpeg)" in out


def test_rewrite_image_links_leaves_external_urls():
    md = "![x](https://example.com/a.png) ![y](/abs/b.png)"
    out = _rewrite_image_links(md)
    assert out == md


def test_ingest_marker_single_output_relocates_and_rewrites(tmp_path):
    # Fake a marker_single output dir: conversion/<stem>/<stem>.md + an image.
    marker_out = tmp_path / "marker_out" / "doc"
    marker_out.mkdir(parents=True)
    (marker_out / "doc.md").write_text("# Title\n![](pic.png)\n")
    (marker_out / "pic.png").write_bytes(b"\x89PNG fake")
    dest = tmp_path / "sources" / "doc"
    dest.mkdir(parents=True)

    figure_count = _ingest_marker_single_output(tmp_path / "marker_out", dest)

    assert figure_count == 1
    assert (dest / "figures" / "pic.png").is_file()
    content = (dest / "content.md").read_text()
    assert "![](figures/pic.png)" in content


def test_ingest_marker_single_output_errors_on_zero_md(tmp_path):
    empty = tmp_path / "marker_out"
    empty.mkdir()
    import pytest
    with pytest.raises(RuntimeError, match="exactly one .md"):
        _ingest_marker_single_output(empty, tmp_path / "dest")
