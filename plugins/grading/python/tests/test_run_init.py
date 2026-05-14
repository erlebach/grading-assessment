import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from plugins.grading.python.run_init import (
    _deep_merge,
    _run_fingerprint,
    _generate_run_id,
    init_run,
)
from plugins.grading.python.schema import RunMeta


def test_deep_merge_overrides_nested_keys():
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    overrides = {"a": {"y": 99}}
    merged = _deep_merge(base, overrides)
    assert merged == {"a": {"x": 1, "y": 99}, "b": 3}
    # base is not mutated
    assert base == {"a": {"x": 1, "y": 2}, "b": 3}


def test_run_fingerprint_is_deterministic():
    cfg = {"a": 1, "b": {"c": 2}}
    fp1 = _run_fingerprint(cfg, "deadbeef")
    fp2 = _run_fingerprint(cfg, "deadbeef")
    assert fp1 == fp2
    assert len(fp1) == 4


def test_run_fingerprint_changes_with_input():
    cfg = {"a": 1}
    assert _run_fingerprint(cfg, "sha1") != _run_fingerprint(cfg, "sha2")
    assert _run_fingerprint({"a": 1}, "s") != _run_fingerprint({"a": 2}, "s")


def test_generate_run_id_format():
    now = datetime(2026, 5, 14, 9, 22, 31, tzinfo=timezone.utc)
    run_id = _generate_run_id(now, "abcd")
    assert run_id == "2026-05-14_09-22-31Z__abcd"
    assert re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}Z__[0-9a-f]{4}$", run_id)


# ---------------------------------------------------------------------------
# Task 5: init_run() integration tests
# ---------------------------------------------------------------------------

def _fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "plugins" / "grading" / "python").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
    (repo / "plugins" / "grading" / "python" / "schema.py").write_text("x = 1\n")
    return repo


_PIPELINE_CONFIG = {
    "seeds_per_type": {"default": 8},
    "generate_rubric": {"good_count": 3, "less_good_count": 3, "wrong_count": 3},
    "marker_single": {"ocr": False, "extract_images": True},
    "profiles": {"smoke": {"seeds_per_type": {"default": 1},
                           "generate_rubric": {"good_count": 1}}},
}


def test_init_run_creates_skeleton(tmp_path):
    runs_dir = tmp_path / "runs"
    repo = _fake_repo(tmp_path)
    run_dir = init_run(runs_dir, repo, _PIPELINE_CONFIG)
    for sub in ("sources", "seed_questions", "types", "rubrics",
                "synthetic_answers", "grades", "traces"):
        assert (run_dir / sub).is_dir(), sub
    assert (run_dir / "src_snapshot.tar.gz").is_file()
    assert (run_dir / "config.yaml").is_file()
    assert (run_dir / "run_meta.yaml").is_file()


def test_init_run_config_excludes_profiles_key(tmp_path):
    run_dir = init_run(tmp_path / "runs", _fake_repo(tmp_path), _PIPELINE_CONFIG)
    cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    assert "profiles" not in cfg
    assert cfg["seeds_per_type"]["default"] == 8     # base value, no profile
    assert cfg["marker_single"]["extract_images"] is True


def test_init_run_applies_profile(tmp_path):
    run_dir = init_run(tmp_path / "runs", _fake_repo(tmp_path),
                       _PIPELINE_CONFIG, profile="smoke")
    cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    assert cfg["seeds_per_type"]["default"] == 1      # overridden by smoke
    assert cfg["generate_rubric"]["good_count"] == 1
    assert cfg["generate_rubric"]["less_good_count"] == 3   # untouched by smoke
    meta = yaml.safe_load((run_dir / "run_meta.yaml").read_text())
    assert meta["profile"] == "smoke"


def test_init_run_meta_validates(tmp_path):
    run_dir = init_run(tmp_path / "runs", _fake_repo(tmp_path), _PIPELINE_CONFIG)
    meta = yaml.safe_load((run_dir / "run_meta.yaml").read_text())
    RunMeta.model_validate(meta)          # raises if invalid
    assert meta["profile"] is None
    assert meta["stages_run"] == []


def test_init_run_unknown_profile_raises(tmp_path):
    with pytest.raises(KeyError):
        init_run(tmp_path / "runs", _fake_repo(tmp_path),
                 _PIPELINE_CONFIG, profile="does-not-exist")
