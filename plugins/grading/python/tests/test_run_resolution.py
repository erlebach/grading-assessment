from pathlib import Path

import pytest

from plugins.grading.python.run_resolution import (
    AmbiguousRunPrefix,
    NoRunMatch,
    resolve_run,
    most_recent_run,
)


@pytest.fixture
def runs_dir(tmp_path):
    base = tmp_path / "runs"
    for name in [
        "2026-05-13_13-15-00Z__abc1",
        "2026-05-13_14-22-00Z__def6",
        "2026-05-14_09-22-31Z__beef",
    ]:
        (base / name).mkdir(parents=True)
    return base


def test_exact_match(runs_dir):
    r = resolve_run("2026-05-13_13-15-00Z__abc1", runs_dir)
    assert r.name == "2026-05-13_13-15-00Z__abc1"


def test_partial_match_unique(runs_dir):
    r = resolve_run("2026-05-13_13-15-00Z", runs_dir)
    assert r.name == "2026-05-13_13-15-00Z__abc1"


def test_partial_match_ambiguous(runs_dir):
    with pytest.raises(AmbiguousRunPrefix) as exc:
        resolve_run("2026-05-13", runs_dir)
    assert "abc1" in str(exc.value)
    assert "def6" in str(exc.value)


def test_no_match(runs_dir):
    with pytest.raises(NoRunMatch):
        resolve_run("1999-01-01", runs_dir)


def test_most_recent_run(runs_dir):
    r = most_recent_run(runs_dir)
    assert r.name == "2026-05-14_09-22-31Z__beef"


def test_most_recent_run_empty(tmp_path):
    (tmp_path / "runs").mkdir()
    with pytest.raises(NoRunMatch):
        most_recent_run(tmp_path / "runs")
