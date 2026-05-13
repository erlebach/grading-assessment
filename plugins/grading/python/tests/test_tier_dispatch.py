from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
TIER_DISPATCH = CONFIG_DIR / "tier_dispatch.yaml"
ROLE_CATALOG = CONFIG_DIR / "role_catalog.yaml"

SUPPORTED_TIERS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
}


def _roles_in_catalog() -> set[str]:
    data = yaml.safe_load(ROLE_CATALOG.read_text())
    return {r["name"] for r in data["roles"]}


def test_default_tier_supported():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    assert data["default_tier"] in SUPPORTED_TIERS


def test_every_role_in_catalog_is_mapped():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    mapped = set(data["roles"].keys())
    catalog = _roles_in_catalog()
    missing = catalog - mapped
    assert not missing, f"unmapped roles: {missing}"


def test_every_mapped_role_exists_in_catalog():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    mapped = set(data["roles"].keys())
    catalog = _roles_in_catalog()
    orphans = mapped - catalog
    assert not orphans, f"orphan role mappings: {orphans}"


def test_every_mapped_tier_supported():
    data = yaml.safe_load(TIER_DISPATCH.read_text())
    for role, tier in data["roles"].items():
        assert tier in SUPPORTED_TIERS, f"role {role!r} -> unsupported tier {tier!r}"
