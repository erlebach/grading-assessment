# tests/v2/test_models.py
import pytest
from pydantic import ValidationError

# Import from v2 module
from v2.models import (
    ConceptCheck, CheckType, PrecisionLevel,
    CriterionV2, RubricV2,
    CheckEvalV2, GradeV2,
    AnswerQuality, SyntheticAnswer,
    OrderingViolation,
)


def test_concept_check_valid():
    c = ConceptCheck(
        check_id="c1",
        check_type=CheckType.DEFINITION,
        concept="zero point on interval scale is arbitrary",
        points=1,
        precision_levels={
            PrecisionLevel.FULL: "Names freezing point convention and states not absence of heat",
            PrecisionLevel.PARTIAL: "States zero is arbitrary without specifics",
            PrecisionLevel.NONE: "Absent or states zero has physical meaning",
        },
    )
    assert c.points == 1
    assert PrecisionLevel.FULL in c.precision_levels


def test_concept_check_rejects_missing_precision_levels():
    with pytest.raises(ValidationError):
        ConceptCheck(
            check_id="c1",
            check_type=CheckType.DEFINITION,
            concept="x",
            points=1,
            precision_levels={},  # must have all three levels
        )


def test_criterion_v2_valid():
    check = ConceptCheck(
        check_id="c1",
        check_type=CheckType.MECHANISM,
        concept="arbitrary zero makes ratio meaningless",
        points=1,
        precision_levels={
            PrecisionLevel.FULL: "Causal chain explained",
            PrecisionLevel.PARTIAL: "Mentions ratio fails without causal chain",
            PrecisionLevel.NONE: "Absent",
        },
    )
    crit = CriterionV2(
        criterion_id="role_of_zero",
        points=1,
        checks=[check],
    )
    assert crit.total_check_points() == 1


def test_rubric_v2_valid():
    check = ConceptCheck(
        check_id="c1",
        check_type=CheckType.DEFINITION,
        concept="zero is arbitrary",
        points=1,
        precision_levels={
            PrecisionLevel.FULL: "full",
            PrecisionLevel.PARTIAL: "partial",
            PrecisionLevel.NONE: "none",
        },
    )
    crit = CriterionV2(criterion_id="crit1", points=1, checks=[check])
    rubric = RubricV2(
        rubric_id="q01_v1",
        question_id="q01",
        question_type="distinction",
        version=1,
        criteria=[crit],
    )
    assert rubric.rubric_id == "q01_v1"
    assert rubric.version == 1


def test_check_eval_v2_valid():
    ev = CheckEvalV2(
        check_id="c1",
        precision=PrecisionLevel.FULL,
        rationale="Answer states freezing point convention explicitly.",
    )
    assert ev.score == 1.0


def test_precision_to_weight():
    assert PrecisionLevel.FULL.to_weight() == 1.0
    assert PrecisionLevel.PARTIAL.to_weight() == 0.5
    assert PrecisionLevel.NONE.to_weight() == 0.0


def test_grade_v2_float_no_truncation():
    ev = CheckEvalV2(
        check_id="c1",
        precision=PrecisionLevel.PARTIAL,
        rationale="partial",
    )
    grade = GradeV2(
        grade_id="g1",
        question_id="q01",
        student_id="s1",
        rubric_id="q01_v1",
        rubric_version=1,
        check_evaluations=[ev],
        raw_score=0.5,
        final_score=5.0,
    )
    assert isinstance(grade.final_score, float)
    assert grade.final_score == 5.0


def test_synthetic_answer():
    ans = SyntheticAnswer(
        question_id="q01",
        quality=AnswerQuality.GOOD,
        variant=1,
        text="20°C/10°C does not equal twice as warm because...",
    )
    assert ans.quality == AnswerQuality.GOOD


def test_ordering_violation():
    v = OrderingViolation(
        question_id="q01",
        criterion_id="crit1",
        bad_pair=("less_good", "wrong"),
        bad_scores=(2.0, 3.0),
        description="less_good < wrong",
    )
    assert v.bad_pair == ("less_good", "wrong")
