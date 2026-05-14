import json as _json
from pathlib import Path

import fitz  # pymupdf — dev dependency, used to build a real PDF fixture
import yaml

from plugins.grading.python import translate_sources as ts
from plugins.grading.python.translate_sources import (
    _resolve_source_name,
    _is_already_translated,
)
from plugins.grading.python.schema import SourceMeta, TimelineEvent


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


def test_marker_pdf_version_unknown_when_not_on_path(monkeypatch):
    monkeypatch.setattr(ts.shutil, "which", lambda name: None)
    assert ts._marker_pdf_version() == "unknown"


def test_marker_pdf_version_reads_shebang_and_queries_interpreter(tmp_path, monkeypatch):
    fake_bin = tmp_path / "marker_single"
    fake_bin.write_text("#!/fake/python\n# entry point\n", encoding="utf-8")
    monkeypatch.setattr(ts.shutil, "which", lambda name: str(fake_bin))

    def fake_run(argv, **kwargs):
        assert argv[0] == "/fake/python"
        assert "marker-pdf" in argv[-1]

        class R:
            returncode = 0
            stdout = "1.10.2\n"
        return R()

    monkeypatch.setattr(ts.subprocess, "run", fake_run)
    assert ts._marker_pdf_version() == "1.10.2"


def test_marker_pdf_version_unknown_when_interpreter_query_fails(tmp_path, monkeypatch):
    fake_bin = tmp_path / "marker_single"
    fake_bin.write_text("#!/fake/python\n", encoding="utf-8")
    monkeypatch.setattr(ts.shutil, "which", lambda name: str(fake_bin))

    def fake_run(argv, **kwargs):
        class R:
            returncode = 1
            stdout = ""
        return R()

    monkeypatch.setattr(ts.subprocess, "run", fake_run)
    assert ts._marker_pdf_version() == "unknown"


def test_marker_pdf_version_resolves_external_install():
    """Integration: when marker_single is actually installed, resolve its real version."""
    import re

    import pytest
    if ts.shutil.which("marker_single") is None:
        pytest.skip("marker_single not installed in this environment")
    resolved = ts._marker_pdf_version()
    assert resolved != "unknown"
    assert re.match(r"\d+\.\d+", resolved), f"expected a version, got {resolved!r}"


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


def test_finalize_writes_valid_meta(tmp_path):
    dest = tmp_path / "sources" / "doc"
    dest.mkdir(parents=True)
    (dest / "content.md").write_text("# hello world\n")

    ts._finalize(dest, "pdf", page_count=3, figure_count=2,
                 extraction={"role": "marker_single",
                             "tier": "marker-pdf==1.0", "ts": "2026-05-14T00:00:00Z"})

    meta = yaml.safe_load((dest / "meta.yaml").read_text())
    SourceMeta.model_validate(meta)               # raises if invalid
    assert meta["format"] == "pdf"
    assert meta["page_count"] == 3
    assert meta["figure_count"] == 2
    assert meta["courses"] == [] and meta["topics"] == []
    assert len(meta["content_sha"]) >= 8


def test_finalize_markdown_extraction_none(tmp_path):
    dest = tmp_path / "sources" / "n"
    dest.mkdir(parents=True)
    (dest / "content.md").write_text("text\n")

    ts._finalize(dest, "markdown", page_count=0, figure_count=0,
                 extraction=None)

    meta = yaml.safe_load((dest / "meta.yaml").read_text())
    SourceMeta.model_validate(meta)
    assert meta["extraction"] is None


def test_finalize_content_sha_tracks_content(tmp_path):
    dest = tmp_path / "sources" / "d"
    dest.mkdir(parents=True)
    (dest / "content.md").write_text("AAA")
    ts._finalize(dest, "markdown", 0, 0, None)
    sha_a = yaml.safe_load((dest / "meta.yaml").read_text())["content_sha"]
    (dest / "content.md").write_text("BBB")
    ts._finalize(dest, "markdown", 0, 0, None)
    sha_b = yaml.safe_load((dest / "meta.yaml").read_text())["content_sha"]
    assert sha_a != sha_b


