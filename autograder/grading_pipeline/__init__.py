"""
Grading Pipeline: Automated rubric-based grading with weighted checklist system.

This module provides:
- Rubric generation and extraction
- Check evaluation (binary pass/fail)
- Grade calculation with category-based weighting
- Grade appeals with version tracking
- Complete audit trail for reproducibility

Core components:
- models: Pydantic data models for all grading entities
- schemas: JSON schema exports for API documentation
- config: Configuration loading with CLI overrides
"""

from .models import (
    Check,
    CheckCategory,
    Rubric,
    CheckEvaluation,
    CheckEvaluationResult,
    GradeResult,
    GradeCalculation,
    Appeal,
)
from .schemas import (
    get_check_schema,
    get_rubric_schema,
    get_check_evaluation_schema,
    get_grade_result_schema,
    get_appeal_schema,
    get_all_schemas,
    save_schemas_to_file,
)

__version__ = "2.1.0"

__all__ = [
    # Models
    "Check",
    "CheckCategory",
    "Rubric",
    "CheckEvaluation",
    "CheckEvaluationResult",
    "GradeResult",
    "GradeCalculation",
    "Appeal",
    # Schemas
    "get_check_schema",
    "get_rubric_schema",
    "get_check_evaluation_schema",
    "get_grade_result_schema",
    "get_appeal_schema",
    "get_all_schemas",
    "save_schemas_to_file",
]
