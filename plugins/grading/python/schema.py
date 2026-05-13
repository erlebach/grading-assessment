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
