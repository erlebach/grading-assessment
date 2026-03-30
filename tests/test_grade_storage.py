"""Tests for T3.4 — grade storage and appeal tracking."""

from __future__ import annotations

import json
import pytest
from datetime import datetime
from pathlib import Path

from grading_pipeline.models import (
    Appeal,
    Check,
    CheckCategory,
    CheckEvaluation,
    CheckEvaluationResult,
    GradeCalculation,
    GradeResult,
)
from grading_dynamic_rubrics.grade_storage import (
    get_grade_history,
    store_grade,
    store_grade_appeal,
    validate_grade_increase,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


def _make_grade(
    student_id: str = "student_001",
    question_id: str = "q01",
    version: int = 1,
    final_score: float = 7.5,
) -> GradeResult:
    check = Check(
        id="c1",
        text="Sample check",
        category=CheckCategory.SEMANTIC,
        weight=1.0,
        question_id=question_id,
    )
    evaluation = CheckEvaluation(
        check_id="c1",
        result=CheckEvaluationResult.PASS,
        score=1.0,
        evidence="good",
    )
    calc = GradeCalculation(
        total_checks=1,
        checks_passed=1,
        checks_failed=0,
        checks_unclear=0,
        weighted_sum=1.0,
        weight_denominator=1.0,
        final_score=final_score,
    )
    grade_id = f"{student_id}_{question_id}_v{version}"
    return GradeResult(
        id=grade_id,
        question_id=question_id,
        student_id=student_id,
        rubric_id=f"{question_id}_rubric_v1",
        rubric_version=1,
        check_evaluations=[evaluation],
        calculation=calc,
        final_score=final_score,
        version=version,
    )


def _make_appeal(
    student_id: str = "student_001",
    question_id: str = "q01",
    original_score: float = 7.5,
    new_score: float = 8.5,
    version: int = 1,
) -> Appeal:
    return Appeal(
        id=f"appeal_{student_id}_{question_id}_v{version}",
        original_grade_id=f"{student_id}_{question_id}_v1",
        student_id=student_id,
        question_id=question_id,
        original_score=original_score,
        new_score=new_score,
        reason="Student argued partial credit",
        requested_at=datetime(2026, 3, 30, 14, 22, 0),
    )


# ---------------------------------------------------------------------------
# validate_grade_increase
# ---------------------------------------------------------------------------

def test_validate_grade_increase_equal():
    """Equal scores are allowed (no decrease)."""
    validate_grade_increase(7.5, 7.5)  # Should not raise


def test_validate_grade_increase_higher():
    """Higher new score is allowed."""
    validate_grade_increase(7.5, 8.0)


def test_validate_grade_increase_lower_raises():
    """Lower new score must raise ValueError."""
    with pytest.raises(ValueError, match="upward"):
        validate_grade_increase(8.0, 7.5)


# ---------------------------------------------------------------------------
# store_grade
# ---------------------------------------------------------------------------

def test_store_grade_creates_file(data_dir):
    grade = _make_grade()
    path = store_grade(grade, data_dir)
    assert path.exists()
    assert path.name == "student_001_q01_grade_v1.json"


def test_store_grade_content_roundtrips(data_dir):
    grade = _make_grade(final_score=6.0)
    path = store_grade(grade, data_dir)
    loaded = GradeResult.model_validate(json.loads(path.read_text()))
    assert loaded.final_score == 6.0
    assert loaded.student_id == "student_001"


def test_store_grade_does_not_overwrite(data_dir):
    grade = _make_grade()
    store_grade(grade, data_dir)
    with pytest.raises(FileExistsError):
        store_grade(grade, data_dir)


def test_store_grade_versions_are_separate_files(data_dir):
    g1 = _make_grade(version=1, final_score=6.0)
    g2 = _make_grade(version=2, final_score=7.0)
    p1 = store_grade(g1, data_dir)
    p2 = store_grade(g2, data_dir)
    assert p1 != p2
    assert p1.exists()
    assert p2.exists()


def test_store_grade_creates_subdirectories(tmp_path):
    """data_dir/grades/final is created automatically."""
    data_dir = tmp_path / "newdir"  # does not exist yet
    grade = _make_grade()
    path = store_grade(grade, data_dir)
    assert path.exists()


# ---------------------------------------------------------------------------
# store_grade_appeal
# ---------------------------------------------------------------------------

def test_store_appeal_creates_file(data_dir):
    appeal = _make_appeal()
    path = store_grade_appeal(appeal, data_dir)
    assert path.exists()
    assert "appeal_student_001_q01_v1" in path.name


def test_store_appeal_timestamp_in_filename(data_dir):
    appeal = _make_appeal()
    path = store_grade_appeal(appeal, data_dir)
    assert "2026-03-30T14:22:00" in path.name


def test_store_appeal_content_roundtrips(data_dir):
    appeal = _make_appeal(new_score=9.0)
    path = store_grade_appeal(appeal, data_dir)
    loaded = Appeal.model_validate(json.loads(path.read_text()))
    assert loaded.new_score == 9.0


def test_store_appeal_does_not_overwrite(data_dir):
    appeal = _make_appeal()
    store_grade_appeal(appeal, data_dir)
    with pytest.raises(FileExistsError):
        store_grade_appeal(appeal, data_dir)


def test_appeal_model_rejects_downward_score():
    """Appeal model itself rejects new_score < original_score."""
    with pytest.raises(ValueError):
        _make_appeal(original_score=8.0, new_score=7.0)


# ---------------------------------------------------------------------------
# get_grade_history
# ---------------------------------------------------------------------------

def test_get_grade_history_empty(data_dir):
    history = get_grade_history("student_001", "q01", data_dir)
    assert history == []


def test_get_grade_history_single(data_dir):
    grade = _make_grade(version=1)
    store_grade(grade, data_dir)
    history = get_grade_history("student_001", "q01", data_dir)
    assert len(history) == 1
    assert history[0].version == 1


def test_get_grade_history_multiple_versions_sorted(data_dir):
    for v in [3, 1, 2]:
        store_grade(_make_grade(version=v, final_score=float(v) * 2), data_dir)
    history = get_grade_history("student_001", "q01", data_dir)
    assert [g.version for g in history] == [1, 2, 3]


def test_get_grade_history_isolation_by_student(data_dir):
    store_grade(_make_grade(student_id="student_001"), data_dir)
    store_grade(_make_grade(student_id="student_002"), data_dir)
    h1 = get_grade_history("student_001", "q01", data_dir)
    h2 = get_grade_history("student_002", "q01", data_dir)
    assert len(h1) == 1
    assert len(h2) == 1
    assert h1[0].student_id == "student_001"
    assert h2[0].student_id == "student_002"


def test_get_grade_history_isolation_by_question(data_dir):
    store_grade(_make_grade(question_id="q01"), data_dir)
    store_grade(_make_grade(question_id="q02"), data_dir)
    h1 = get_grade_history("student_001", "q01", data_dir)
    h2 = get_grade_history("student_001", "q02", data_dir)
    assert len(h1) == 1
    assert len(h2) == 1
