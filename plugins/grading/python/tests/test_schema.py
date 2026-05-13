import pytest

from plugins.grading.python.schema import TypeName, TypeCatalog, TypeCatalogEntry


def test_type_name_has_ten_values():
    assert len(list(TypeName)) == 10


def test_type_name_expected_set():
    expected = {
        "DEFINITION",
        "DISTINCTION",
        "MECHANISM",
        "CLASSIFICATION",
        "ENUMERATION",
        "EXAMPLE_GENERATION",
        "ERROR_IDENTIFICATION",
        "COMPARISON",
        "APPLICATION",
        "PROOF_OR_ARGUMENT",
    }
    assert {t.value for t in TypeName} == expected


def test_type_catalog_round_trip():
    raw = {
        "types": [
            {
                "name": "MECHANISM",
                "description": "How a process unfolds.",
                "candidate_axes": ["causal_chain_correctness", "temporal_ordering"],
            }
        ]
    }
    catalog = TypeCatalog.model_validate(raw)
    assert catalog.types[0].name is TypeName.MECHANISM
    assert catalog.types[0].candidate_axes == ["causal_chain_correctness", "temporal_ordering"]


def test_type_catalog_rejects_unknown_type():
    raw = {"types": [{"name": "MADE_UP", "description": "x", "candidate_axes": ["a"]}]}
    with pytest.raises(Exception):
        TypeCatalog.model_validate(raw)


def test_type_catalog_rejects_empty_axes():
    raw = {"types": [{"name": "MECHANISM", "description": "x", "candidate_axes": []}]}
    with pytest.raises(Exception):
        TypeCatalog.model_validate(raw)


from plugins.grading.python.schema import (
    ScoreLevels,
    AxisDef,
    UniversalRubric,
    UniversalRubricStatus,
    Aggregate,
)


def _good_axis(name="a", weight=1.0):
    return {
        "name": name,
        "description": "x",
        "weight": weight,
        "score_levels": {
            "full":    {"value": 1.0, "criterion": "all"},
            "partial": {"value": 0.5, "criterion": "some"},
            "none":    {"value": 0.0, "criterion": "none"},
        },
    }


def test_universal_rubric_round_trip():
    raw = {
        "type": "MECHANISM",
        "status": "frozen",
        "axes": [_good_axis("causal", 0.6), _good_axis("temporal", 0.4)],
        "aggregate": {"method": "weighted_mean", "out_of": 10.0},
    }
    r = UniversalRubric.model_validate(raw)
    assert r.type is TypeName.MECHANISM
    assert len(r.axes) == 2


def test_universal_rubric_status_values():
    assert {s.value for s in UniversalRubricStatus} == {
        "frozen",
        "warning_test_marginal",
        "failed_to_converge",
    }


def test_score_level_value_constants():
    sl = ScoreLevels.model_validate({
        "full":    {"value": 1.0, "criterion": "x"},
        "partial": {"value": 0.5, "criterion": "x"},
        "none":    {"value": 0.0, "criterion": "x"},
    })
    assert sl.full.value == 1.0 and sl.partial.value == 0.5 and sl.none.value == 0.0
