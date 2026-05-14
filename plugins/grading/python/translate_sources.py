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
