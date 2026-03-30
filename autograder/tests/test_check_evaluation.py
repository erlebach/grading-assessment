"""Tests for T3.1 — check_evaluation.py.

Tests are written from the spec (TASK_LIST.md T3.1), not from the implementation.
LLM calls are mocked so tests run offline without Ollama.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from grading_dynamic_rubrics.check_evaluation import (
    _parse_llm_response,
    apply_human_override,
    evaluate_check_hybrid,
    evaluate_check_llm,
    evaluate_checks_llm,
    HybridCheckEvaluation,
)
from grading_pipeline.models import (
    Check,
    CheckCategory,
    CheckEvaluation,
    CheckEvaluationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_check(
    check_id: str = "q01_check_1",
    text: str = "Student defines 'object' correctly",
    category: CheckCategory = CheckCategory.SEMANTIC,
    weight: float = 1.0,
    question_id: str = "q01",
) -> Check:
    return Check(
        id=check_id,
        text=text,
        category=category,
        weight=weight,
        question_id=question_id,
    )


def _mock_llm(json_payload: dict) -> MagicMock:
    """Return a mock LLM whose .complete() returns the given JSON payload."""
    llm = MagicMock()
    response = MagicMock()
    response.text = json.dumps(json_payload)
    llm.complete.return_value = response
    return llm


QUESTION = "What is an object in object-oriented programming?"
ANSWER_PASS = "An object is an instance of a class that encapsulates data (attributes) and behaviour (methods)."
ANSWER_FAIL = "I don't know, maybe something round?"
ANSWER_PARTIAL = "An object has attributes but I am not sure about methods."
EVIDENCE = "Objects are instances of classes. They bundle state (attributes) and behaviour (methods)."


# ---------------------------------------------------------------------------
# Unit tests: _parse_llm_response
# ---------------------------------------------------------------------------

class TestParseLlmResponse:
    def test_valid_json(self):
        raw = '{"result": "pass", "evidence": "student nailed it", "confidence": 0.95}'
        data = _parse_llm_response(raw, "q01_check_1")
        assert data["result"] == "pass"
        assert data["confidence"] == 0.95

    def test_json_inside_markdown_fence(self):
        raw = '```json\n{"result": "fail", "evidence": "wrong", "confidence": 0.8}\n```'
        data = _parse_llm_response(raw, "q01_check_1")
        assert data["result"] == "fail"

    def test_json_with_surrounding_text(self):
        raw = 'Here is my evaluation:\n{"result": "unclear", "evidence": "partial", "confidence": 0.5}\nDone.'
        data = _parse_llm_response(raw, "q01_check_1")
        assert data["result"] == "unclear"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            _parse_llm_response("Not JSON at all.", "q01_check_1")

    def test_json_missing_result_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            _parse_llm_response('{"evidence": "something"}', "q01_check_1")


# ---------------------------------------------------------------------------
# Unit tests: evaluate_check_llm
# ---------------------------------------------------------------------------

class TestEvaluateCheckLlm:
    def test_pass_result(self):
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "student defined it well", "confidence": 0.95})
        result = evaluate_check_llm(check, QUESTION, ANSWER_PASS, evidence=EVIDENCE, llm=llm)

        assert isinstance(result, CheckEvaluation)
        assert result.check_id == "q01_check_1"
        assert result.result == CheckEvaluationResult.PASS
        assert result.score == 1.0
        assert result.confidence == 0.95
        assert "student defined it well" in result.evidence
        assert result.grader == "llm"

    def test_fail_result(self):
        check = _make_check()
        llm = _mock_llm({"result": "fail", "evidence": "answer is irrelevant", "confidence": 0.98})
        result = evaluate_check_llm(check, QUESTION, ANSWER_FAIL, evidence=EVIDENCE, llm=llm)

        assert result.result == CheckEvaluationResult.FAIL
        assert result.score == 0.0
        assert result.confidence == 0.98

    def test_unclear_result_scores_zero(self):
        check = _make_check()
        llm = _mock_llm({"result": "unclear", "evidence": "partial mention", "confidence": 0.6})
        result = evaluate_check_llm(check, QUESTION, ANSWER_PARTIAL, evidence=EVIDENCE, llm=llm)

        assert result.result == CheckEvaluationResult.UNCLEAR
        assert result.score == 0.0  # unclear treated as fail for scoring

    def test_confidence_clamped_to_0_1(self):
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "ok", "confidence": 1.5})
        result = evaluate_check_llm(check, QUESTION, ANSWER_PASS, llm=llm)
        assert result.confidence == 1.0

    def test_confidence_clamped_negative(self):
        check = _make_check()
        llm = _mock_llm({"result": "fail", "evidence": "bad", "confidence": -0.3})
        result = evaluate_check_llm(check, QUESTION, ANSWER_FAIL, llm=llm)
        assert result.confidence == 0.0

    def test_unknown_result_defaults_to_unclear(self):
        check = _make_check()
        llm = _mock_llm({"result": "maybe", "evidence": "not sure", "confidence": 0.5})
        result = evaluate_check_llm(check, QUESTION, ANSWER_PARTIAL, llm=llm)
        assert result.result == CheckEvaluationResult.UNCLEAR

    def test_no_evidence_still_works(self):
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "looks good", "confidence": 0.9})
        result = evaluate_check_llm(check, QUESTION, ANSWER_PASS, evidence=None, llm=llm)
        assert result.result == CheckEvaluationResult.PASS

    def test_llm_prompt_contains_check_text(self):
        """Verify the LLM receives check text in its prompt."""
        check = _make_check(text="Student names at least two OOP principles")
        llm = _mock_llm({"result": "pass", "evidence": "listed encapsulation and inheritance", "confidence": 0.9})
        evaluate_check_llm(check, QUESTION, ANSWER_PASS, llm=llm)
        called_prompt = llm.complete.call_args[0][0]
        assert "Student names at least two OOP principles" in called_prompt
        assert QUESTION in called_prompt
        assert ANSWER_PASS in called_prompt

    def test_llm_failure_raises_valueerror(self):
        check = _make_check()
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("Ollama not running")
        with pytest.raises(ValueError, match="LLM call failed"):
            evaluate_check_llm(check, QUESTION, ANSWER_PASS, llm=llm, max_retries=1)

    def test_retries_on_empty_response(self):
        check = _make_check()
        llm = MagicMock()
        good_response = MagicMock()
        good_response.text = json.dumps({"result": "pass", "evidence": "ok", "confidence": 0.9})
        empty_response = MagicMock()
        empty_response.text = ""
        # First call returns empty, second returns good
        llm.complete.side_effect = [empty_response, good_response]
        result = evaluate_check_llm(check, QUESTION, ANSWER_PASS, llm=llm, max_retries=3)
        assert result.result == CheckEvaluationResult.PASS


# ---------------------------------------------------------------------------
# Unit tests: evaluate_checks_llm
# ---------------------------------------------------------------------------

class TestEvaluateChecksLlm:
    def _checks(self):
        return [
            _make_check("q01_check_1", "Defines object correctly"),
            _make_check("q01_check_2", "Mentions class as blueprint", category=CheckCategory.SEMANTIC),
            _make_check("q01_check_3", "Gives a concrete example", category=CheckCategory.APPLICATION),
        ]

    def test_returns_one_evaluation_per_check(self):
        checks = self._checks()
        payloads = [
            {"result": "pass", "evidence": "good", "confidence": 0.9},
            {"result": "fail", "evidence": "missing", "confidence": 0.8},
            {"result": "unclear", "evidence": "vague", "confidence": 0.5},
        ]
        llm = MagicMock()
        llm.complete.side_effect = [
            MagicMock(text=json.dumps(p)) for p in payloads
        ]
        results = evaluate_checks_llm(checks, QUESTION, ANSWER_PASS, llm=llm)
        assert len(results) == 3
        assert results[0].result == CheckEvaluationResult.PASS
        assert results[1].result == CheckEvaluationResult.FAIL
        assert results[2].result == CheckEvaluationResult.UNCLEAR

    def test_failed_check_does_not_abort_rest(self):
        """If one check evaluation fails, the rest still complete."""
        checks = self._checks()
        good = MagicMock(text=json.dumps({"result": "pass", "evidence": "ok", "confidence": 0.9}))
        llm = MagicMock()
        # First call raises, others succeed
        llm.complete.side_effect = [RuntimeError("boom"), good, good]
        results = evaluate_checks_llm(checks, QUESTION, ANSWER_PASS, llm=llm, max_retries=1)
        assert len(results) == 3
        assert results[0].result == CheckEvaluationResult.FAIL
        assert results[0].confidence == 0.0
        assert "Evaluation failed" in results[0].evidence
        assert results[1].result == CheckEvaluationResult.PASS
        assert results[2].result == CheckEvaluationResult.PASS

    def test_check_ids_preserved_in_order(self):
        checks = self._checks()
        payloads = [{"result": "pass", "evidence": "e", "confidence": 0.9}] * 3
        llm = MagicMock()
        llm.complete.side_effect = [MagicMock(text=json.dumps(p)) for p in payloads]
        results = evaluate_checks_llm(checks, QUESTION, ANSWER_PASS, llm=llm)
        ids = [r.check_id for r in results]
        assert ids == ["q01_check_1", "q01_check_2", "q01_check_3"]

    def test_empty_checks_returns_empty_list(self):
        llm = MagicMock()
        results = evaluate_checks_llm([], QUESTION, ANSWER_PASS, llm=llm)
        assert results == []
        llm.complete.assert_not_called()


# ---------------------------------------------------------------------------
# Unit tests: T3.2 — evaluate_check_hybrid / apply_human_override
# ---------------------------------------------------------------------------

class TestEvaluateCheckHybrid:
    def test_high_confidence_no_review(self):
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "clear answer", "confidence": 0.95})
        hybrid = evaluate_check_hybrid(check, QUESTION, ANSWER_PASS, llm=llm)

        assert isinstance(hybrid, HybridCheckEvaluation)
        assert hybrid.needs_review is False
        assert hybrid.human_override is None
        assert hybrid.final_evaluation.result == CheckEvaluationResult.PASS

    def test_low_confidence_flags_for_review(self):
        check = _make_check()
        llm = _mock_llm({"result": "unclear", "evidence": "borderline", "confidence": 0.5})
        hybrid = evaluate_check_hybrid(check, QUESTION, ANSWER_PARTIAL, llm=llm,
                                       confidence_threshold=0.9)

        assert hybrid.needs_review is True
        assert hybrid.human_override is None

    def test_confidence_exactly_at_threshold_no_review(self):
        """confidence == threshold should NOT trigger review (strict less-than)."""
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "ok", "confidence": 0.9})
        hybrid = evaluate_check_hybrid(check, QUESTION, ANSWER_PASS, llm=llm,
                                       confidence_threshold=0.9)
        assert hybrid.needs_review is False

    def test_configurable_threshold(self):
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "ok", "confidence": 0.75})
        # With threshold=0.8, 0.75 < 0.8 → needs review
        hybrid_high = evaluate_check_hybrid(check, QUESTION, ANSWER_PASS, llm=llm,
                                            confidence_threshold=0.8)
        assert hybrid_high.needs_review is True

        llm2 = _mock_llm({"result": "pass", "evidence": "ok", "confidence": 0.75})
        # With threshold=0.7, 0.75 >= 0.7 → no review
        hybrid_low = evaluate_check_hybrid(check, QUESTION, ANSWER_PASS, llm=llm2,
                                           confidence_threshold=0.7)
        assert hybrid_low.needs_review is False

    def test_llm_evaluation_stored(self):
        check = _make_check()
        llm = _mock_llm({"result": "fail", "evidence": "wrong answer", "confidence": 0.98})
        hybrid = evaluate_check_hybrid(check, QUESTION, ANSWER_FAIL, llm=llm)

        assert hybrid.llm_evaluation.result == CheckEvaluationResult.FAIL
        assert hybrid.llm_evaluation.grader == "llm"
        assert hybrid.confidence_threshold == 0.9  # default

    def test_final_evaluation_returns_llm_when_no_override(self):
        check = _make_check()
        llm = _mock_llm({"result": "pass", "evidence": "ok", "confidence": 0.9})
        hybrid = evaluate_check_hybrid(check, QUESTION, ANSWER_PASS, llm=llm)
        assert hybrid.final_evaluation is hybrid.llm_evaluation


class TestApplyHumanOverride:
    def _make_hybrid(self, confidence: float = 0.5) -> HybridCheckEvaluation:
        check = _make_check()
        llm = _mock_llm({"result": "unclear", "evidence": "borderline", "confidence": confidence})
        return evaluate_check_hybrid(check, QUESTION, ANSWER_PARTIAL, llm=llm,
                                     confidence_threshold=0.9)

    def test_override_stores_human_evaluation(self):
        hybrid = self._make_hybrid()
        updated = apply_human_override(hybrid, CheckEvaluationResult.PASS, "Clearly passes on review")

        assert updated.human_override is not None
        assert updated.human_override.result == CheckEvaluationResult.PASS
        assert updated.human_override.score == 1.0
        assert updated.human_override.evidence == "Clearly passes on review"
        assert updated.human_override.grader == "human"
        assert updated.human_override.confidence == 1.0

    def test_override_clears_needs_review(self):
        hybrid = self._make_hybrid(confidence=0.4)
        assert hybrid.needs_review is True
        updated = apply_human_override(hybrid, CheckEvaluationResult.FAIL, "Definitely wrong")
        assert updated.needs_review is False

    def test_final_evaluation_returns_human_override(self):
        hybrid = self._make_hybrid()
        updated = apply_human_override(hybrid, CheckEvaluationResult.PASS, "Reviewer confirmed pass")
        assert updated.final_evaluation is updated.human_override
        assert updated.final_evaluation.result == CheckEvaluationResult.PASS

    def test_llm_evaluation_preserved_after_override(self):
        hybrid = self._make_hybrid(confidence=0.5)
        original_llm = hybrid.llm_evaluation
        updated = apply_human_override(hybrid, CheckEvaluationResult.PASS, "Overriding")
        assert updated.llm_evaluation is original_llm

    def test_custom_grader_label(self):
        hybrid = self._make_hybrid()
        updated = apply_human_override(hybrid, CheckEvaluationResult.FAIL, "Wrong", grader="instructor_jones")
        assert updated.human_override.grader == "instructor_jones"

    def test_unclear_override_scores_zero(self):
        hybrid = self._make_hybrid()
        updated = apply_human_override(hybrid, CheckEvaluationResult.UNCLEAR, "Still borderline")
        assert updated.human_override.score == 0.0

    def test_fail_override_scores_zero(self):
        hybrid = self._make_hybrid()
        updated = apply_human_override(hybrid, CheckEvaluationResult.FAIL, "Wrong")
        assert updated.human_override.score == 0.0
