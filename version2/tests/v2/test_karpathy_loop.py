# tests/v2/test_karpathy_loop.py
import json
from unittest.mock import MagicMock, call
import pytest
from v2.karpathy_loop import KarpathyLoop, KarpathyConfig, KarpathyResult
from v2.models import AnswerQuality, GradeV2, RubricV2, SyntheticAnswer, ConceptCheck, CriterionV2, CheckType, PrecisionLevel


def _simple_rubric(version: int = 1) -> RubricV2:
    check = ConceptCheck(
        check_id="c1", check_type=CheckType.DEFINITION, concept="x", points=1,
        precision_levels={PrecisionLevel.FULL: "f", PrecisionLevel.PARTIAL: "p", PrecisionLevel.NONE: "n"},
    )
    crit = CriterionV2(criterion_id="crit1", points=1, checks=[check])
    return RubricV2(
        rubric_id=f"q01_v{version}", question_id="q01", question_type="distinction",
        version=version, criteria=[crit],
    )


def _grade(student_id, q, score) -> GradeV2:
    return GradeV2(
        grade_id=f"{student_id}_{q}", question_id=q, student_id=student_id,
        rubric_id="r1", rubric_version=1, check_evaluations=[],
        raw_score=score / 10.0, final_score=score,
    )


def _answers():
    return [
        SyntheticAnswer(question_id="q01", quality=q, variant=v, text="text")
        for q in AnswerQuality for v in range(1, 4)
    ]


def test_loop_stops_when_no_violations():
    """Judge always gives correct ordering → loop converges on iteration 0."""
    mock_judge = MagicMock()
    mock_judge.evaluate.return_value = []

    mock_scorer = MagicMock()
    mock_scorer.side_effect = lambda **kw: _grade(kw["student_id"], "q01",
        8.0 if "good" in kw["student_id"] else 5.0 if "less_good" in kw["student_id"] else 2.0)

    mock_critic = MagicMock()
    mock_rubric_gen = MagicMock()

    loop = KarpathyLoop(
        judge=mock_judge,
        scorer=mock_scorer,
        critic=mock_critic,
        rubric_generator=mock_rubric_gen,
        config=KarpathyConfig(max_iterations=3, train_per_level=2, val_per_level=1),
    )
    result = loop.run(
        initial_rubric=_simple_rubric(),
        answers=_answers(),
        question_id="q01",
        question_text="Q",
        question_type="distinction",
        source_material="S",
    )
    assert result.converged
    assert result.iterations_used == 0
    assert mock_critic.propose_fix.call_count == 0


def test_loop_stops_at_max_iterations():
    """Judge always gives violations → loop stops at max_iterations."""
    mock_judge = MagicMock()
    mock_judge.evaluate.return_value = []

    mock_scorer = MagicMock()
    # Always wrong order: good=2, less_good=5, wrong=8
    mock_scorer.side_effect = lambda **kw: _grade(kw["student_id"], "q01",
        2.0 if "good" in kw["student_id"] else 5.0 if "less_good" in kw["student_id"] else 8.0)

    mock_critic = MagicMock()
    mock_critic.propose_fix.return_value = _simple_rubric(version=2)

    mock_rubric_gen = MagicMock()

    loop = KarpathyLoop(
        judge=mock_judge,
        scorer=mock_scorer,
        critic=mock_critic,
        rubric_generator=mock_rubric_gen,
        config=KarpathyConfig(max_iterations=2, train_per_level=2, val_per_level=1),
    )
    result = loop.run(
        initial_rubric=_simple_rubric(),
        answers=_answers(),
        question_id="q01",
        question_text="Q",
        question_type="distinction",
        source_material="S",
    )
    assert not result.converged
    assert result.iterations_used == 2
