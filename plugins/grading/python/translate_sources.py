"""CLI + library entrypoint: translate one PDF or markdown source into the
active run folder (Stage 0).

Usage:

    python -m plugins.grading.python.translate_sources <source_path> \
        [--name <n>] [--run <prefix>] [--force]

PDF translation shells out to the `marker_single` CLI (marker-pdf package);
markdown is a verbatim passthrough. Fully deterministic — no subagent, no LLM.
See spec docs/superpowers/specs/2026-05-14-stage0-translate-sources-design.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import ValidationError
from pypdf import PdfReader

from plugins.grading.python.run_resolution import (
    NoRunMatch,
    most_recent_run,
    resolve_run,
)
from plugins.grading.python.schema import SourceMeta, TimelineEvent

_IMG_LINK_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_DEFAULT_MARKER_CONFIG = {"ocr": False, "extract_images": True}


def _resolve_source_name(source_path: Path, name: str | None) -> str:
    if name:
        return name
    stem = source_path.stem.lower()
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_")


def _is_already_translated(dest_dir: Path) -> bool:
    content = dest_dir / "content.md"
    meta = dest_dir / "meta.yaml"
    if not (content.is_file() and meta.is_file()):
        return False
    try:
        SourceMeta.model_validate(yaml.safe_load(meta.read_text(encoding="utf-8")))
        return True
    except (ValidationError, yaml.YAMLError):
        return False


def _rewrite_image_links(markdown: str, prefix: str = "figures") -> str:
    """Repoint local image links at the figures/ subdir; leave URLs/abs paths."""
    def repl(m: re.Match) -> str:
        alt, target = m.group(1), m.group(2)
        if "://" in target or target.startswith("/"):
            return m.group(0)
        return f"![{alt}]({prefix}/{Path(target).name})"
    return _IMG_LINK_RE.sub(repl, markdown)


def _ingest_marker_single_output(marker_out_dir: Path, dest_dir: Path) -> int:
    """Relocate marker_single's <stem>.md -> dest_dir/content.md and its sibling
    images -> dest_dir/figures/, rewriting image links. Returns figure count."""
    md_files = sorted(marker_out_dir.rglob("*.md"))
    if len(md_files) != 1:
        raise RuntimeError(
            f"expected exactly one .md in marker_single output, "
            f"found {len(md_files)} under {marker_out_dir}"
        )
    src_md = md_files[0]
    figures_dir = dest_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    figure_count = 0
    for item in sorted(src_md.parent.iterdir()):
        if item.is_file() and item.suffix.lower() in _IMAGE_SUFFIXES:
            shutil.copy2(item, figures_dir / item.name)
            figure_count += 1

    (dest_dir / "content.md").write_text(_rewrite_image_links(src_md.read_text(encoding="utf-8")), encoding="utf-8")
    return figure_count


def _marker_pdf_version() -> str:
    """Version of the external `marker-pdf` that provides the `marker_single` CLI.

    `marker-pdf` is not a dependency of this project's venv (it is an external
    `uv tool` install), so `importlib.metadata` in *this* interpreter cannot see
    it. Resolve the `marker_single` entry-point script on PATH, read its shebang
    to find the interpreter of the environment it lives in, and query that.
    Returns "unknown" if resolution fails at any step.
    """
    marker_bin = shutil.which("marker_single")
    if marker_bin is None:
        return "unknown"
    try:
        first_line = Path(marker_bin).read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError, UnicodeDecodeError):
        return "unknown"
    if not first_line.startswith("#!"):
        return "unknown"
    interpreter = first_line[2:].split()
    if not interpreter:
        return "unknown"
    try:
        result = subprocess.run(
            [*interpreter, "-c",
             "import importlib.metadata as m; print(m.version('marker-pdf'))"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _pdf_page_count(pdf_path: Path) -> int:
    return len(PdfReader(str(pdf_path)).pages)


def _invoke_marker_single(input_pdf: Path, output_dir: Path,
                          marker_cfg: dict) -> None:
    """Run the marker_single CLI. Raises RuntimeError on non-zero exit."""
    argv = ["marker_single", "--output_dir", str(output_dir),
            "--output_format", "markdown"]
    if not marker_cfg.get("ocr", False):
        argv.append("--disable_ocr")
    if not marker_cfg.get("extract_images", True):
        argv.append("--disable_image_extraction")
    argv.append(str(input_pdf))
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"marker_single failed (exit {result.returncode}): {result.stderr}"
        )


def _translate_pdf(source_path: Path, dest_dir: Path,
                   marker_cfg: dict) -> tuple[int, int, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        _invoke_marker_single(source_path, out_dir, marker_cfg)
        figure_count = _ingest_marker_single_output(out_dir, dest_dir)

    content_md = dest_dir / "content.md"
    if not content_md.is_file() or not content_md.read_text(encoding="utf-8").strip():
        raise RuntimeError(
            f"marker_single produced no usable content.md for {source_path}"
        )

    extraction = {
        "role": "marker_single",
        "tier": f"marker-pdf=={_marker_pdf_version()}",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    return _pdf_page_count(source_path), figure_count, extraction


def _translate_markdown(source_path: Path,
                        dest_dir: Path) -> tuple[int, int, None]:
    raw = source_path.read_text(encoding="utf-8")
    figures_dir = dest_dir / "figures"
    figure_count = 0
    for m in _IMG_LINK_RE.finditer(raw):
        target = m.group(2)
        if "://" in target or target.startswith("/"):
            continue
        img_src = source_path.parent / target
        if img_src.is_file():
            figures_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img_src, figures_dir / img_src.name)
            figure_count += 1
    (dest_dir / "content.md").write_text(_rewrite_image_links(raw), encoding="utf-8")
    return 0, figure_count, None


def _finalize(dest_dir: Path, fmt: str, page_count: int,
              figure_count: int, extraction: dict | None) -> Path:
    content_bytes = (dest_dir / "content.md").read_bytes()
    meta = {
        "format": fmt,
        "courses": [],
        "topics": [],
        "extraction": extraction,
        "content_sha": hashlib.sha256(content_bytes).hexdigest(),
        "figure_count": figure_count,
        "page_count": page_count,
    }
    SourceMeta.model_validate(meta)              # invariant: must be schema-valid
    (dest_dir / "meta.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    return dest_dir


def _load_marker_config(run_dir: Path) -> dict:
    cfg_path = run_dir / "config.yaml"
    if cfg_path.is_file():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return cfg.get("marker_single") or _DEFAULT_MARKER_CONFIG
    return _DEFAULT_MARKER_CONFIG


def _append_timeline(run_dir: Path, source_name: str, *, skipped: bool) -> None:
    traces_dir = run_dir / "traces" / "translate_sources"
    traces_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "python_helper_call",
        "actor": "translate_sources",
        "name": source_name,
        "phase": "end",
        "details": {"skipped": skipped},
    }
    TimelineEvent.model_validate(event)          # invariant: schema-valid
    with (traces_dir / "timeline.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def translate_source(source_path: Path, run_dir: Path, *,
                     name: str | None = None, force: bool = False) -> Path:
    """Translate one PDF or markdown source into run_dir/sources/<name>/."""
    source_path = Path(source_path)
    run_dir = Path(run_dir)
    if not source_path.is_file():
        raise FileNotFoundError(f"source not found: {source_path}")

    source_name = _resolve_source_name(source_path, name)
    dest_dir = run_dir / "sources" / source_name

    if not force and _is_already_translated(dest_dir):
        print(f"already translated: {source_name}")
        _append_timeline(run_dir, source_name, skipped=True)
        return dest_dir

    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        marker_cfg = _load_marker_config(run_dir)
        page_count, figure_count, extraction = _translate_pdf(
            source_path, dest_dir, marker_cfg)
        fmt = "pdf"
    elif suffix == ".md":
        page_count, figure_count, extraction = _translate_markdown(
            source_path, dest_dir)
        fmt = "markdown"
    else:
        raise ValueError(f"unsupported source type: {suffix!r} (expected .pdf or .md)")

    _finalize(dest_dir, fmt, page_count, figure_count, extraction)
    _append_timeline(run_dir, source_name, skipped=False)
    return dest_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="translate_sources")
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--name", default=None,
                        help="override the auto-derived source name")
    parser.add_argument("--run", default=None,
                        help="run-folder prefix; defaults to most recent")
    parser.add_argument("--runs-root", type=Path, default=None,
                        help="override preprocessing/runs/ location (for tests)")
    parser.add_argument("--force", action="store_true",
                        help="re-translate even if already present")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[3]
    runs_dir = args.runs_root or (repo_root / "preprocessing" / "runs")
    try:
        run_dir = (resolve_run(args.run, runs_dir) if args.run
                   else most_recent_run(runs_dir))
    except NoRunMatch:
        print("error: no run folder found — run /grade:init first.",
              file=sys.stderr)
        return 1

    dest = translate_source(args.source_path, run_dir,
                            name=args.name, force=args.force)
    print(f"translated -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
