"""Pydantic models + invariant validators for every grading-plugin artifact.

Spec reference: docs/superpowers/specs/2026-05-13-grading-plugin-design.md §3.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


WEIGHT_EPSILON = 1e-6


class TypeName(str, Enum):
    DEFINITION = "DEFINITION"
    DISTINCTION = "DISTINCTION"
    MECHANISM = "MECHANISM"
    CLASSIFICATION = "CLASSIFICATION"
    ENUMERATION = "ENUMERATION"
    EXAMPLE_GENERATION = "EXAMPLE_GENERATION"
    ERROR_IDENTIFICATION = "ERROR_IDENTIFICATION"
    COMPARISON = "COMPARISON"
    APPLICATION = "APPLICATION"
    PROOF_OR_ARGUMENT = "PROOF_OR_ARGUMENT"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TypeCatalogEntry(_Strict):
    name: TypeName
    description: str = Field(min_length=1)
    candidate_axes: list[str] = Field(min_length=1)

    @field_validator("candidate_axes")
    @classmethod
    def axes_nonempty_strings(cls, v: list[str]) -> list[str]:
        if any((not isinstance(a, str)) or not a.strip() for a in v):
            raise ValueError("candidate_axes entries must be non-empty strings")
        if len(set(v)) != len(v):
            raise ValueError("candidate_axes must be unique within a type")
        return v


class TypeCatalog(_Strict):
    types: list[TypeCatalogEntry] = Field(min_length=1)

    @field_validator("types")
    @classmethod
    def names_unique(cls, v: list[TypeCatalogEntry]) -> list[TypeCatalogEntry]:
        names = [t.name for t in v]
        if len(set(names)) != len(names):
            raise ValueError("type names must be unique")
        return v


class ScoreLevelEntry(_Strict):
    value: float
    criterion: str = Field(min_length=1)


class ScoreLevels(_Strict):
    full: ScoreLevelEntry
    partial: ScoreLevelEntry
    none: ScoreLevelEntry


class AxisDef(_Strict):
    name: str = Field(min_length=1)
    description: str = ""
    weight: float = Field(ge=0.0)
    score_levels: ScoreLevels


class Aggregate(_Strict):
    method: str = Field(min_length=1)
    out_of: float = Field(gt=0.0)


class UniversalRubricStatus(str, Enum):
    FROZEN = "frozen"
    WARNING_TEST_MARGINAL = "warning_test_marginal"
    FAILED_TO_CONVERGE = "failed_to_converge"


class UniversalRubric(_Strict):
    type: TypeName
    status: UniversalRubricStatus
    axes: list[AxisDef] = Field(min_length=1)
    aggregate: Aggregate


def validate_universal_rubric(raw: dict) -> UniversalRubric:
    """Apply §3.6 first bullet's invariants.

    Returns the validated model. Raises ValueError with a useful message on
    any invariant violation.
    """
    rubric = UniversalRubric.model_validate(raw)

    names = [a.name for a in rubric.axes]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate axis names: {names}")

    total = sum(a.weight for a in rubric.axes)
    if abs(total - 1.0) > WEIGHT_EPSILON:
        raise ValueError(f"axis weights must sum to 1.0; got {total}")

    for axis in rubric.axes:
        sl = axis.score_levels
        if not (sl.full.value > sl.partial.value > sl.none.value):
            raise ValueError(
                f"axis {axis.name!r}: score_levels not monotone "
                f"(full={sl.full.value}, partial={sl.partial.value}, none={sl.none.value})"
            )

    return rubric
