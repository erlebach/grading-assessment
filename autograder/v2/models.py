"""v2 data models: concept-check rubrics and LLM-judge grading records."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class CheckType(str, Enum):
    DEFINITION = "definition"
    DISTINCTION = "distinction"
    MECHANISM = "mechanism"
    POSITIVE_EXAMPLE = "positive_example"
    NEGATIVE_EXAMPLE = "negative_example"
    GENERALIZATION = "generalization"


class PrecisionLevel(str, Enum):
    FULL = "full"      # score weight: 1.0
    PARTIAL = "partial"  # score weight: 0.5
    NONE = "none"      # score weight: 0.0

    def to_weight(self) -> float:
        return {"full": 1.0, "partial": 0.5, "none": 0.0}[self.value]


class EvaluationMode(str, Enum):
    SINGLE = "single"
    MULTI = "multi"


class ModelTier(str, Enum):
    OSS = "oss"
    FOUNDATIONAL = "foundational"
    MIXED = "mixed"


class ConceptCheck(BaseModel):
    """One typed concept check within a criterion."""

    check_id: str
    check_type: CheckType
    concept: str = Field(..., description="Vocabulary-agnostic concept description")
    points: float = Field(..., gt=0)
    precision_levels: dict[PrecisionLevel, str] = Field(
        ..., description="Descriptions for full / partial / none precision"
    )

    @field_validator("precision_levels")
    @classmethod
    def has_all_levels(cls, v: dict) -> dict:
        required = {PrecisionLevel.FULL, PrecisionLevel.PARTIAL, PrecisionLevel.NONE}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"precision_levels missing keys: {missing}")
        return v

    model_config = ConfigDict(title="ConceptCheck")


class CriterionV2(BaseModel):
    """A rubric criterion composed of typed concept checks."""

    criterion_id: str
    points: float = Field(..., gt=0)
    checks: list[ConceptCheck] = Field(..., min_length=1)

    def total_check_points(self) -> float:
        return sum(c.points for c in self.checks)

    @model_validator(mode="after")
    def points_match_checks(self) -> "CriterionV2":
        total = self.total_check_points()
        if abs(self.points - total) > 0.01:
            raise ValueError(
                f"CriterionV2.points ({self.points}) must equal sum of check points ({total})"
            )
        return self

    model_config = ConfigDict(title="CriterionV2")


class RubricV2(BaseModel):
    """v2 rubric for one question."""

    rubric_id: str
    question_id: str
    question_type: str  # matches QuestionType enum value
    version: int = Field(default=1, ge=1)
    criteria: list[CriterionV2] = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    iteration: int = Field(default=0, ge=0, description="Karpathy iteration that produced this rubric")

    model_config = ConfigDict(title="RubricV2")


class CheckEvalV2(BaseModel):
    """Judge evaluation of one concept check."""

    check_id: str
    precision: PrecisionLevel
    rationale: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> float:
        return self.precision.to_weight()

    model_config = ConfigDict(title="CheckEvalV2")


class GradeV2(BaseModel):
    """Final grade record for one student answer, v2."""

    grade_id: str
    question_id: str
    student_id: str
    rubric_id: str
    rubric_version: int
    check_evaluations: list[CheckEvalV2]
    raw_score: float = Field(..., ge=0.0, le=1.0, description="Weighted mean of check scores (0–1)")
    final_score: float = Field(..., ge=0.0, le=10.0, description="raw_score × 10, float, no truncation")
    answer_text: Optional[str] = None
    graded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_mode: EvaluationMode = Field(default=EvaluationMode.SINGLE)
    model_tier: ModelTier = Field(default=ModelTier.FOUNDATIONAL)

    model_config = ConfigDict(title="GradeV2")


class AnswerQuality(str, Enum):
    GOOD = "good"
    LESS_GOOD = "less_good"
    WRONG = "wrong"


class SyntheticAnswer(BaseModel):
    """One LLM-generated synthetic answer."""

    question_id: str
    quality: AnswerQuality
    variant: int = Field(..., ge=1, le=3)
    text: str

    model_config = ConfigDict(title="SyntheticAnswer")


class OrderingViolation(BaseModel):
    """A detected ordering violation in benchmark scores."""

    question_id: str
    criterion_id: str
    bad_pair: tuple[str, str]  # e.g. ("less_good", "wrong")
    bad_scores: tuple[float, float]
    description: str

    model_config = ConfigDict(title="OrderingViolation")
