from pathlib import Path

import yaml

CATALOG = Path(__file__).resolve().parents[2] / "config" / "role_catalog.yaml"

EXPECTED_ROLES = {
    "pdf_translator",
    "seed_gen",
    "seed_validator",
    "materialize_seed",
    "axis_criterion_drafter",
    "judge",
    "critic",
    "overlay_critic",
    "question_workup",
    "gold_annotator",
}


def test_catalog_exists():
    assert CATALOG.is_file()


def test_catalog_has_all_expected_roles():
    data = yaml.safe_load(CATALOG.read_text())
    declared = {r["name"] for r in data["roles"]}
    assert declared == EXPECTED_ROLES, declared.symmetric_difference(EXPECTED_ROLES)


def test_every_role_has_description():
    data = yaml.safe_load(CATALOG.read_text())
    for role in data["roles"]:
        assert role.get("description"), role["name"]
