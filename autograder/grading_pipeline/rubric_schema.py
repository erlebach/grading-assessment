"""Pydantic schema for validating LLM-generated rubric JSON responses.

"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RubricDimension(BaseModel):
    """A single dimension (criterion) in the rubric.

    """

    title: str = Field(..., description="Dimension title")
    points: int = Field(..., ge=1, le=10, description="Points for this dimension")
    description: str = Field(..., description="Full-credit description")


class RubricJsonResponse(BaseModel):
    """Complete rubric JSON response from LLM.

    """

    dimensions: list[RubricDimension] = Field(..., min_length=2, max_length=5)
    total_points: Literal[10] = Field(default=10)

    @field_validator("dimensions")
    @classmethod
    def validate_total_points(cls, v: list[RubricDimension]) -> list[RubricDimension]:
        """Validate that dimension points sum to total_points.

        Args:
            v: List of rubric dimensions.

        Returns:
            Validated list of dimensions.

        Raises:
            ValueError: If points don't sum to 10.

        """
        total = sum(d.points for d in v)
        if total != 10:
            raise ValueError(f"Total points must equal 10, got {total}")
        return v
