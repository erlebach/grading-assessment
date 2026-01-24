"""Criterion loader for multi-dimensional reranking queries.

This module loads criterion descriptions and titles from JSON files
to support criterion-specific evidence retrieval queries.

"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_criterion_descriptions(question_id: str) -> dict[str, str]:
    """Load criterion descriptions from JSON file.

    Args:
        question_id: Question identifier (e.g., "q01")

    Returns:
        Dictionary mapping criterion_id to description string.
        Returns empty dict if file not found or invalid JSON.

    """
    json_path = Path(__file__).parent.parent / "rubrics_dynamic" / "json" / f"{question_id}_title_description_converted.json"

    try:
        if not json_path.exists():
            logger.warning(
                f"Criterion JSON file not found: {json_path}. "
                f"Using fallback empty descriptions."
            )
            return {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        descriptions = {}
        for criterion in data.get("criterion_titles", []):
            criterion_id = criterion.get("criterion_id")
            description = criterion.get("description", "")
            if criterion_id and description:
                descriptions[criterion_id] = description

        logger.debug(
            f"Loaded {len(descriptions)} criterion descriptions from {json_path}"
        )
        return descriptions

    except (json.JSONDecodeError, IOError) as e:
        logger.warning(
            f"Error loading criterion descriptions from {json_path}: {e}. "
            f"Using fallback empty descriptions."
        )
        return {}


def load_criterion_titles(question_id: str) -> dict[str, str]:
    """Load criterion titles from JSON file.

    Args:
        question_id: Question identifier (e.g., "q01")

    Returns:
        Dictionary mapping criterion_id to title string.
        Returns empty dict if file not found or invalid JSON.

    """
    json_path = Path(__file__).parent.parent / "rubrics_dynamic" / "json" / f"{question_id}_title_description_converted.json"

    try:
        if not json_path.exists():
            logger.warning(
                f"Criterion JSON file not found: {json_path}. "
                f"Using fallback empty titles."
            )
            return {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        titles = {}
        for criterion in data.get("criterion_titles", []):
            criterion_id = criterion.get("criterion_id")
            title = criterion.get("title", "")
            if criterion_id and title:
                titles[criterion_id] = title

        logger.debug(f"Loaded {len(titles)} criterion titles from {json_path}")
        return titles

    except (json.JSONDecodeError, IOError) as e:
        logger.warning(
            f"Error loading criterion titles from {json_path}: {e}. "
            f"Using fallback empty titles."
        )
        return {}


def get_criterion_description(
    question_id: str, criterion_id: str, fallback: Optional[str] = None
) -> str:
    """Get a single criterion description with fallback.

    Args:
        question_id: Question identifier
        criterion_id: Criterion identifier
        fallback: Fallback description if not found (default: empty string)

    Returns:
        Criterion description string or fallback value

    """
    descriptions = load_criterion_descriptions(question_id)
    return descriptions.get(criterion_id, fallback or "")


def get_criterion_title(
    question_id: str, criterion_id: str, fallback: Optional[str] = None
) -> str:
    """Get a single criterion title with fallback.

    Args:
        question_id: Question identifier
        criterion_id: Criterion identifier
        fallback: Fallback title if not found (default: formatted criterion_id)

    Returns:
        Criterion title string or fallback value

    """
    titles = load_criterion_titles(question_id)
    if criterion_id in titles:
        return titles[criterion_id]

    # Use fallback or format criterion_id
    if fallback:
        return fallback
    return criterion_id.replace("_", " ").title()
