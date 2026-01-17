"""Rubric configuration loader for grading pipeline.

This module loads and validates rubric configuration from YAML files,
providing functions to resolve rubric paths for question IDs.

"""

from pathlib import Path
from typing import Any

import yaml


def load_rubric_config(config_path: Path) -> dict[str, dict[str, str]]:
    """Load rubric configuration from YAML file.

    Args:
        config_path: Path to the rubric configuration YAML file.

    Returns:
        Dictionary mapping question_id to rubric metadata (path, description).

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file is invalid or missing required fields.

    """
    if not config_path.exists():
        raise FileNotFoundError(f"Rubric config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not config or "rubrics" not in config:
        raise ValueError(
            f"Invalid rubric config: missing 'rubrics' key in {config_path}"
        )

    rubrics = config["rubrics"]
    if not isinstance(rubrics, dict):
        raise ValueError(
            f"Invalid rubric config: 'rubrics' must be a dictionary in {config_path}"
        )

    # Validate each rubric entry
    validated_rubrics: dict[str, dict[str, str]] = {}
    for question_id, rubric_info in rubrics.items():
        if not isinstance(rubric_info, dict):
            raise ValueError(
                f"Invalid rubric config: rubric entry for {question_id} must be a dictionary"
            )

        if "path" not in rubric_info:
            raise ValueError(
                f"Invalid rubric config: missing 'path' for question {question_id}"
            )

        validated_rubrics[question_id] = {
            "path": str(rubric_info["path"]),
            "description": str(rubric_info.get("description", "")),
        }

    return validated_rubrics


def get_rubric_path(question_id: str, config_path: Path) -> Path:
    """Get rubric path for a question_id.

    Args:
        question_id: The question identifier (e.g., "q01").
        config_path: Path to the rubric configuration YAML file.

    Returns:
        Path to the rubric file for the question.

    Raises:
        ValueError: If question_id not found in config or rubric file doesn't exist.

    """
    config = load_rubric_config(config_path)

    if question_id not in config:
        available = ", ".join(config.keys())
        raise ValueError(
            f"Question ID '{question_id}' not found in rubric config. "
            f"Available questions: {available}"
        )

    rubric_path_str = config[question_id]["path"]
    rubric_path = Path(rubric_path_str)

    # Resolve relative paths relative to config file's directory
    if not rubric_path.is_absolute():
        rubric_path = config_path.parent / rubric_path

    if not rubric_path.exists():
        raise ValueError(
            f"Rubric file not found for question {question_id}: {rubric_path}"
        )

    return rubric_path


if __name__ == "__main__":
    # Test config loading
    test_config = Path(__file__).parent / "config" / "rubrics.yaml"
    if test_config.exists():
        config = load_rubric_config(test_config)
        print(f"✓ Loaded rubric config with {len(config)} questions")
        for qid, info in config.items():
            print(f"  {qid}: {info['path']}")
    else:
        print(f"⚠ Test config not found: {test_config}")
