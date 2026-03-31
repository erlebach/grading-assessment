# tests/v2/test_judge.py
import json
from unittest.mock import MagicMock
import pytest
from v2.judge import ConceptJudge, EvaluationMode
from v2.models import (
    CheckEvalV2, CheckType, ConceptCheck, CriterionV2,
    PrecisionLevel, RubricV2,
)


def _make_rubric() -> RubricV2:
    check = ConceptCheck(
        check_id="c1",
        check_type=CheckType.DEFINITION,
        concept="interval scale zero is arbitrary",
        points=1,
        precision_levels={
            PrecisionLevel.FULL: "Names convention, states not absence of heat",
            PrecisionLevel.PARTIAL: "States arbitrary without specifics",
            PrecisionLevel.NONE: "Absent or wrong",
        },
    )
    crit = CriterionV2(criterion_id="zero_role", points=1, checks=[check])
    return RubricV2(
        rubric_id="q01_v1",
        question_id="q01",
        question_type="mechanism",
        version=1,
        criteria=[crit],
    )


def _llm_returning(payload: dict):
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text=json.dumps(payload))
    return llm


SINGLE_RESPONSE = {
    "evaluations": [
        {"check_id": "c1", "precision": "full", "rationale": "Student names freezing point."}
    ]
}

MULTI_RESPONSE = {
    "check_id": "c1",
    "precision": "partial",
    "rationale": "Mentions arbitrary but no specifics.",
}


def test_single_mode_returns_one_eval_per_check():
    llm = _llm_returning(SINGLE_RESPONSE)
    judge = ConceptJudge(llm=llm, mode=EvaluationMode.SINGLE)
    evals = judge.evaluate(
        answer_text="Celsius zero is arbitrary...",
        rubric=_make_rubric(),
        evidence_context="",
    )
    assert len(evals) == 1
    assert evals[0].check_id == "c1"
    assert evals[0].precision == PrecisionLevel.FULL


def test_multi_mode_calls_llm_once_per_check():
    rubric = _make_rubric()
    check2 = ConceptCheck(
        check_id="c2",
        check_type=CheckType.MECHANISM,
        concept="arbitrary zero makes ratios meaningless",
        points=1,
        precision_levels={
            PrecisionLevel.FULL: "Causal chain",
            PrecisionLevel.PARTIAL: "Mentions ratio fails",
            PrecisionLevel.NONE: "Absent",
        },
    )
    rubric.criteria[0].checks.append(check2)
    llm = MagicMock()
    llm.complete.side_effect = [
        MagicMock(text=json.dumps({"check_id": "c1", "precision": "full", "rationale": "ok"})),
        MagicMock(text=json.dumps({"check_id": "c2", "precision": "partial", "rationale": "partial"})),
    ]
    judge = ConceptJudge(llm=llm, mode=EvaluationMode.MULTI)
    evals = judge.evaluate(
        answer_text="answer",
        rubric=rubric,
        evidence_context="",
    )
    assert llm.complete.call_count == 2
    assert len(evals) == 2


def test_precision_maps_to_correct_score():
    llm = _llm_returning(SINGLE_RESPONSE)
    judge = ConceptJudge(llm=llm, mode=EvaluationMode.SINGLE)
    evals = judge.evaluate("answer", _make_rubric(), "")
    assert evals[0].score == 1.0   # full → 1.0
