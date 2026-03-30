"""Tests for grading_pipeline/models.py (T1.2).

All tests are derived from the T1.2 specification:
  - Models validate on instantiation
  - Can serialize/deserialize to JSON
  - Validation rules:
      * CheckEvaluation: score must be 1.0 for PASS, 0.0 for FAIL
      * Appeal: new_score must be >= original_score (upward only)
      * GradeResult.final_score: 0.0 – 10.0
      * Check.weight: must be > 0
      * Rubric.version, GradeResult.version: must be >= 1

Spec reference: TASK_LIST.md §T1.2 and config/grading_config.yaml §appeals.
"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from grading_pipeline.models import (
    Appeal,
    Check,
    CheckCategory,
    CheckEvaluation,
    CheckEvaluationResult,
    GradeCalculation,
    GradeResult,
    Rubric,
)


# ---------------------------------------------------------------------------
# Helpers — minimal valid objects per spec
# ---------------------------------------------------------------------------

def make_check(**overrides) -> dict:
    base = dict(id="q01_d1_c1", text="Student defines X.", category="semantic",
                weight=1.0, question_id="q01")
    return {**base, **overrides}


def make_evaluation(**overrides) -> dict:
    base = dict(check_id="q01_d1_c1", result="pass", score=1.0,
                evidence="Student wrote a correct definition.")
    return {**base, **overrides}


def make_calculation(**overrides) -> dict:
    base = dict(total_checks=3, checks_passed=2, checks_failed=1, checks_unclear=0,
                weighted_sum=6.0, weight_denominator=9.0, final_score=6.67)
    return {**base, **overrides}


def make_grade_result(**overrides) -> dict:
    calc = GradeCalculation(**make_calculation())
    ev = CheckEvaluation(**make_evaluation())
    base = dict(id="s1_q01_v1", question_id="q01", student_id="s1",
                rubric_id="q01_rubric", rubric_version=1,
                check_evaluations=[ev], calculation=calc, final_score=7.5)
    return {**base, **overrides}


def make_appeal(**overrides) -> dict:
    base = dict(id="ap_s1_q01_v1", original_grade_id="s1_q01_v1",
                student_id="s1", question_id="q01",
                original_score=6.0, new_score=7.0,
                reason="Definition was partially correct.")
    return {**base, **overrides}


# ===========================================================================
# Check
# ===========================================================================

class TestCheck:
    def test_valid_check_instantiates(self):
        c = Check(**make_check())
        assert c.id == "q01_d1_c1"
        assert c.category == CheckCategory.SEMANTIC

    def test_category_enum_values(self):
        for cat in ("semantic", "application", "clarity"):
            c = Check(**make_check(category=cat))
            assert c.category.value == cat

    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            Check(**make_check(category="unknown"))

    def test_weight_must_be_positive(self):
        with pytest.raises(ValidationError):
            Check(**make_check(weight=0))
        with pytest.raises(ValidationError):
            Check(**make_check(weight=-1.0))

    def test_id_and_question_id_required(self):
        data = make_check()
        del data["id"]
        with pytest.raises(ValidationError):
            Check(**data)
        data = make_check()
        del data["question_id"]
        with pytest.raises(ValidationError):
            Check(**data)

    def test_optional_fields_default_to_none(self):
        c = Check(**make_check())
        assert c.rubric_id is None
        assert c.dimension_id is None
        assert c.evidence is None

    def test_json_round_trip(self):
        c = Check(**make_check())
        restored = Check.model_validate_json(c.model_dump_json())
        assert restored == c


# ===========================================================================
# Rubric
# ===========================================================================

class TestRubric:
    def test_valid_rubric_instantiates(self):
        r = Rubric(id="q01_rubric", question_id="q01",
                   title="Q01 Rubric", description="Test rubric")
        assert r.version == 1
        assert r.checks == []
        assert r.total_points == 10.0

    def test_rubric_with_checks(self):
        checks = [Check(**make_check(id=f"q01_d1_c{i}")) for i in range(1, 4)]
        r = Rubric(id="q01_rubric", question_id="q01",
                   title="Q01", description="desc", checks=checks)
        assert len(r.checks) == 3

    def test_version_must_be_at_least_1(self):
        with pytest.raises(ValidationError):
            Rubric(id="r", question_id="q01", title="t", description="d", version=0)

    def test_total_points_must_be_positive(self):
        with pytest.raises(ValidationError):
            Rubric(id="r", question_id="q01", title="t", description="d",
                   total_points=0)

    def test_created_at_defaults_to_now(self):
        before = datetime.utcnow()
        r = Rubric(id="r", question_id="q01", title="t", description="d")
        after = datetime.utcnow()
        assert before <= r.created_at <= after

    def test_json_round_trip(self):
        r = Rubric(id="q01_rubric", question_id="q01",
                   title="Q01 Rubric", description="desc")
        restored = Rubric.model_validate_json(r.model_dump_json())
        assert restored.id == r.id
        assert restored.version == r.version


# ===========================================================================
# CheckEvaluation — spec: score must match result
# ===========================================================================

class TestCheckEvaluation:
    def test_pass_with_score_one(self):
        ev = CheckEvaluation(**make_evaluation(result="pass", score=1.0))
        assert ev.result == CheckEvaluationResult.PASS
        assert ev.score == 1.0

    def test_fail_with_score_zero(self):
        ev = CheckEvaluation(**make_evaluation(result="fail", score=0.0))
        assert ev.result == CheckEvaluationResult.FAIL
        assert ev.score == 0.0

    def test_unclear_allowed_with_any_valid_score(self):
        # unclear does not enforce score value per spec
        ev = CheckEvaluation(**make_evaluation(result="unclear", score=0.0))
        assert ev.result == CheckEvaluationResult.UNCLEAR

    def test_pass_with_wrong_score_raises(self):
        with pytest.raises(ValidationError):
            CheckEvaluation(**make_evaluation(result="pass", score=0.0))

    def test_fail_with_wrong_score_raises(self):
        with pytest.raises(ValidationError):
            CheckEvaluation(**make_evaluation(result="fail", score=1.0))

    def test_score_bounded_0_to_1(self):
        with pytest.raises(ValidationError):
            CheckEvaluation(**make_evaluation(result="pass", score=1.5))
        with pytest.raises(ValidationError):
            CheckEvaluation(**make_evaluation(result="fail", score=-0.1))

    def test_evidence_required(self):
        data = make_evaluation()
        del data["evidence"]
        with pytest.raises(ValidationError):
            CheckEvaluation(**data)

    def test_grader_defaults_to_llm(self):
        ev = CheckEvaluation(**make_evaluation())
        assert ev.grader == "llm"

    def test_json_round_trip(self):
        ev = CheckEvaluation(**make_evaluation())
        restored = CheckEvaluation.model_validate_json(ev.model_dump_json())
        assert restored == ev


# ===========================================================================
# GradeResult
# ===========================================================================

class TestGradeResult:
    def test_valid_grade_result_instantiates(self):
        gr = GradeResult(**make_grade_result())
        assert gr.version == 1
        assert gr.is_appeal() is False

    def test_version_above_1_is_appeal(self):
        gr = GradeResult(**make_grade_result(version=2))
        assert gr.is_appeal() is True

    def test_final_score_bounded_0_to_10(self):
        with pytest.raises(ValidationError):
            GradeResult(**make_grade_result(final_score=-0.1))
        with pytest.raises(ValidationError):
            GradeResult(**make_grade_result(final_score=10.1))

    def test_rubric_version_must_be_at_least_1(self):
        with pytest.raises(ValidationError):
            GradeResult(**make_grade_result(rubric_version=0))

    def test_json_round_trip(self):
        gr = GradeResult(**make_grade_result())
        restored = GradeResult.model_validate_json(gr.model_dump_json())
        assert restored.id == gr.id
        assert restored.final_score == gr.final_score


# ===========================================================================
# Appeal — spec: only upward adjustments allowed
# ===========================================================================

class TestAppeal:
    def test_valid_appeal_instantiates(self):
        ap = Appeal(**make_appeal())
        assert ap.decision == "pending"
        assert ap.is_approved() is False

    def test_new_score_higher_than_original_allowed(self):
        ap = Appeal(**make_appeal(original_score=5.0, new_score=7.0))
        assert ap.new_score == 7.0

    def test_new_score_equal_to_original_allowed(self):
        # Equal is not a decrease — should be valid
        ap = Appeal(**make_appeal(original_score=6.0, new_score=6.0))
        assert ap.new_score == 6.0

    def test_new_score_lower_than_original_raises(self):
        # Spec: only upward adjustments
        with pytest.raises(ValidationError):
            Appeal(**make_appeal(original_score=7.0, new_score=6.0))

    def test_decision_defaults_to_pending(self):
        ap = Appeal(**make_appeal())
        assert ap.decision == "pending"

    def test_approved_decision(self):
        ap = Appeal(**make_appeal(decision="approved"))
        assert ap.is_approved() is True

    def test_denied_decision(self):
        ap = Appeal(**make_appeal(decision="denied"))
        assert ap.is_approved() is False

    def test_invalid_decision_raises(self):
        with pytest.raises(ValidationError):
            Appeal(**make_appeal(decision="maybe"))

    def test_score_boundaries(self):
        with pytest.raises(ValidationError):
            Appeal(**make_appeal(original_score=-1.0, new_score=0.0))
        with pytest.raises(ValidationError):
            Appeal(**make_appeal(original_score=9.0, new_score=11.0))

    def test_json_round_trip(self):
        ap = Appeal(**make_appeal())
        restored = Appeal.model_validate_json(ap.model_dump_json())
        assert restored.id == ap.id
        assert restored.original_score == ap.original_score
