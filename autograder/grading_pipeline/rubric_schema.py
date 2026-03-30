"""Pydantic schema for validating LLM-generated rubric JSON responses.

These schemas validate the raw JSON returned by the LLM before it is
converted into the canonical Check / Rubric models in models.py.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .models import CheckCategory


class RawCheck(BaseModel):
    """A single check as returned by the LLM inside a dimension."""

    text: str = Field(..., description="Binary, atomic check statement")
    weight: float = Field(..., gt=0, description="Relative weight for this check")


class RubricDimension(BaseModel):
    """A single dimension (criterion) in the LLM rubric response."""

    title: str = Field(..., description="Dimension title")
    category: CheckCategory = Field(..., description="One of: semantic, application, clarity")
    points: float = Field(..., gt=0, description="Points allocated to this dimension")
    checks: list[RawCheck] = Field(..., min_length=1, max_length=4, description="Atomic checks")

    @field_validator("checks")
    @classmethod
    def at_least_one_check(cls, v: list[RawCheck]) -> list[RawCheck]:
        if not v:
            raise ValueError("Each dimension must have at least one check")
        return v


class RubricJsonResponse(BaseModel):
    """Complete rubric JSON response from the LLM."""

    dimensions: list[RubricDimension] = Field(..., min_length=2, max_length=5)
    total_points: Literal[10] = Field(default=10)

    @field_validator("dimensions")
    @classmethod
    def points_sum_to_ten(cls, v: list[RubricDimension]) -> list[RubricDimension]:
        total = sum(d.points for d in v)
        if abs(total - 10) > 0.01:
            raise ValueError(f"Dimension points must sum to 10, got {total}")
        return v
