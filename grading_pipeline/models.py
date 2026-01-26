"""
Pydantic data models for the weighted checklist grading system.

Defines all core data structures with validation:
- Check: Individual checklist item
- Rubric: Collection of checks for a question
- CheckEvaluation: Result of evaluating a single check
- GradeResult: Final grade with calculation details
- Appeal: Grade appeal with version tracking
"""

from datetime import datetime
from typing import Optional, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator


class CheckCategory(str, Enum):
    """Category for a check (semantic, application, clarity)."""

    SEMANTIC = "semantic"
    APPLICATION = "application"
    CLARITY = "clarity"


class Check(BaseModel):
    """
    A single check in a rubric.

    Checks are atomic evaluation items that are either passed or failed.
    Each check belongs to exactly one category.
    """

    id: str = Field(
        ...,
        description="Unique identifier for the check (e.g., 'q01_check_1')"
    )
    text: str = Field(
        ...,
        description="The check description (what must be true for pass)"
    )
    category: CheckCategory = Field(
        ...,
        description="Category of this check"
    )
    weight: float = Field(
        default=1.0,
        gt=0,
        description="Base weight for this check (independent of category weight)"
    )
    rubric_id: Optional[str] = Field(
        default=None,
        description="ID of the rubric this check belongs to"
    )
    dimension_id: Optional[str] = Field(
        default=None,
        description="ID of the dimension (criterion) this check came from"
    )
    question_id: str = Field(
        ...,
        description="Question ID this check is for"
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Source text from original rubric dimension (for audit trail)"
    )

    class Config:
        title = "Check"
        json_schema_extra = {
            "example": {
                "id": "q01_check_1",
                "text": "Student defines 'object' correctly",
                "category": "semantic",
                "weight": 1.0,
                "question_id": "q01",
                "evidence": "Student must demonstrate understanding of 'object' as a collection of attributes"
            }
        }


class Rubric(BaseModel):
    """
    A grading rubric for a single question.

    Contains the original dimensions/criteria and extracted checks.
    """

    id: str = Field(
        ...,
        description="Unique rubric ID (e.g., 'q01_rubric')"
    )
    question_id: str = Field(
        ...,
        description="The question ID this rubric is for"
    )
    title: str = Field(
        ...,
        description="Human-readable rubric title"
    )
    description: str = Field(
        ...,
        description="Rubric description/context"
    )
    checks: list[Check] = Field(
        default_factory=list,
        description="Extracted checks from dimensions"
    )
    dimensions: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Original rubric dimensions (for audit trail)"
    )
    total_points: float = Field(
        default=10.0,
        gt=0,
        description="Total points for this rubric"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this rubric was created"
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Rubric version number"
    )

    class Config:
        title = "Rubric"
        json_encoders = {datetime: lambda v: v.isoformat()}


class CheckEvaluationResult(str, Enum):
    """Result of evaluating a single check."""

    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"


class CheckEvaluation(BaseModel):
    """
    Result of evaluating a single check against a student answer.
    """

    check_id: str = Field(
        ...,
        description="ID of the check being evaluated"
    )
    result: CheckEvaluationResult = Field(
        ...,
        description="Whether the check passed, failed, or was unclear"
    )
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Binary score: 1.0 for pass, 0.0 for fail"
    )
    evidence: str = Field(
        ...,
        description="Explanation of why the check passed or failed"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this evaluation (0-1)"
    )
    grader: str = Field(
        default="llm",
        description="Who performed the evaluation (e.g., 'llm', 'human')"
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this check was evaluated"
    )

    class Config:
        title = "Check Evaluation"
        json_encoders = {datetime: lambda v: v.isoformat()}

    @validator("score")
    def score_matches_result(cls, v, values):
        """Ensure score matches result."""
        if "result" in values:
            result = values["result"]
            if result == CheckEvaluationResult.PASS and v != 1.0:
                raise ValueError("Pass result must have score=1.0")
            elif result == CheckEvaluationResult.FAIL and v != 0.0:
                raise ValueError("Fail result must have score=0.0")
        return v


class GradeCalculation(BaseModel):
    """Details of how the final grade was calculated."""

    total_checks: int = Field(
        ...,
        ge=0,
        description="Total number of checks evaluated"
    )
    checks_passed: int = Field(
        ...,
        ge=0,
        description="Number of checks that passed"
    )
    checks_failed: int = Field(
        ...,
        ge=0,
        description="Number of checks that failed"
    )
    checks_unclear: int = Field(
        ...,
        ge=0,
        description="Number of checks with unclear results"
    )
    weighted_sum: float = Field(
        ...,
        ge=0.0,
        description="Sum of (pass_i × weight_i × category_weight_i)"
    )
    weight_denominator: float = Field(
        ...,
        gt=0.0,
        description="Sum of (weight_i × category_weight_i) for normalization"
    )
    final_score: float = Field(
        ...,
        ge=0.0,
        description="Final score on 0-10 scale"
    )

    class Config:
        title = "Grade Calculation"


