import pytest

from plugins.grading.python.contracts import MaterializeSeedOutput


def _good():
    return {
        "seed_id": "MECHANISM_001",
        "concept_overlay": [
            {"id": "c1", "text": "...", "weight": 0.6, "relevant_axes": ["a"]},
            {"id": "c2", "text": "...", "weight": 0.4, "relevant_axes": ["a"]},
        ],
        "answers": [
            {"answer_id": "good_1", "quality": "good", "text": "..."},
            {"answer_id": "ap_a", "quality": "axis_perturbation",
             "text": "...", "target_axis": "a"},
        ],
        "gold_coverage": {
            "good_1": {"c1": {"a": "full"}, "c2": {"a": "full"}},
            "ap_a":   {"c1": {"a": "partial"}, "c2": {"a": "partial"}},
        },
    }


def test_materialize_seed_accepts_good():
    MaterializeSeedOutput.model_validate(_good())


def test_materialize_seed_rejects_axis_perturbation_without_target():
    raw = _good()
    raw["answers"][1]["target_axis"] = None
    with pytest.raises(Exception):
        MaterializeSeedOutput.model_validate(raw)
