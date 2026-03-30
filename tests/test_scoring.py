"""Tests for T3.3 — scoring algorithm (grading_dynamic_rubrics/scoring.py)."""

from __future__ import annotations

import pytest

from grading_pipeline.models import (
    Check,
    CheckCategory,
    CheckEvaluation,
    CheckEvaluationResult,
)
from grading_dynamic_rubrics.scoring import compute_final_score, load_category_weights

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS = {
    "semantic": 1.0,
    "application": 2.0,
    "clarity": 1.0,
}


def _check(check_id: str, category: str, weight: float = 1.0) -> Check:
    return Check(
        id=check_id,
        text=f"Check {check_id}",
        category=CheckCategory(category),
        weight=weight,
        question_id="q01",
    )


def _eval(check_id: str, result: CheckEvaluationResult) -> CheckEvaluation:
    score = 1.0 if result == CheckEvaluationResult.PASS else 0.0
    return CheckEvaluation(
        check_id=check_id,
        result=result,
        score=score,
        evidence="test evidence",
    )


# ---------------------------------------------------------------------------
# All checks pass
# ---------------------------------------------------------------------------

def test_all_pass_equal_weights():
    """All checks pass with equal weights → score = 10.0."""
    checks = [
        _check("c1", "semantic", 1.0),
        _check("c2", "semantic", 1.0),
    ]
    evals = [
        _eval("c1", CheckEvaluationResult.PASS),
        _eval("c2", CheckEvaluationResult.PASS),
    ]
    calc, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert score == pytest.approx(10.0)
    assert calc.checks_passed == 2
    assert calc.checks_failed == 0
    assert calc.weighted_sum == pytest.approx(calc.weight_denominator)


# ---------------------------------------------------------------------------
# All checks fail
# ---------------------------------------------------------------------------

def test_all_fail():
    """All checks fail → score = 0.0."""
    checks = [_check("c1", "application", 2.0), _check("c2", "clarity", 1.0)]
    evals = [
        _eval("c1", CheckEvaluationResult.FAIL),
        _eval("c2", CheckEvaluationResult.FAIL),
    ]
    calc, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert score == pytest.approx(0.0)
    assert calc.checks_passed == 0
    assert calc.checks_failed == 2
    assert calc.weighted_sum == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Mixed results
# ---------------------------------------------------------------------------

def test_mixed_results_formula():
    """Verify exact formula output for a known mixed case.

    checks:
      c1: semantic, weight=1  → cat_weight=1  → effective=1
      c2: application, weight=1 → cat_weight=2 → effective=2
      c3: clarity, weight=1   → cat_weight=1  → effective=1

    evaluations: c1=PASS, c2=FAIL, c3=PASS
    weighted_sum = 1 + 0 + 1 = 2
    weight_denom = 1 + 2 + 1 = 4
    score = (2/4)*10 = 5.0
    """
    checks = [
        _check("c1", "semantic", 1.0),
        _check("c2", "application", 1.0),
        _check("c3", "clarity", 1.0),
    ]
    evals = [
        _eval("c1", CheckEvaluationResult.PASS),
        _eval("c2", CheckEvaluationResult.FAIL),
        _eval("c3", CheckEvaluationResult.PASS),
    ]
    calc, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert score == pytest.approx(5.0)
    assert calc.weighted_sum == pytest.approx(2.0)
    assert calc.weight_denominator == pytest.approx(4.0)
    assert calc.checks_passed == 2
    assert calc.checks_failed == 1


def test_mixed_different_check_weights():
    """Checks with different base weights affect score correctly.

    checks:
      c1: semantic, weight=3 → effective=3
      c2: semantic, weight=1 → effective=1

    evaluations: c1=FAIL, c2=PASS
    weighted_sum = 0 + 1 = 1
    weight_denom = 3 + 1 = 4
    score = (1/4)*10 = 2.5
    """
    checks = [
        _check("c1", "semantic", 3.0),
        _check("c2", "semantic", 1.0),
    ]
    evals = [
        _eval("c1", CheckEvaluationResult.FAIL),
        _eval("c2", CheckEvaluationResult.PASS),
    ]
    calc, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert score == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Unclear results
