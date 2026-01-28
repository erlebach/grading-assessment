"""
Pydantic schemas for grading configuration validation.

Validates:
- Category definitions (weights, descriptions)
- Grading parameters (min/max scores, calculation method)
- Storage and logging configuration
- Appeals configuration
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, validator
import yaml


class CategoryDefinition(BaseModel):
    """Schema for a single category."""

    name: str = Field(..., description="Category name (e.g., 'semantic', 'application')")
    weight: float = Field(
        ...,
        gt=0,
        description="Weight for this category. Must be positive. Only ratios matter."
    )
    description: str = Field(..., description="Human-readable description of category")

    class Config:
        title = "Category Definition"


class CategoriesConfig(BaseModel):
    """Schema for categories configuration."""

    categories: list[CategoryDefinition] = Field(
        ...,
        min_items=1,
        description="List of grading categories"
    )

    class Config:
        title = "Categories Configuration"

    @validator("categories")
    def check_unique_names(cls, v):
        """Ensure category names are unique."""
        names = [cat.name for cat in v]
        if len(names) != len(set(names)):
            raise ValueError("Category names must be unique")
        return v

    def get_category_weight(self, category_name: str) -> float:
        """Get weight for a specific category."""
        for cat in self.categories:
            if cat.name == category_name:
                return cat.weight
        raise ValueError(f"Category '{category_name}' not found")

    def get_category_by_name(self, name: str) -> Optional[CategoryDefinition]:
        """Get category definition by name."""
        for cat in self.categories:
            if cat.name == name:
                return cat
        return None


class ScoringConfig(BaseModel):
    """Scoring parameters."""

    min_checks_per_rubric: int = Field(ge=1, description="Minimum checks per rubric")
    max_checks_per_rubric: int = Field(ge=1, description="Maximum checks per rubric")
    max_score: float = Field(gt=0, description="Maximum possible score")
    min_score: float = Field(ge=0, description="Minimum possible score")
    calculation_method: Literal["weighted_checklist"] = Field(
        default="weighted_checklist",
        description="Score calculation method"
    )

    @validator("max_checks_per_rubric")
    def max_ge_min(cls, v, values):
        """Ensure max_checks >= min_checks."""
        if "min_checks_per_rubric" in values and v < values["min_checks_per_rubric"]:
            raise ValueError("max_checks_per_rubric must be >= min_checks_per_rubric")
        return v

    @validator("min_score")
    def min_lt_max(cls, v, values):
        """Ensure min_score < max_score."""
        if "max_score" in values and v >= values["max_score"]:
            raise ValueError("min_score must be < max_score")
        return v

    class Config:
        title = "Scoring Configuration"


class CheckEvaluationConfig(BaseModel):
    """Check evaluation parameters."""

    default_on_unclear: bool = Field(
        default=False,
        description="Default check result if LLM response is unclear"
    )
    require_evidence: bool = Field(
        default=True,
        description="Require evidence for check evaluation"
    )
    allow_partial_credit: bool = Field(
        default=False,
        description="Allow partial credit for checks (future feature)"
    )

    class Config:
        title = "Check Evaluation Configuration"


class RubricGenerationConfig(BaseModel):
    """Rubric generation parameters."""

    rubric_style: Literal["prescriptive", "holistic"] = Field(
        default="prescriptive",
        description="Rubric style: prescriptive (absolute deductions) or holistic"
    )
    points_per_dimension: float = Field(
        gt=0,
        description="Expected total points per dimension"
    )
    allow_regeneration_on_validation_failure: bool = Field(
        default=True,
        description="Allow regeneration if validation fails"
    )
    max_regeneration_attempts: int = Field(
        ge=1,
        description="Maximum regeneration attempts"
    )

    class Config:
        title = "Rubric Generation Configuration"


class AppealsConfig(BaseModel):
    """Grade appeal parameters."""

    only_upward_adjustments: bool = Field(
        default=True,
        description="Only allow upward grade adjustments on appeal"
    )
    track_grade_history: bool = Field(
        default=True,
        description="Track all grade versions for audit trail"
    )
    max_increase_per_appeal: float = Field(
        ge=0,
        description="Maximum score increase allowed per appeal"
    )

    class Config:
        title = "Appeals Configuration"


class StorageConfig(BaseModel):
    """Storage and logging configuration."""

    base_directory: str = Field(
        default="grading_results",
        description="Base directory for all grading data"
    )
    rubrics_directory: str = Field(
        default="rubrics",
        description="Subdirectory for rubrics (relative to base)"
    )
    grades_directory: str = Field(
        default="grades",
        description="Subdirectory for grades (relative to base)"
    )
    appeals_directory: str = Field(
        default="appeals",
        description="Subdirectory for appeals (relative to base)"
    )
    logs_directory: str = Field(
        default="logs",
        description="Subdirectory for logs (relative to base)"
    )
    enable_logging: bool = Field(
        default=True,
        description="Enable logging"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    class Config:
        title = "Storage Configuration"


class GradingConfigSchema(BaseModel):
    """Complete grading configuration schema."""

    scoring: ScoringConfig = Field(..., description="Scoring parameters")
    check_evaluation: CheckEvaluationConfig = Field(
        ..., description="Check evaluation parameters"
    )
    rubric_generation: RubricGenerationConfig = Field(
        ..., description="Rubric generation parameters"
    )
    appeals: AppealsConfig = Field(..., description="Appeals parameters")
    storage: StorageConfig = Field(..., description="Storage parameters")

    class Config:
        title = "Grading Configuration"


def load_categories_config(file_path: str) -> CategoriesConfig:
    """Load and validate categories configuration from YAML file."""
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)
    return CategoriesConfig(**data)


def load_grading_config(file_path: str) -> GradingConfigSchema:
    """Load and validate grading configuration from YAML file."""
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)
    return GradingConfigSchema(**data)


def validate_config_values(categories: CategoriesConfig, grading: GradingConfigSchema) -> tuple[bool, list[str]]:
    """
    Cross-validate configurations to ensure consistency.

    Args:
        categories: Validated categories configuration
        grading: Validated grading configuration

    Returns:
        Tuple of (is_valid, list of validation error messages)
    """
    errors = []

    # Validate that all category weights are positive
    for cat in categories.categories:
        if cat.weight <= 0:
            errors.append(f"Category '{cat.name}' has non-positive weight: {cat.weight}")

    # Validate scoring config consistency
    if grading.scoring.max_checks_per_rubric < grading.scoring.min_checks_per_rubric:
        errors.append(
            f"max_checks_per_rubric ({grading.scoring.max_checks_per_rubric}) "
            f"< min_checks_per_rubric ({grading.scoring.min_checks_per_rubric})"
        )

    if grading.scoring.min_score >= grading.scoring.max_score:
        errors.append(
            f"min_score ({grading.scoring.min_score}) "
            f">= max_score ({grading.scoring.max_score})"
        )

    return len(errors) == 0, errors


if __name__ == "__main__":
    # Example usage and validation
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            config = load_grading_config(file_path)
            print("✓ Configuration is valid")
            print(f"  Scoring method: {config.scoring.calculation_method}")
            print(f"  Max score: {config.scoring.max_score}")
        except Exception as e:
            print(f"✗ Configuration validation failed: {e}")
            sys.exit(1)
