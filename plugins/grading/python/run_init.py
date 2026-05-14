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


_RUN_SUBDIRS = (
    "sources", "seed_questions", "types", "rubrics",
    "synthetic_answers", "grades", "traces",
)


def _git_sha(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root,
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_dirty(repo_root: Path) -> bool:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root,
            capture_output=True, text=True, check=True,
        )
        return bool(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def init_run(
    runs_dir: Path,
    repo_root: Path,
    pipeline_config: dict,
    profile: str | None = None,
    now: datetime | None = None,
) -> Path:
    """Create and bootstrap a self-contained run folder. Returns its path."""
    now = now or datetime.now(timezone.utc)
    runs_dir = Path(runs_dir)
    repo_root = Path(repo_root)

    config = {k: v for k, v in pipeline_config.items() if k != "profiles"}
    if profile is not None:
        profiles = pipeline_config.get("profiles", {})
        if profile not in profiles:
            raise KeyError(f"unknown profile {profile!r}; "
                           f"known: {sorted(profiles)}")
        config = _deep_merge(config, profiles[profile])

    git_sha = _git_sha(repo_root)
    git_dirty = _git_dirty(repo_root)
    fingerprint = _run_fingerprint(config, git_sha or "")
    run_id = _generate_run_id(now, fingerprint)
    run_dir = runs_dir / run_id

    for sub in _RUN_SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    (run_dir / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    create_snapshot(repo_root, run_dir / "src_snapshot.tar.gz")

    run_meta = {
        "run_id": run_id,
        "started_at": now.isoformat(),
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "status": "success",
        "stages_run": [],
        "profile": profile,
    }
    RunMeta.model_validate(run_meta)          # invariant: must be schema-valid
    (run_dir / "run_meta.yaml").write_text(yaml.safe_dump(run_meta, sort_keys=False))
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_init")
    parser.add_argument("--profile", default=None,
                        help="named profile from pipeline.yaml's profiles: block")
    parser.add_argument("--runs-dir", type=Path, default=None,
                        help="override preprocessing/runs/ location (for tests)")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[3]
    runs_dir = args.runs_dir or (repo_root / "preprocessing" / "runs")
    pipeline_path = repo_root / "plugins" / "grading" / "config" / "pipeline.yaml"
    pipeline_config = yaml.safe_load(pipeline_path.read_text())

    run_dir = init_run(runs_dir, repo_root, pipeline_config, profile=args.profile)
    print(f"initialized run → {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
