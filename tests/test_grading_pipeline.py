"""T4.2 — Integration tests for the full grading pipeline.

Tests chain: rubric checks → LLM evaluation → scoring → GradeResult.
LLM calls are mocked; realistic sample question/answer data is used.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from grading_pipeline.models import (
    Check,
    CheckCategory,
    CheckEvaluation,
    CheckEvaluationResult,
    GradeResult,
)
from grading_dynamic_rubrics.check_evaluation import (
    evaluate_checks_llm,
    evaluate_check_hybrid,
    apply_human_override,
    HybridCheckEvaluation,
)
from grading_dynamic_rubrics.scoring import compute_final_score, load_category_weights


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
            text="Student defines 'object' as an instance of a class",
            category=CheckCategory.SEMANTIC,
            weight=1.0,
            question_id="q01",
        ),
        Check(
            id="q01_check_2",
            text="Student mentions attributes and methods",
            category=CheckCategory.SEMANTIC,
            weight=1.0,
            question_id="q01",
        ),
        Check(
            id="q01_check_3",
            text="Student provides a concrete example of an object",
            category=CheckCategory.APPLICATION,
            weight=1.5,
            question_id="q01",
        ),
    ]


def _llm_pass(check_ids: list[str]) -> MagicMock:
    """Return an LLM mock that passes the given check ids and fails the rest."""
    import json

    llm = MagicMock()

    def _side_effect(prompt):
        resp = MagicMock()
        # Determine which check is being evaluated from the prompt
        result = "fail"
        for cid in check_ids:
            if cid in prompt:
                result = "pass"
                break
        resp.text = json.dumps(
            {"result": result, "evidence": "test evidence", "confidence": 0.95}
        )
        return resp

    llm.complete.side_effect = _side_effect
    return llm


def _llm_all_pass() -> MagicMock:
    import json

    llm = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps(
        {"result": "pass", "evidence": "correct answer", "confidence": 0.95}
    )
    llm.complete.return_value = resp
    return llm


def _llm_all_fail() -> MagicMock:
    import json

    llm = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps(
        {"result": "fail", "evidence": "missing content", "confidence": 0.95}
    )
    llm.complete.return_value = resp
    return llm


# ---------------------------------------------------------------------------
# Happy path: all checks pass
# ---------------------------------------------------------------------------

class TestGradingPipelineAllPass:
    def test_evaluations_returned(self, sample_checks, category_weights):
        llm = _llm_all_pass()
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="What is an object in OOP?",
            student_answer="An object is an instance of a class with attributes and methods. Example: a Car object.",
            llm=llm,
        )
        assert len(evaluations) == 3

    def test_all_pass_score_is_ten(self, sample_checks, category_weights):
        llm = _llm_all_pass()
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="What is an object in OOP?",
            student_answer="An object is an instance of a class with attributes and methods. Example: a Car object.",
            llm=llm,
        )
        _, final_score = compute_final_score(sample_checks, evaluations, category_weights)
        assert final_score == pytest.approx(10.0)

    def test_grade_calculation_counts(self, sample_checks, category_weights):
        llm = _llm_all_pass()
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="What is an object in OOP?",
            student_answer="An object is an instance of a class.",
            llm=llm,
        )
        calc, _ = compute_final_score(sample_checks, evaluations, category_weights)
        assert calc.checks_passed == 3
        assert calc.checks_failed == 0
        assert calc.checks_unclear == 0


# ---------------------------------------------------------------------------
# Happy path: all checks fail
# ---------------------------------------------------------------------------

class TestGradingPipelineAllFail:
    def test_all_fail_score_is_zero(self, sample_checks, category_weights):
        llm = _llm_all_fail()
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="What is an object in OOP?",
            student_answer="I don't know.",
            llm=llm,
        )
        _, final_score = compute_final_score(sample_checks, evaluations, category_weights)
        assert final_score == pytest.approx(0.0)

    def test_all_fail_grade_counts(self, sample_checks, category_weights):
        llm = _llm_all_fail()
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="What is an object in OOP?",
            student_answer="I don't know.",
            llm=llm,
        )
        calc, _ = compute_final_score(sample_checks, evaluations, category_weights)
        assert calc.checks_failed == 3
        assert calc.checks_passed == 0


# ---------------------------------------------------------------------------
# Mixed results
# ---------------------------------------------------------------------------

class TestGradingPipelineMixed:
    def test_partial_pass_score_between_zero_and_ten(self, sample_checks, category_weights):
        import json

        call_count = 0
        results = ["pass", "fail", "fail"]

        llm = MagicMock()

        def _side(prompt):
            nonlocal call_count
            r = MagicMock()
            r.text = json.dumps(
                {"result": results[call_count % len(results)], "evidence": "x", "confidence": 0.9}
            )
            call_count += 1
            return r

        llm.complete.side_effect = _side
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="Q?",
            student_answer="partial answer",
            llm=llm,
        )
        _, score = compute_final_score(sample_checks, evaluations, category_weights)
        assert 0.0 < score < 10.0

    def test_unclear_treated_as_fail_in_mixed(self, sample_checks, category_weights):
        import json

        llm = MagicMock()
        results = ["pass", "unclear", "fail"]
        call_count = 0

        def _side(prompt):
            nonlocal call_count
            r = MagicMock()
            r.text = json.dumps(
                {"result": results[call_count % len(results)], "evidence": "x", "confidence": 0.5}
            )
            call_count += 1
            return r

        llm.complete.side_effect = _side
        evaluations = evaluate_checks_llm(
            sample_checks,
            question_text="Q?",
            student_answer="partial",
            llm=llm,
        )
        calc, _ = compute_final_score(sample_checks, evaluations, category_weights)
        assert calc.checks_unclear == 1
        assert calc.checks_passed == 1
        assert calc.checks_failed == 1


# ---------------------------------------------------------------------------
# Hybrid evaluation + human override integration
# ---------------------------------------------------------------------------

class TestHybridEvaluationIntegration:
    def test_high_confidence_auto_graded(self, sample_checks, category_weights):
        """High-confidence LLM result should be auto-graded (no review needed)."""
        import json

        llm = MagicMock()
        resp = MagicMock()
        resp.text = json.dumps({"result": "pass", "evidence": "correct", "confidence": 0.95})
        llm.complete.return_value = resp

        hybrid = evaluate_check_hybrid(
            sample_checks[0],
            question_text="What is an object?",
            student_answer="An object is an instance of a class.",
            llm=llm,
            confidence_threshold=0.9,
        )
        assert isinstance(hybrid, HybridCheckEvaluation)
        assert not hybrid.needs_review
        assert hybrid.final_evaluation.result == CheckEvaluationResult.PASS

    def test_low_confidence_flags_for_review(self, sample_checks):
        """Low-confidence LLM result should be flagged for human review."""
        import json

        llm = MagicMock()
        resp = MagicMock()
        resp.text = json.dumps({"result": "unclear", "evidence": "ambiguous", "confidence": 0.5})
        llm.complete.return_value = resp

        hybrid = evaluate_check_hybrid(
            sample_checks[0],
            question_text="What is an object?",
            student_answer="...",
            llm=llm,
            confidence_threshold=0.9,
        )
        assert hybrid.needs_review

    def test_human_override_changes_result(self, sample_checks):
        """Human override should change the final evaluation."""
        import json

        llm = MagicMock()
        resp = MagicMock()
        resp.text = json.dumps({"result": "fail", "evidence": "wrong", "confidence": 0.95})
        llm.complete.return_value = resp

        hybrid = evaluate_check_hybrid(
            sample_checks[0],
            question_text="What is an object?",
            student_answer="...",
            llm=llm,
        )
        overridden = apply_human_override(
            hybrid,
            result=CheckEvaluationResult.PASS,
            evidence="Instructor re-read and found it correct",
        )
        assert overridden.final_evaluation.result == CheckEvaluationResult.PASS
        assert not overridden.needs_review


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestGradingPipelineEdgeCases:
    def test_single_check_pass(self, category_weights):
        checks = [
            Check(
                id="q01_check_1",
                text="Student mentions class",
                category=CheckCategory.SEMANTIC,
                weight=1.0,
                question_id="q01",
            )
        ]
        evals = [
            CheckEvaluation(
                check_id="q01_check_1",
                result=CheckEvaluationResult.PASS,
                score=1.0,
                evidence="mentioned class",
                confidence=0.9,
            )
        ]
        _, score = compute_final_score(checks, evals, category_weights)
        assert score == pytest.approx(10.0)

    def test_missing_evaluation_treated_as_fail(self, sample_checks, category_weights):
        """If evaluations list is shorter than checks, missing ones count as fail."""
        # Only provide evaluation for first check
        evals = [
            CheckEvaluation(
                check_id="q01_check_1",
                result=CheckEvaluationResult.PASS,
                score=1.0,
                evidence="ok",
                confidence=0.9,
            )
        ]
        calc, score = compute_final_score(sample_checks, evals, category_weights)
        assert score < 10.0
        assert calc.checks_failed == 2