# ---------------------------------------------------------------------------

def test_unclear_treated_as_fail():
    """UNCLEAR evaluations count as fail for scoring."""
    checks = [_check("c1", "semantic", 1.0), _check("c2", "semantic", 1.0)]
    evals = [
        _eval("c1", CheckEvaluationResult.PASS),
        CheckEvaluation(
            check_id="c2",
            result=CheckEvaluationResult.UNCLEAR,
            score=0.0,
            evidence="unclear",
        ),
    ]
    calc, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert score == pytest.approx(5.0)
    assert calc.checks_unclear == 1
    assert calc.checks_passed == 1


# ---------------------------------------------------------------------------
# Missing evaluations
# ---------------------------------------------------------------------------

def test_missing_evaluation_treated_as_fail():
    """A check with no evaluation is treated as a fail."""
    checks = [_check("c1", "semantic", 1.0), _check("c2", "semantic", 1.0)]
    evals = [_eval("c1", CheckEvaluationResult.PASS)]  # c2 missing
    calc, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert score == pytest.approx(5.0)
    assert calc.checks_failed == 1


# ---------------------------------------------------------------------------
# Score bounds
# ---------------------------------------------------------------------------

def test_score_within_bounds():
    """Final score is always between 0 and 10 inclusive."""
    checks = [_check("c1", "application", 1.0)]
    evals = [_eval("c1", CheckEvaluationResult.PASS)]
    _, score = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert 0.0 <= score <= 10.0


# ---------------------------------------------------------------------------
# Calculation detail fields
# ---------------------------------------------------------------------------

def test_calculation_totals():
    """total_checks matches the number of checks passed in."""
    checks = [_check(f"c{i}", "semantic") for i in range(5)]
    evals = [_eval(f"c{i}", CheckEvaluationResult.PASS) for i in range(5)]
    calc, _ = compute_final_score(checks, evals, CATEGORY_WEIGHTS)
    assert calc.total_checks == 5
    assert calc.checks_passed == 5
    assert calc.checks_failed == 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_empty_checks_raises():
    """Empty checks list raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        compute_final_score([], [], CATEGORY_WEIGHTS)


def test_empty_category_weights_raises():
    """Empty category_weights raises ValueError."""
    checks = [_check("c1", "semantic")]
    evals = [_eval("c1", CheckEvaluationResult.PASS)]
    with pytest.raises(ValueError, match="empty"):
        compute_final_score(checks, evals, {})


def test_unknown_category_raises():
    """A check whose category is not in category_weights raises ValueError."""
    checks = [_check("c1", "semantic")]
    evals = [_eval("c1", CheckEvaluationResult.PASS)]
    with pytest.raises(ValueError, match="Category"):
        compute_final_score(checks, evals, {"application": 2.0})


# ---------------------------------------------------------------------------
# load_category_weights
# ---------------------------------------------------------------------------

def test_load_category_weights(tmp_path):
    """load_category_weights correctly parses a YAML config."""
    yaml_content = """
categories:
  - name: semantic
    weight: 1
  - name: application
    weight: 2
  - name: clarity
    weight: 1
"""
    cfg = tmp_path / "categories.yaml"
    cfg.write_text(yaml_content)
    weights = load_category_weights(cfg)
    assert weights == {"semantic": 1.0, "application": 2.0, "clarity": 1.0}


def test_load_category_weights_real_config():
    """load_category_weights works against the actual project config."""
    from pathlib import Path
    config_path = Path(__file__).parent.parent / "config" / "grading_categories.yaml"
    weights = load_category_weights(config_path)
    assert "semantic" in weights
    assert "application" in weights
    assert "clarity" in weights
    assert weights["application"] == pytest.approx(2.0)