# ---------------------------------------------------------------------------
# Task 12: translate_source(), _append_timeline(), main()
# ---------------------------------------------------------------------------

def _run_dir_with_config(tmp_path) -> Path:
    run_dir = tmp_path / "runs" / "2026-05-14_00-00-00Z__abcd"
    for sub in ("sources", "traces"):
        (run_dir / sub).mkdir(parents=True)
    (run_dir / "config.yaml").write_text(yaml.safe_dump(
        {"marker_single": {"ocr": False, "extract_images": True}}))
    return run_dir


def test_translate_source_markdown_end_to_end(tmp_path):
    run_dir = _run_dir_with_config(tmp_path)
    src = tmp_path / "My Notes.md"
    src.write_text("# Notes\ntext\n")

    dest = ts.translate_source(src, run_dir)

    assert dest == run_dir / "sources" / "my_notes"
    assert (dest / "content.md").is_file()
    SourceMeta.model_validate(yaml.safe_load((dest / "meta.yaml").read_text()))
    lines = (run_dir / "traces" / "translate_sources" / "timeline.jsonl") \
        .read_text().splitlines()
    assert len(lines) == 1
    TimelineEvent.model_validate(_json.loads(lines[0]))
    assert _json.loads(lines[0])["event_type"] == "python_helper_call"


def test_translate_source_skip_if_present(tmp_path, capsys):
    run_dir = _run_dir_with_config(tmp_path)
    src = tmp_path / "notes.md"
    src.write_text("# Notes\n")
    ts.translate_source(src, run_dir)
    first_sha = yaml.safe_load(
        (run_dir / "sources" / "notes" / "meta.yaml").read_text())["content_sha"]

    src.write_text("# CHANGED\n")            # change source
    ts.translate_source(src, run_dir)        # second call: should skip
    second_sha = yaml.safe_load(
        (run_dir / "sources" / "notes" / "meta.yaml").read_text())["content_sha"]
    assert first_sha == second_sha           # not re-translated
    assert "already translated" in capsys.readouterr().out

    # Verify the skip path appends a skipped=True timeline event
    timeline_path = run_dir / "traces" / "translate_sources" / "timeline.jsonl"
    lines = timeline_path.read_text().splitlines()
    assert len(lines) == 2                   # one per call
    second_event = _json.loads(lines[1])
    assert second_event["details"] == {"skipped": True}
    TimelineEvent.model_validate(second_event)


def test_translate_source_force_retranslates(tmp_path):
    run_dir = _run_dir_with_config(tmp_path)
    src = tmp_path / "notes.md"
    src.write_text("# Notes\n")
    ts.translate_source(src, run_dir)
    src.write_text("# CHANGED\n")
    ts.translate_source(src, run_dir, force=True)
    content = (run_dir / "sources" / "notes" / "content.md").read_text()
    assert content == "# CHANGED\n"


def test_translate_source_missing_file_raises(tmp_path):
    run_dir = _run_dir_with_config(tmp_path)
    import pytest
    with pytest.raises(FileNotFoundError):
        ts.translate_source(tmp_path / "nope.md", run_dir)


def test_main_errors_when_no_run_folder(tmp_path, capsys):
    (tmp_path / "runs").mkdir()
    src = tmp_path / "notes.md"
    src.write_text("# x\n")
    rc = ts.main([str(src), "--runs-root", str(tmp_path / "runs")])
    assert rc == 1
    assert "/grade:init" in capsys.readouterr().err


def test_translate_source_unsupported_type_raises(tmp_path):
    run_dir = _run_dir_with_config(tmp_path)
    src = tmp_path / "notes.txt"
    src.write_text("plain text\n")
    import pytest
    with pytest.raises(ValueError):
        ts.translate_source(src, run_dir)
