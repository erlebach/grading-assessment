"""T2.3 — Category assignment and validation for extracted checks.

Since T2.1 (rubric_generator_template.txt) already instructs the LLM to embed
categories directly in the JSON output, this module's job is *validation* and
*override*, not a separate LLM call.

Responsibilities
----------------
1. Load canonical categories from ``config/grading_categories.yaml``.
2. Validate each Check's category against the canonical list.
3. Provide a configurable fallback strategy for invalid categories:
   - ``"error"``   — raise ValueError (strict mode)
   - ``"default"`` — reassign to the configured default category (default mode)
   - ``"fuzzy"``   — attempt case-insensitive / partial match, then fall back
4. Return the mutated Rubric (checks updated in-place on copies).

Public API
----------
validate_categories(rubric, config_path=None, on_invalid="default") -> Rubric
load_category_config(path=None) -> CategoryConfig
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .models import Check, CheckCategory, Rubric


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------

class CategoryDefinition(BaseModel):
    name: str
    weight: float
    description: str = ""


class CategoryConfig(BaseModel):
    categories: list[CategoryDefinition]
    default_category: str = Field(default="semantic")

    def valid_names(self) -> frozenset[str]:
        return frozenset(c.name for c in self.categories)

    def weight_for(self, name: str) -> float:
        for c in self.categories:
            if c.name == name:
                return c.weight
        raise KeyError(f"Unknown category: {name!r}")


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = (
    Path(__file__).parent.parent / "config" / "grading_categories.yaml"
)


def load_category_config(path: str | Path | None = None) -> CategoryConfig:
    """Load and return the category configuration.

    Args:
        path: Path to ``grading_categories.yaml``. Uses the project default
              if not specified.

    Returns:
        Parsed CategoryConfig.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the YAML is malformed or missing ``categories`` key.
    """
    resolved = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not resolved.exists():
        raise FileNotFoundError(f"Category config not found: {resolved}")

    with resolved.open() as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict) or "categories" not in raw:
        raise ValueError(f"Invalid category config at {resolved}: missing 'categories' key")

    cats = [
        CategoryDefinition(
            name=c["name"],
            weight=float(c.get("weight", 1.0)),
            description=c.get("description", ""),
        )
        for c in raw["categories"]
    ]
    return CategoryConfig(categories=cats)


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

OnInvalid = Literal["error", "default", "fuzzy"]


def _fuzzy_match(value: str, valid: frozenset[str]) -> str | None:
    """Return the first case-insensitive match, or None."""
    lower = value.lower().strip()
    for name in valid:
        if lower == name or lower.startswith(name) or name.startswith(lower):
            return name
    return None


def _resolve_category(
    check: Check,
    valid: frozenset[str],
    default_cat: str,
    on_invalid: OnInvalid,
) -> CheckCategory:
    """Return the resolved CheckCategory for a check, applying the fallback strategy."""
    current = check.category.value

    if current in valid:
        return check.category  # already valid — no change

    if on_invalid == "error":
        raise ValueError(
            f"Check {check.id!r} has invalid category {current!r}. "
            f"Valid categories: {sorted(valid)}"
        )

    if on_invalid == "fuzzy":
        matched = _fuzzy_match(current, valid)
        if matched:
            return CheckCategory(matched)
        # fall through to default

    # "default" (or fuzzy with no match)
    return CheckCategory(default_cat)


def validate_categories(
    rubric: Rubric,
    config_path: str | Path | None = None,
    on_invalid: OnInvalid = "default",
) -> Rubric:
    """Validate and optionally reassign categories on all checks in a Rubric.

    Returns a *new* Rubric with corrected checks (does not mutate the input).

    Args:
        rubric:      The Rubric to validate.
        config_path: Path to ``grading_categories.yaml`` (uses project default
                     if not provided).
        on_invalid:  Strategy when an invalid category is encountered:
                     ``"error"`` — raise ValueError;
                     ``"default"`` — reassign to ``CategoryConfig.default_category``;
                     ``"fuzzy"`` — try case-insensitive match first, then default.

    Returns:
        A new Rubric with all check categories validated/corrected.

    Raises:
        ValueError: If ``on_invalid="error"`` and any check has an invalid category.
        FileNotFoundError: If the config file cannot be found.
    """
    config = load_category_config(config_path)
    valid = config.valid_names()
    default_cat = config.default_category

    updated_checks: list[Check] = []
    for check in rubric.checks:
        resolved = _resolve_category(check, valid, default_cat, on_invalid)
        if resolved != check.category:
            # Build a corrected copy
            updated = check.model_copy(update={"category": resolved})
            updated_checks.append(updated)
        else:
            updated_checks.append(check)

    return rubric.model_copy(update={"checks": updated_checks})
