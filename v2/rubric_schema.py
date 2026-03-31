"""Pydantic schemas for validating LLM-generated v2 rubric JSON.

parse_rubric_response() validates raw LLM dict and returns a canonical RubricV2.
MAX_CHECKS_PER_CRITERION enforces the complexity budget (REDESIGN §5).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from v2.models import (
    CheckType,
    ConceptCheck,
    CriterionV2,
    PrecisionLevel,
    RubricV2,
)

MAX_CHECKS_PER_CRITERION = 4  # complexity budget (REDESIGN §5)


class RawPrecisionLevels(BaseModel):
    """Raw precision level descriptions from LLM."""

    full: str
    partial: str
    none: str


class RawConceptCheck(BaseModel):
    """Raw concept check from LLM response."""

    check_id: str
    check_type: CheckType
    concept: str
    points: float = Field(..., gt=0)
    precision_levels: RawPrecisionLevels


class RawCriterion(BaseModel):
    """Raw criterion from LLM response."""

    criterion_id: str
    points: float = Field(..., gt=0)
    checks: list[RawConceptCheck] = Field(..., min_length=1, max_length=MAX_CHECKS_PER_CRITERION)

    @field_validator("checks")
    @classmethod
    def at_least_one(cls, v: list) -> list:
        if not v:
            raise ValueError("criterion must have at least one check")
        return v


class RubricV2Response(BaseModel):
    """Complete rubric JSON response as returned by the LLM."""

    criteria: list[RawCriterion] = Field(..., min_length=1, max_length=6)


def parse_rubric_response(
    raw: dict,
    question_id: str,
    question_type: str,
    version: int,
) -> RubricV2:
    """Validate raw LLM dict and return a canonical RubricV2.

    Raises ValidationError if the JSON does not match the schema.
    CriterionV2's own model_validator will raise if points ≠ sum of check points.
    """
    validated = RubricV2Response.model_validate(raw)
    criteria = []
    for rc in validated.criteria:
        checks = []
        for rck in rc.checks:
            pl = rck.precision_levels
            checks.append(
                ConceptCheck(
                    check_id=rck.check_id,
                    check_type=rck.check_type,
                    concept=rck.concept,
                    points=rck.points,
                    precision_levels={
                        PrecisionLevel.FULL: pl.full,
                        PrecisionLevel.PARTIAL: pl.partial,
                        PrecisionLevel.NONE: pl.none,
                    },
                )
            )
        criteria.append(
            CriterionV2(criterion_id=rc.criterion_id, points=rc.points, checks=checks)
        )
    return RubricV2(
        rubric_id=f"{question_id}_v{version}",
        question_id=question_id,
        question_type=question_type,
        version=version,
        criteria=criteria,
    )