class GradeResult(BaseModel):
    """
    Final grade for a student answer to a question.

    Includes all calculation details for reproducibility and audit trail.
    """

    id: str = Field(
        ...,
        description="Unique grade result ID (e.g., 'student_001_q01_v1')"
    )
    question_id: str = Field(
        ...,
        description="Question ID"
    )
    student_id: str = Field(
        ...,
        description="Student ID"
    )
    rubric_id: str = Field(
        ...,
        description="Rubric ID used for grading"
    )
    rubric_version: int = Field(
        ...,
        ge=1,
        description="Version of the rubric used"
    )
    answer_text: Optional[str] = Field(
        default=None,
        description="The student's answer (for audit trail)"
    )
    check_evaluations: list[CheckEvaluation] = Field(
        ...,
        description="Evaluation results for all checks"
    )
    calculation: GradeCalculation = Field(
        ...,
        description="Calculation details"
    )
    final_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Final grade (0-10)"
    )
    grader: str = Field(
        default="llm",
        description="Grader identifier"
    )
    graded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the grade was assigned"
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Grade version (for appeal tracking)"
    )

    class Config:
        title = "Grade Result"
        json_encoders = {datetime: lambda v: v.isoformat()}

    def is_appeal(self) -> bool:
        """Check if this is an appeal grade (version > 1)."""
        return self.version > 1


class Appeal(BaseModel):
    """
    Grade appeal record with version history.

    Tracks appeals and maintains complete history of grade changes.
    """

    id: str = Field(
        ...,
        description="Unique appeal ID (e.g., 'appeal_student_001_q01_v1')"
    )
    original_grade_id: str = Field(
        ...,
        description="ID of the original grade being appealed"
    )
    student_id: str = Field(
        ...,
        description="Student ID"
    )
    question_id: str = Field(
        ...,
        description="Question ID"
    )
    original_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Original grade"
    )
    new_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="New grade after appeal"
    )
    reason: str = Field(
        ...,
        description="Reason for the appeal"
    )
    decision: Literal["approved", "denied", "pending"] = Field(
        default="pending",
        description="Decision on the appeal"
    )
    instructor_notes: Optional[str] = Field(
        default=None,
        description="Instructor comments on appeal decision"
    )
    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the appeal was requested"
    )
    decided_at: Optional[datetime] = Field(
        default=None,
        description="When the appeal decision was made"
    )

    class Config:
        title = "Appeal"
        json_encoders = {datetime: lambda v: v.isoformat()}

    @validator("new_score")
    def new_score_higher(cls, v, values):
        """Ensure appeals only increase scores."""
        if "original_score" in values and v < values["original_score"]:
            raise ValueError("Appeal cannot decrease score (only upward adjustments allowed)")
        return v

    def is_approved(self) -> bool:
        """Check if appeal was approved."""
        return self.decision == "approved"


if __name__ == "__main__":
    # Example usage and validation
    from datetime import datetime

    # Create a sample check
    check = Check(
        id="q01_check_1",
        text="Student defines 'object' correctly",
        category=CheckCategory.SEMANTIC,
        weight=1.0,
        question_id="q01"
    )
    print("✓ Check created:", check.id)

    # Create a sample check evaluation
    evaluation = CheckEvaluation(
        check_id="q01_check_1",
        result=CheckEvaluationResult.PASS,
        score=1.0,
        evidence="Student provided correct definition: 'An object is a collection of attributes.'"
    )
    print("✓ Check evaluation created:", evaluation.result)

    # Create a sample grade calculation
    calculation = GradeCalculation(
        total_checks=5,
        checks_passed=4,
        checks_failed=1,
        checks_unclear=0,
        weighted_sum=7.0,
        weight_denominator=8.0,
        final_score=8.75
    )
    print("✓ Grade calculation created with score:", calculation.final_score)

    # Create a sample grade result
    grade = GradeResult(
        id="student_001_q01_v1",
        question_id="q01",
        student_id="student_001",
        rubric_id="q01_rubric",
        rubric_version=1,
        check_evaluations=[evaluation],
        calculation=calculation,
        final_score=8.75
    )
    print("✓ Grade result created:", grade.id)

    # Create a sample appeal
    appeal = Appeal(
        id="appeal_student_001_q01_v1",
        original_grade_id="student_001_q01_v1",
        student_id="student_001",
        question_id="q01",
        original_score=8.75,
        new_score=9.0,
        reason="Disagreement with evaluation of definition clarity"
    )
    print("✓ Appeal created:", appeal.id)
