import pytest

from plugins.grading.python.schema import (
    validate_universal_rubric,
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
