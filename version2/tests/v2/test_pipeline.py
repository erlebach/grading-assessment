# tests/v2/test_pipeline.py
from unittest.mock import MagicMock
import pytest
from v2.pipeline import PipelineV2, PipelineConfig
from v2.models import AnswerQuality, GradeV2, RubricV2, SyntheticAnswer, ConceptCheck, CriterionV2, CheckType, PrecisionLevel
from v2.karpathy_loop import KarpathyResult


def _simple_rubric() -> RubricV2:
    check = ConceptCheck(
        check_id="c1", check_type=CheckType.DEFINITION, concept="x", points=1,
        precision_levels={PrecisionLevel.FULL: "f", PrecisionLevel.PARTIAL: "p", PrecisionLevel.NONE: "n"},
    )
    return RubricV2(
        rubric_id="q01_v1", question_id="q01", question_type="mechanism", version=1,
        criteria=[CriterionV2(criterion_id="crit1", points=1, checks=[check])],
    )


def _grade(student_id, score) -> GradeV2:
    return GradeV2(
        grade_id=f"{student_id}_q01", question_id="q01", student_id=student_id,
        rubric_id="q01_v1", rubric_version=1, check_evaluations=[],
        raw_score=score / 10.0, final_score=score,
    )


def test_pipeline_run_returns_grades_and_rubric():
    mock_answer_gen = MagicMock()
    mock_answer_gen.generate.return_value = [
        SyntheticAnswer(question_id="q01", quality=q, variant=v, text="t")
        for q in AnswerQuality for v in range(1, 4)
    ]

    mock_rubric_gen = MagicMock()
    mock_rubric_gen.generate.return_value = _simple_rubric()

    mock_karpathy = MagicMock()
    mock_karpathy.run.return_value = KarpathyResult(
        final_rubric=_simple_rubric(), converged=True, iterations_used=0
    )

    mock_judge = MagicMock()
    mock_judge.evaluate.return_value = []

    pipeline = PipelineV2(
        answer_generator=mock_answer_gen,
        rubric_generator=mock_rubric_gen,
        karpathy_loop=mock_karpathy,
        judge=mock_judge,
        config=PipelineConfig(evaluation_mode="single", model_tier="foundational"),
    )

    result = pipeline.run(
        question_id="q01",
        question_text="Why can't you compute ratios on Celsius?",
        question_type="mechanism",
        source_material="Celsius zero is arbitrary...",
        student_answers={"student_001": "My answer about zero."},
    )

    assert "rubric" in result
    assert "student_grades" in result
    assert "student_001" in result["student_grades"]


def test_pipeline_generates_answers_if_none_provided():
    mock_answer_gen = MagicMock()
    mock_answer_gen.generate.return_value = [
        SyntheticAnswer(question_id="q01", quality=q, variant=v, text="t")
        for q in AnswerQuality for v in range(1, 4)
    ]
    mock_rubric_gen = MagicMock()
    mock_rubric_gen.generate.return_value = _simple_rubric()

    mock_karpathy = MagicMock()
    mock_karpathy.run.return_value = KarpathyResult(
        final_rubric=_simple_rubric(), converged=True, iterations_used=0
    )

    mock_judge = MagicMock()
    mock_judge.evaluate.return_value = []

    pipeline = PipelineV2(
        answer_generator=mock_answer_gen,
        rubric_generator=mock_rubric_gen,
        karpathy_loop=mock_karpathy,
        judge=mock_judge,
        config=PipelineConfig(),
    )
    pipeline.run(
        question_id="q01",
        question_text="Q",
        question_type="mechanism",
        source_material="S",
        student_answers={"s1": "answer"},
    )
    mock_answer_gen.generate.assert_called_once()
