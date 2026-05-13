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
