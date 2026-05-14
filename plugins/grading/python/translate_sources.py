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
from importlib.metadata import PackageNotFoundError, version
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
        SourceMeta.model_validate(yaml.safe_load(meta.read_text()))
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

    (dest_dir / "content.md").write_text(_rewrite_image_links(src_md.read_text()))
    return figure_count


def _marker_pdf_version() -> str:
    try:
        return version("marker-pdf")
    except PackageNotFoundError:
        return "unknown"


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
    if not content_md.is_file() or not content_md.read_text().strip():
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
    raw = source_path.read_text()
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
    (dest_dir / "content.md").write_text(_rewrite_image_links(raw))
    return 0, figure_count, None
