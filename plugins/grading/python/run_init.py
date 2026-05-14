"""CLI + library entrypoint: create and bootstrap a preprocessing run folder.

Usage:

    python -m plugins.grading.python.run_init [--profile <name>]

Writes a self-contained run folder under preprocessing/runs/ with the stage
subdirectory skeleton, a frozen merged config.yaml, src_snapshot.tar.gz, and
run_meta.yaml. See spec docs/superpowers/specs/2026-05-14-stage0-translate-sources-design.md.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from plugins.grading.python.schema import RunMeta
from plugins.grading.python.snapshot import create_snapshot


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Return a new dict: base recursively updated with overrides."""
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _run_fingerprint(merged_config: dict, git_sha: str) -> str:
    """4-char content fingerprint of the merged config + git sha (spec §2)."""
    payload = yaml.safe_dump(merged_config, sort_keys=True) + (git_sha or "")
    return hashlib.sha256(payload.encode()).hexdigest()[:4]


def _generate_run_id(now: datetime, fingerprint: str) -> str:
    """Run id = YYYY-MM-DD_HH-MM-SSZ__<fingerprint> (spec §2)."""
    return now.strftime("%Y-%m-%d_%H-%M-%SZ") + f"__{fingerprint}"
