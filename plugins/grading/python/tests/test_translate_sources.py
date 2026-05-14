from pathlib import Path

import fitz  # pymupdf — dev dependency, used to build a real PDF fixture
import yaml

from plugins.grading.python import translate_sources as ts
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


def _make_pdf(path: Path, pages: int = 2) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i}")
    doc.save(str(path))
    doc.close()


def test_translate_pdf_happy_path(tmp_path, monkeypatch):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, pages=2)
    dest = tmp_path / "sources" / "doc"
    dest.mkdir(parents=True)

    def fake_invoke(input_pdf, output_dir, marker_cfg):
        d = Path(output_dir) / "doc"
        d.mkdir(parents=True)
        (d / "doc.md").write_text("# Doc\n![](pic.png)\n")
        (d / "pic.png").write_bytes(b"\x89PNG fake")

    monkeypatch.setattr(ts, "_invoke_marker_single", fake_invoke)

    page_count, figure_count, extraction = ts._translate_pdf(
        pdf, dest, {"ocr": False, "extract_images": True})

    assert page_count == 2
    assert figure_count == 1
    assert extraction["role"] == "marker_single"
    assert extraction["tier"].startswith("marker-pdf==")
    assert (dest / "content.md").read_text().startswith("# Doc")


def test_translate_pdf_errors_on_empty_content(tmp_path, monkeypatch):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, pages=1)
    dest = tmp_path / "sources" / "doc"
    dest.mkdir(parents=True)

    def fake_invoke(input_pdf, output_dir, marker_cfg):
        d = Path(output_dir) / "doc"
        d.mkdir(parents=True)
        (d / "doc.md").write_text("   \n")   # whitespace only

    monkeypatch.setattr(ts, "_invoke_marker_single", fake_invoke)

    import pytest
    with pytest.raises(RuntimeError, match="no usable content"):
        ts._translate_pdf(pdf, dest, {"ocr": False, "extract_images": True})


def test_invoke_marker_single_raises_on_nonzero(tmp_path, monkeypatch):
    def fake_run(argv, **kwargs):
        class R:
            returncode = 2
            stderr = "boom"
        return R()
    monkeypatch.setattr(ts.subprocess, "run", fake_run)
    import pytest
    with pytest.raises(RuntimeError, match="marker_single failed"):
        ts._invoke_marker_single(tmp_path / "x.pdf", tmp_path / "out",
                                 {"ocr": False, "extract_images": True})


def test_translate_markdown_passthrough_and_image_copy(tmp_path):
    src = tmp_path / "notes.md"
    src.write_text("# Notes\n![](diagram.png)\n![ext](http://x/y.png)\n")
    (tmp_path / "diagram.png").write_bytes(b"\x89PNG fake")
    dest = tmp_path / "sources" / "notes"
    dest.mkdir(parents=True)

    page_count, figure_count, extraction = ts._translate_markdown(src, dest)

    assert page_count == 0
    assert figure_count == 1
    assert extraction is None
    assert (dest / "figures" / "diagram.png").is_file()
    content = (dest / "content.md").read_text()
    assert "![](figures/diagram.png)" in content
    assert "![ext](http://x/y.png)" in content   # external URL untouched


def test_translate_markdown_no_images(tmp_path):
    src = tmp_path / "plain.md"
    src.write_text("# Plain\njust text\n")
    dest = tmp_path / "sources" / "plain"
    dest.mkdir(parents=True)

    page_count, figure_count, extraction = ts._translate_markdown(src, dest)

    assert (page_count, figure_count, extraction) == (0, 0, None)
    assert (dest / "content.md").read_text() == "# Plain\njust text\n"
