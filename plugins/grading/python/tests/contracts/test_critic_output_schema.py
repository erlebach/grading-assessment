import pytest

from plugins.grading.python.contracts import CriticOutput


def test_critic_output_accepts_weight_revision():
    raw = {
        "revisions": [
            {"kind": "weight", "axis": "causal", "new_weight": 0.4, "rationale": "..."},
        ],
        "rationale_summary": "...",
    }
    out = CriticOutput.model_validate(raw)
    assert out.revisions[0].kind == "weight"


def test_critic_output_accepts_criterion_revision():
    raw = {
        "revisions": [
            {"kind": "criterion", "axis": "causal", "level": "partial",
             "new_criterion": "...", "rationale": "..."},
        ],
        "rationale_summary": "...",
    }
    CriticOutput.model_validate(raw)


def test_critic_output_rejects_unknown_kind():
    raw = {"revisions": [{"kind": "purple", "rationale": "..."}], "rationale_summary": "x"}
    with pytest.raises(Exception):
        CriticOutput.model_validate(raw)
