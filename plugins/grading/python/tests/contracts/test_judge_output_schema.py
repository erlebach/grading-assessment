import pytest

from plugins.grading.python.contracts import JudgeOutput, JudgeRow


def test_judge_output_accepts_well_formed():
    raw = {
        "rows": [
            {
                "answer_id": "good_1", "concept_id": "c1", "axis": "causal",
                "level": "full", "rationale": "explicit causes.",
            },
        ]
    }
    out = JudgeOutput.model_validate(raw)
    assert out.rows[0].level == "full"


def test_judge_output_rejects_bad_level():
    raw = {"rows": [
        {"answer_id": "a", "concept_id": "c", "axis": "x",
         "level": "MAYBE", "rationale": "..."}
    ]}
    with pytest.raises(Exception):
        JudgeOutput.model_validate(raw)


def test_judge_output_rejects_missing_rationale():
    raw = {"rows": [
        {"answer_id": "a", "concept_id": "c", "axis": "x", "level": "full"}
    ]}
    with pytest.raises(Exception):
        JudgeOutput.model_validate(raw)
