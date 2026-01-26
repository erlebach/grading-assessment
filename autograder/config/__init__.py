"""
Configuration module for the weighted checklist grading system.

Provides:
- Configuration schemas (Pydantic validation)
- Configuration loading with CLI override support
- Category and grading parameter definitions
"""

from .config_loader import (
    load_all_configs,
    create_config_argparser,
    parse_cli_overrides,
    apply_cli_overrides,
)
from .grading_config_schema import (
    CategoriesConfig,
    GradingConfigSchema,
    CategoryDefinition,
    ScoringConfig,
    CheckEvaluationConfig,
    RubricGenerationConfig,
    AppealsConfig,
    StorageConfig,
    load_categories_config,
    load_grading_config,
    validate_config_values,
)

__all__ = [
    # Loaders
    "load_all_configs",
    "create_config_argparser",
    "parse_cli_overrides",
    "apply_cli_overrides",
    # Schemas
    "CategoriesConfig",
    "GradingConfigSchema",
    "CategoryDefinition",
    "ScoringConfig",
    "CheckEvaluationConfig",
    "RubricGenerationConfig",
    "AppealsConfig",
    "StorageConfig",
    "load_categories_config",
    "load_grading_config",
    "validate_config_values",
]
