import pytest

from plugins.grading.python.schema import (
    validate_universal_rubric,
    validate_per_question_rubric,
    UniversalRubric,
)


def _axis(name, weight, full=1.0, partial=0.5, none=0.0):
    return {
        "name": name,
        "description": "x",
        "weight": weight,
        "score_levels": {
            "full":    {"value": full,    "criterion": "x"},
            "partial": {"value": partial, "criterion": "x"},
            "none":    {"value": none,    "criterion": "x"},
        },
    }


def _good_rubric():
    return {
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_axis("a", 0.5), _axis("b", 0.5)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    }


def test_validate_universal_rubric_accepts_good():
    validate_universal_rubric(_good_rubric())


def test_validate_universal_rubric_rejects_negative_weight():
    raw = _good_rubric()
    raw["axes"][0]["weight"] = -0.1
    with pytest.raises(ValueError, match="weight"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_weights_not_summing_to_one():
    raw = _good_rubric()
    raw["axes"][0]["weight"] = 0.4
    raw["axes"][1]["weight"] = 0.4
    with pytest.raises(ValueError, match="sum"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_non_monotone_levels():
    raw = _good_rubric()
    # partial > full violates monotonicity
    raw["axes"][0]["score_levels"]["partial"]["value"] = 0.99
    raw["axes"][0]["score_levels"]["full"]["value"] = 0.5
    with pytest.raises(ValueError, match="monoton"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_zero_out_of():
    raw = _good_rubric()
    raw["aggregate"]["out_of"] = 0.0
    with pytest.raises(ValueError, match="out_of"):
        validate_universal_rubric(raw)


def test_validate_universal_rubric_rejects_duplicate_axes():
    raw = _good_rubric()
    raw["axes"][1]["name"] = raw["axes"][0]["name"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_universal_rubric(raw)


def _universal_for_test():
    return UniversalRubric.model_validate({
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_axis("a", 0.6), _axis("b", 0.4)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    })


def _good_pqr():
    return {
        "question_id": "Q03",
        "course": "data_quality",
        "type": "MECHANISM",
        "universal_rubric_ref": "types/MECHANISM/universal_rubric.yaml",
        "concept_overlay": [
            {"id": "c1", "text": "...", "weight": 0.6, "relevant_axes": ["a"]},
            {"id": "c2", "text": "...", "weight": 0.4, "relevant_axes": ["a", "b"]},
        ],
        "status": "frozen",
    }


def test_validate_pqr_accepts_good():
    validate_per_question_rubric(_good_pqr(), universal=_universal_for_test())


def test_validate_pqr_rejects_weights_not_summing_to_one():
    raw = _good_pqr()
    raw["concept_overlay"][0]["weight"] = 0.3
    with pytest.raises(ValueError, match="sum"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_empty_relevant_axes():
    raw = _good_pqr()
    raw["concept_overlay"][0]["relevant_axes"] = []
    with pytest.raises(ValueError, match="relevant_axes"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_relevant_axes_outside_universal():
    raw = _good_pqr()
    raw["concept_overlay"][0]["relevant_axes"] = ["nonexistent_axis"]
    with pytest.raises(ValueError, match="relevant_axes"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_type_mismatch_with_universal():
    raw = _good_pqr()
    raw["type"] = "DEFINITION"
    with pytest.raises(ValueError, match="type"):
        validate_per_question_rubric(raw, universal=_universal_for_test())


def test_validate_pqr_rejects_duplicate_concept_ids():
    raw = _good_pqr()
    raw["concept_overlay"][1]["id"] = raw["concept_overlay"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_per_question_rubric(raw, universal=_universal_for_test())
