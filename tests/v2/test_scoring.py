# tests/v2/test_scoring.py
import pytest
from v2.scoring import compute_grade
from v2.models import (
    CheckEvalV2, CheckType, ConceptCheck, CriterionV2,
    GradeV2, PrecisionLevel, RubricV2,
)


def _make_rubric_and_evals(precision_for_c1: PrecisionLevel, precision_for_c2: PrecisionLevel):
    c1 = ConceptCheck(
        check_id="c1", check_type=CheckType.DEFINITION,
        concept="x", points=1,
        precision_levels={PrecisionLevel.FULL: "f", PrecisionLevel.PARTIAL: "p", PrecisionLevel.NONE: "n"},
    )
    c2 = ConceptCheck(
        check_id="c2", check_type=CheckType.MECHANISM,
        concept="y", points=2,
        precision_levels={PrecisionLevel.FULL: "f", PrecisionLevel.PARTIAL: "p", PrecisionLevel.NONE: "n"},
    )
    crit = CriterionV2(criterion_id="crit1", points=3, checks=[c1, c2])
    rubric = RubricV2(rubric_id="r1", question_id="q01", question_type="mechanism", version=1, criteria=[crit])
    evals = [
        CheckEvalV2(check_id="c1", precision=precision_for_c1, score=precision_for_c1.to_weight(), rationale="r"),
        CheckEvalV2(check_id="c2", precision=precision_for_c2, score=precision_for_c2.to_weight(), rationale="r"),
    ]
    return rubric, evals


def test_full_full_gives_ten():
    rubric, evals = _make_rubric_and_evals(PrecisionLevel.FULL, PrecisionLevel.FULL)
    grade = compute_grade(
        grade_id="g1", question_id="q01", student_id="s1",
        rubric=rubric, check_evaluations=evals,
    )
    assert grade.final_score == pytest.approx(10.0)
    assert isinstance(grade.final_score, float)


def test_none_none_gives_zero():
    rubric, evals = _make_rubric_and_evals(PrecisionLevel.NONE, PrecisionLevel.NONE)
    grade = compute_grade(
        grade_id="g1", question_id="q01", student_id="s1",
        rubric=rubric, check_evaluations=evals,
    )
    assert grade.final_score == pytest.approx(0.0)


def test_mixed_precision_is_float_no_truncation():
    # c1(points=1, partial=0.5) + c2(points=2, full=1.0) → weighted mean
    # = (0.5*1 + 1.0*2) / (1+2) = 2.5/3 ≈ 0.8333
    rubric, evals = _make_rubric_and_evals(PrecisionLevel.PARTIAL, PrecisionLevel.FULL)
    grade = compute_grade(
        grade_id="g1", question_id="q01", student_id="s1",
        rubric=rubric, check_evaluations=evals,
    )
    assert grade.final_score == pytest.approx(8.333, abs=0.01)
    assert isinstance(grade.final_score, float)
    assert grade.final_score != int(grade.final_score)


def test_returns_grade_v2():
    rubric, evals = _make_rubric_and_evals(PrecisionLevel.FULL, PrecisionLevel.FULL)
    grade = compute_grade(
        grade_id="g1", question_id="q01", student_id="s1",
        rubric=rubric, check_evaluations=evals,
    )
    assert isinstance(grade, GradeV2)
