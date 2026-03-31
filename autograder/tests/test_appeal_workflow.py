"""T4.2 — Integration tests for grade appeals and recalculation workflow.

Tests the full appeal cycle:
  store initial grade → submit appeal → validate → store revised grade
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

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
from grading_dynamic_rubrics.scoring import compute_final_score, load_category_weights


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def config_path():
    return Path(__file__).parent.parent / "config" / "grading_categories.yaml"


@pytest.fixture
def category_weights(config_path):
    return load_category_weights(config_path)


@pytest.fixture
def sample_checks():
    return [
        Check(
            id="q01_check_1",
            text="Student defines object correctly",
            category=CheckCategory.SEMANTIC,
            weight=1.0,
            question_id="q01",
        ),
        Check(
            id="q01_check_2",
            text="Student gives an example",
            category=CheckCategory.APPLICATION,
            weight=1.5,
            question_id="q01",
        ),
    ]


def _make_grade(
    student_id: str,
    question_id: str,
    score: float,
    checks_passed: int,
    checks_failed: int,
    version: int = 1,
) -> GradeResult:
    calc = GradeCalculation(
        total_checks=checks_passed + checks_failed,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        checks_unclear=0,
        weighted_sum=float(checks_passed),
        weight_denominator=float(max(checks_passed + checks_failed, 1)),
        final_score=score,
    )
    return GradeResult(
        id=f"{student_id}_{question_id}_v{version}",
        student_id=student_id,
        question_id=question_id,
        rubric_id=f"{question_id}_rubric",
        rubric_version=1,
        final_score=score,
        version=version,
        calculation=calc,
        check_evaluations=[],
    )


# ---------------------------------------------------------------------------
# Happy path: store → appeal → revised grade
# ---------------------------------------------------------------------------

class TestAppealHappyPath:
    def test_store_initial_grade(self, data_dir):
        grade = _make_grade("student_001", "q01", score=6.0, checks_passed=1, checks_failed=1)
        path = store_grade(grade, data_dir)
        assert path.exists()

    def test_store_appeal(self, data_dir):
        grade = _make_grade("student_001", "q01", score=6.0, checks_passed=1, checks_failed=1)
        store_grade(grade, data_dir)

        appeal = Appeal(
            id="appeal_student_001_q01_v1",
            original_grade_id="student_001_q01_v1",
            student_id="student_001",
            question_id="q01",
            original_score=6.0,
            new_score=8.0,
            reason="The grader missed my second example.",
            requested_at=datetime(2026, 3, 30, 10, 0, 0),
        )
        path = store_grade_appeal(appeal, data_dir)
        assert path.exists()

    def test_revised_grade_stored_with_higher_version(self, data_dir):
        grade_v1 = _make_grade("student_001", "q01", score=6.0, checks_passed=1, checks_failed=1, version=1)
        store_grade(grade_v1, data_dir)

        grade_v2 = _make_grade("student_001", "q01", score=8.0, checks_passed=2, checks_failed=0, version=2)
        path = store_grade(grade_v2, data_dir)
        assert path.exists()

    def test_grade_history_contains_both_versions(self, data_dir):
        grade_v1 = _make_grade("student_001", "q01", score=6.0, checks_passed=1, checks_failed=1, version=1)
        store_grade(grade_v1, data_dir)
        grade_v2 = _make_grade("student_001", "q01", score=8.0, checks_passed=2, checks_failed=0, version=2)
        store_grade(grade_v2, data_dir)

        history = get_grade_history("student_001", "q01", data_dir)
        assert len(history) == 2
        assert history[0].version == 1
        assert history[1].version == 2

    def test_grade_history_scores_match(self, data_dir):
        grade_v1 = _make_grade("student_001", "q01", score=6.0, checks_passed=1, checks_failed=1, version=1)
        store_grade(grade_v1, data_dir)
        grade_v2 = _make_grade("student_001", "q01", score=8.0, checks_passed=2, checks_failed=0, version=2)
        store_grade(grade_v2, data_dir)

        history = get_grade_history("student_001", "q01", data_dir)
        assert history[0].final_score == pytest.approx(6.0)
        assert history[1].final_score == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# Validate grade increase constraint
# ---------------------------------------------------------------------------

class TestGradeIncreaseValidation:
    def test_equal_score_allowed(self):
        validate_grade_increase(7.0, 7.0)  # should not raise

    def test_higher_score_allowed(self):
        validate_grade_increase(6.0, 8.0)  # should not raise

    def test_lower_score_rejected(self):
        with pytest.raises(ValueError, match="upward"):
            validate_grade_increase(8.0, 6.0)

    def test_appeal_model_rejects_downward_score(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Appeal(
                id="appeal_student_001_q01_v1",
                original_grade_id="student_001_q01_v1",
                student_id="student_001",
                question_id="q01",
                original_score=8.0,
                new_score=5.0,  # downward — must be rejected
                reason="trying to lower grade",
                requested_at=datetime(2026, 3, 30, 10, 0, 0),
            )


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestAppealErrorCases:
    def test_cannot_overwrite_existing_grade(self, data_dir):
        grade = _make_grade("student_001", "q01", score=6.0, checks_passed=1, checks_failed=1, version=1)
        store_grade(grade, data_dir)
        with pytest.raises(FileExistsError):
            store_grade(grade, data_dir)  # same student/question/version

    def test_cannot_overwrite_existing_appeal(self, data_dir):
        appeal = Appeal(
            id="appeal_student_001_q01_v1",
            original_grade_id="student_001_q01_v1",
            student_id="student_001",
            question_id="q01",
            original_score=6.0,
            new_score=8.0,
            reason="missed example",
            requested_at=datetime(2026, 3, 30, 10, 0, 0),
        )
        store_grade_appeal(appeal, data_dir)
        with pytest.raises(FileExistsError):
            store_grade_appeal(appeal, data_dir)

    def test_history_empty_for_unknown_student(self, data_dir):
        history = get_grade_history("nobody", "q99", data_dir)
        assert history == []

    def test_history_isolated_by_student(self, data_dir):
        g1 = _make_grade("alice", "q01", score=7.0, checks_passed=2, checks_failed=0, version=1)
        g2 = _make_grade("bob", "q01", score=5.0, checks_passed=1, checks_failed=1, version=1)
        store_grade(g1, data_dir)
        store_grade(g2, data_dir)

        assert len(get_grade_history("alice", "q01", data_dir)) == 1
        assert len(get_grade_history("bob", "q01", data_dir)) == 1
        assert get_grade_history("alice", "q01", data_dir)[0].final_score == pytest.approx(7.0)

    def test_history_isolated_by_question(self, data_dir):
        g1 = _make_grade("alice", "q01", score=7.0, checks_passed=2, checks_failed=0, version=1)
        g2 = _make_grade("alice", "q02", score=5.0, checks_passed=1, checks_failed=1, version=1)
        store_grade(g1, data_dir)
        store_grade(g2, data_dir)

        assert len(get_grade_history("alice", "q01", data_dir)) == 1
        assert len(get_grade_history("alice", "q02", data_dir)) == 1


# ---------------------------------------------------------------------------
# Scoring integration within appeal workflow
# ---------------------------------------------------------------------------

class TestScoringInAppealWorkflow:
    def test_revised_score_from_scoring_module(self, sample_checks, category_weights, data_dir):
        """Simulate a re-grade triggered by an appeal using the scoring module."""
        # Original grade: one check passed
        orig_evals = [
            CheckEvaluation(
                check_id="q01_check_1",
                result=CheckEvaluationResult.PASS,
                score=1.0,
                evidence="correct",
                confidence=0.9,
            ),
            CheckEvaluation(
                check_id="q01_check_2",
                result=CheckEvaluationResult.FAIL,
                score=0.0,
                evidence="missed",
                confidence=0.9,
            ),
        ]
        _, orig_score = compute_final_score(sample_checks, orig_evals, category_weights)

        # After appeal: both checks now pass
        revised_evals = [
            CheckEvaluation(
                check_id="q01_check_1",
                result=CheckEvaluationResult.PASS,
                score=1.0,
                evidence="correct",
                confidence=0.9,
            ),
            CheckEvaluation(
                check_id="q01_check_2",
                result=CheckEvaluationResult.PASS,
                score=1.0,
                evidence="example was valid after review",
                confidence=0.95,
            ),
        ]
        _, revised_score = compute_final_score(sample_checks, revised_evals, category_weights)

        assert revised_score > orig_score

        # Store both grades
        calc_orig = GradeCalculation(
            total_checks=2, checks_passed=1, checks_failed=1, checks_unclear=0,
            weighted_sum=1.0, weight_denominator=2.0, final_score=orig_score,
        )
        g_v1 = GradeResult(
            id="student_001_q01_v1",
            student_id="student_001", question_id="q01",
            rubric_id="q01_rubric", rubric_version=1,
            final_score=orig_score,
            version=1, calculation=calc_orig, check_evaluations=[],
        )
        store_grade(g_v1, data_dir)

        calc_rev = GradeCalculation(
            total_checks=2, checks_passed=2, checks_failed=0, checks_unclear=0,
            weighted_sum=2.0, weight_denominator=2.0, final_score=revised_score,
        )
        g_v2 = GradeResult(
            id="student_001_q01_v2",
            student_id="student_001", question_id="q01",
            rubric_id="q01_rubric", rubric_version=1,
            final_score=revised_score,
            version=2, calculation=calc_rev, check_evaluations=[],
        )
        store_grade(g_v2, data_dir)

        history = get_grade_history("student_001", "q01", data_dir)
        assert len(history) == 2
        assert history[1].final_score > history[0].final_score
