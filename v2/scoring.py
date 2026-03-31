"""Concept-presence scoring: presence x precision → float grade.

No int() truncation anywhere. All arithmetic in float.
compute_grade() is the public entry point.
"""

from __future__ import annotations

from v2.models import CheckEvalV2, GradeV2, RubricV2


def _check_points(rubric: RubricV2, check_id: str) -> float:
    """Return the point value for a check by ID."""
    for crit in rubric.criteria:
        for check in crit.checks:
            if check.check_id == check_id:
                return check.points
    raise KeyError(f"check_id {check_id!r} not found in rubric {rubric.rubric_id!r}")


def compute_grade(
    grade_id: str,
    question_id: str,
    student_id: str,
    rubric: RubricV2,
    check_evaluations: list[CheckEvalV2],
    evaluation_mode: str = "single",
    model_tier: str = "foundational",
) -> GradeV2:
    """Compute a weighted-mean grade from check evaluations.

    raw_score = sum(score_i * points_i) / sum(points_i)
    final_score = raw_score * 10   (float, no truncation)
    """
    total_weighted = 0.0
    total_points = 0.0
    for ev in check_evaluations:
        pts = _check_points(rubric, ev.check_id)
        total_weighted += ev.score * pts
        total_points += pts

    raw_score = total_weighted / total_points if total_points > 0 else 0.0
    final_score = raw_score * 10.0

    return GradeV2(
        grade_id=grade_id,
        question_id=question_id,
        student_id=student_id,
        rubric_id=rubric.rubric_id,
        rubric_version=rubric.version,
        check_evaluations=check_evaluations,
        raw_score=raw_score,
        final_score=final_score,
        evaluation_mode=evaluation_mode,
        model_tier=model_tier,
    )
