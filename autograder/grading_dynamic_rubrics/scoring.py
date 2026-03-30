"""T3.3 — Scoring algorithm for weighted checklist grading.

Public API
----------
compute_final_score(
    checks: list[Check],
    evaluations: list[CheckEvaluation],
    category_weights: dict[str, float],
) -> GradeResult-like tuple (GradeCalculation, float)

load_category_weights(config_path: str | Path) -> dict[str, float]
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from grading_pipeline.models import (
    Check,
    CheckEvaluation,
    CheckEvaluationResult,
    GradeCalculation,
)

# ---------------------------------------------------------------------------
# Category weight loader
# ---------------------------------------------------------------------------

def load_category_weights(config_path: Union[str, Path]) -> dict[str, float]:
    """Load category weights from a YAML config file.

    Parameters
    ----------
    config_path:
        Path to a YAML file containing a ``categories`` list, each entry
        having ``name`` and ``weight`` keys.

    Returns
    -------
    dict[str, float]
        Mapping of category name → weight.
    """
    path = Path(config_path)
    with path.open() as fh:
        data = yaml.safe_load(fh)
    return {cat["name"]: float(cat["weight"]) for cat in data["categories"]}


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def compute_final_score(
    checks: list[Check],
    evaluations: list[CheckEvaluation],
    category_weights: dict[str, float],
) -> tuple[GradeCalculation, float]:
    """Compute the final score from check evaluations and category weights.

    Formula
    -------
    final_score = (Σ pass_i × weight_i × cat_weight_i)
                  / (Σ weight_i × cat_weight_i) × 10

    Parameters
    ----------
    checks:
        The rubric checks that were evaluated.  Each check carries its own
        ``weight`` and ``category``.
    evaluations:
        One ``CheckEvaluation`` per check.  Matched by ``check_id``.
    category_weights:
        Mapping of category name → weight (e.g. from ``load_category_weights``).

    Returns
    -------
    (GradeCalculation, float)
        The detailed calculation object and the final score on the 0–10 scale.

    Raises
    ------
    ValueError
        If ``category_weights`` is empty or all effective weights are zero.
    ValueError
        If a check's category is not present in ``category_weights``.
    ValueError
        If ``checks`` and ``evaluations`` lists are empty.
    """
    if not checks:
        raise ValueError("checks list must not be empty")
    if not category_weights:
        raise ValueError("category_weights must not be empty")

    # Build lookup: check_id → CheckEvaluation
    eval_by_id: dict[str, CheckEvaluation] = {e.check_id: e for e in evaluations}

    weighted_sum = 0.0
    weight_denominator = 0.0
    checks_passed = 0
    checks_failed = 0
    checks_unclear = 0

    for check in checks:
        cat_name = check.category.value if hasattr(check.category, "value") else str(check.category)
        if cat_name not in category_weights:
            raise ValueError(
                f"Category '{cat_name}' not found in category_weights. "
                f"Available: {list(category_weights.keys())}"
            )
        cat_weight = category_weights[cat_name]
        effective_weight = check.weight * cat_weight
        weight_denominator += effective_weight

        evaluation = eval_by_id.get(check.id)
        if evaluation is None:
            # Missing evaluation treated as fail
            checks_failed += 1
            continue

        if evaluation.result == CheckEvaluationResult.PASS:
            weighted_sum += effective_weight
            checks_passed += 1
        elif evaluation.result == CheckEvaluationResult.FAIL:
            checks_failed += 1
        else:
            # UNCLEAR — treated as fail for scoring purposes
            checks_unclear += 1

    if weight_denominator <= 0.0:
        raise ValueError("Total weight denominator is zero; check weights must be positive")

    final_score = round((weighted_sum / weight_denominator) * 10.0, 6)
    # Clamp to [0, 10] to handle any floating-point overshoot
    final_score = max(0.0, min(10.0, final_score))

    calculation = GradeCalculation(
        total_checks=len(checks),
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        checks_unclear=checks_unclear,
        weighted_sum=weighted_sum,
        weight_denominator=weight_denominator,
        final_score=final_score,
    )
    return calculation, final_score
