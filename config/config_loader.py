"""
Configuration loader with CLI argument override support.

Loads configurations from YAML files with support for CLI argument overrides.
Configuration hierarchy: CLI arguments > YAML files > defaults

Usage:
    from config.config_loader import load_all_configs

    categories, grading = load_all_configs(
        categories_file="config/grading_categories.yaml",
        grading_file="config/grading_config.yaml",
        cli_overrides={
            "scoring.max_score": 100,
            "scoring.calculation_method": "weighted_checklist",
        }
    )
"""

import argparse
from pathlib import Path
from typing import Any, Optional
import yaml

from .grading_config_schema import (
    CategoriesConfig,
    GradingConfigSchema,
    load_categories_config,
    load_grading_config,
    validate_config_values,
)


def apply_cli_overrides(config_dict: dict, cli_overrides: dict) -> dict:
    """
    Apply CLI argument overrides to configuration dictionary.

    Supports nested keys using dot notation (e.g., "scoring.max_score").

    Args:
        config_dict: Configuration dictionary
        cli_overrides: Dictionary of CLI overrides with dot-notation keys

    Returns:
        Updated configuration dictionary
    """
    for key_path, value in cli_overrides.items():
        keys = key_path.split(".")
        current = config_dict

        # Navigate to parent dict
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set final value
        final_key = keys[-1]
        current[final_key] = value

    return config_dict


def load_all_configs(
    categories_file: Optional[str] = None,
    grading_file: Optional[str] = None,
    cli_overrides: Optional[dict] = None,
) -> tuple[CategoriesConfig, GradingConfigSchema]:
    """
    Load all configurations with CLI overrides.

    Args:
        categories_file: Path to categories YAML file
        grading_file: Path to grading YAML file
        cli_overrides: Dictionary of CLI overrides (dot notation)

    Returns:
        Tuple of (categories_config, grading_config)

    Raises:
        FileNotFoundError: If config files not found
        ValueError: If configuration validation fails
    """
    # Use default paths if not provided
    if categories_file is None:
        categories_file = str(Path(__file__).parent / "grading_categories.yaml")
    if grading_file is None:
        grading_file = str(Path(__file__).parent / "grading_config.yaml")

    cli_overrides = cli_overrides or {}

    # Load categories
    categories = load_categories_config(categories_file)

    # Load grading config
    grading = load_grading_config(grading_file)

    # Apply CLI overrides to grading config (categories rarely need overrides)
    if cli_overrides:
        # Convert to dict, apply overrides, reconstruct
        with open(grading_file) as f:
            grading_dict = yaml.safe_load(f)

        grading_dict = apply_cli_overrides(grading_dict, cli_overrides)
        grading = GradingConfigSchema(**grading_dict)

    # Cross-validate
    is_valid, errors = validate_config_values(categories, grading)
    if not is_valid:
        error_msg = "Configuration validation failed:\n" + "\n".join(errors)
        raise ValueError(error_msg)

    return categories, grading


def create_config_argparser() -> argparse.ArgumentParser:
    """
    Create argument parser for configuration overrides.

    Returns:
        ArgumentParser configured for grading system CLI
    """
    parser = argparse.ArgumentParser(
        description="Grading system with weighted checklist evaluation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Configuration files
    parser.add_argument(
        "--categories-config",
        type=str,
        default=None,
        help="Path to categories configuration YAML file",
    )
    parser.add_argument(
        "--grading-config",
        type=str,
        default=None,
        help="Path to grading configuration YAML file",
    )

    # Scoring overrides
    scoring_group = parser.add_argument_group("scoring", "Scoring parameters")
    scoring_group.add_argument(
        "--max-score",
        type=float,
        default=None,
        dest="max_score",
        help="Maximum possible score",
    )
    scoring_group.add_argument(
        "--min-score",
        type=float,
        default=None,
        dest="min_score",
        help="Minimum possible score",
    )
    scoring_group.add_argument(
        "--calculation-method",
        type=str,
        default=None,
        dest="calculation_method",
        choices=["weighted_checklist"],
        help="Score calculation method",
    )

    # Check evaluation overrides
    check_group = parser.add_argument_group("check_evaluation", "Check evaluation parameters")
    check_group.add_argument(
        "--default-on-unclear",
        type=bool,
        default=None,
        dest="default_on_unclear",
        help="Default check result if LLM response is unclear",
    )
    check_group.add_argument(
        "--require-evidence",
        type=bool,
        default=None,
        dest="require_evidence",
        help="Require evidence for check evaluation",
    )

    # Appeals overrides
    appeals_group = parser.add_argument_group("appeals", "Grade appeal parameters")
    appeals_group.add_argument(
        "--only-upward-adjustments",
        type=bool,
        default=None,
        dest="only_upward_adjustments",
        help="Only allow upward grade adjustments",
    )
    appeals_group.add_argument(
        "--max-increase-per-appeal",
        type=float,
        default=None,
        dest="max_increase_per_appeal",
        help="Maximum score increase per appeal",
    )

    # Verbosity
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser


def parse_cli_overrides(args: argparse.Namespace) -> dict:
    """
    Convert argparse Namespace to CLI overrides dictionary.

    Only includes arguments that were explicitly set (not None or defaults).

    Args:
        args: Parsed command-line arguments

    Returns:
        Dictionary of CLI overrides in dot-notation format
    """
    overrides = {}
    arg_to_key = {
        "max_score": "scoring.max_score",
        "min_score": "scoring.min_score",
        "calculation_method": "scoring.calculation_method",
        "default_on_unclear": "check_evaluation.default_on_unclear",
        "require_evidence": "check_evaluation.require_evidence",
        "only_upward_adjustments": "appeals.only_upward_adjustments",
        "max_increase_per_appeal": "appeals.max_increase_per_appeal",
    }

    for arg_name, key_path in arg_to_key.items():
        if hasattr(args, arg_name):
            value = getattr(args, arg_name)
            if value is not None:  # Only add if explicitly set
                overrides[key_path] = value

    return overrides


if __name__ == "__main__":
    # Example usage
    parser = create_config_argparser()
    args = parser.parse_args()

    # Load configurations with CLI overrides
    cli_overrides = parse_cli_overrides(args)
    categories, grading = load_all_configs(
        categories_file=args.categories_config,
        grading_file=args.grading_config,
        cli_overrides=cli_overrides,
    )

    print("Configuration loaded successfully!")
    print(f"Categories: {[cat.name for cat in categories.categories]}")
    print(f"Scoring method: {grading.scoring.calculation_method}")
    print(f"Max score: {grading.scoring.max_score}")
    if cli_overrides:
        print(f"CLI overrides applied: {cli_overrides}")
