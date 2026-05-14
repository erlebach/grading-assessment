import re
from datetime import datetime, timezone

from plugins.grading.python.run_init import (
    _deep_merge,
    _run_fingerprint,
    _generate_run_id,
)


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
