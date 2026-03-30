"""T2.2 — Extract Check objects from LLM rubric JSON responses.

Takes the raw JSON string produced by the LLM (validated against
RubricJsonResponse) and converts it into canonical Rubric + Check
Pydantic models ready for downstream categorisation and deduplication.

Public API
----------
extract_checks(raw_json, question_id, rubric_id, version=1) -> Rubric
parse_rubric_json(raw_json) -> RubricJsonResponse   # exposed for testing
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from .models import Check, CheckCategory, Rubric
from .rubric_schema import RubricJsonResponse


# ---------------------------------------------------------------------------
# JSON cleaning helpers
# ---------------------------------------------------------------------------

def _strip_json_fence(text: str) -> str:
    """Remove markdown code fences if the LLM wrapped the JSON in them."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> str:
    """Return the first top-level {...} block found in text."""
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM response")
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unmatched braces in LLM response")


# ---------------------------------------------------------------------------
# Parse & validate
# ---------------------------------------------------------------------------

def parse_rubric_json(raw_json: str) -> RubricJsonResponse:
    """Parse and validate raw LLM output into a RubricJsonResponse.

    Args:
        raw_json: Raw string from the LLM (may contain markdown fences or
                  leading/trailing text).

    Returns:
        Validated RubricJsonResponse.

    Raises:
        ValueError: If JSON cannot be parsed or fails schema validation.
    """
    cleaned = _strip_json_fence(raw_json)
    json_str = _extract_json_object(cleaned)

    try:
        data: dict[str, Any] = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in LLM response: {exc}") from exc

    try:
        return RubricJsonResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"LLM rubric failed schema validation:\n{exc}") from exc


# ---------------------------------------------------------------------------
# Conversion to canonical models
# ---------------------------------------------------------------------------

def extract_checks(
    raw_json: str,
    question_id: str,
    rubric_id: str | None = None,
    version: int = 1,
) -> Rubric:
    """Parse the LLM rubric JSON and return a canonical Rubric with Checks.

    Check IDs are generated as:  ``{question_id}_d{dim_idx}_c{check_idx}``
    e.g. ``q01_d1_c2`` for question q01, dimension 1, check 2.

    Args:
        raw_json:    Raw LLM output string.
        question_id: Identifier for the question (e.g. "q01").
        rubric_id:   Rubric identifier; defaults to ``{question_id}_rubric``.
        version:     Rubric version number (default 1).

    Returns:
        A fully-populated Rubric containing all extracted Check objects.

    Raises:
        ValueError: On parse or validation failure.
    """
    if rubric_id is None:
        rubric_id = f"{question_id}_rubric"

    response = parse_rubric_json(raw_json)

    checks: list[Check] = []
    dimensions_raw: list[dict[str, Any]] = []

    for dim_idx, dim in enumerate(response.dimensions, start=1):
        dimensions_raw.append({
            "title": dim.title,
            "category": dim.category.value,
            "points": dim.points,
            "num_checks": len(dim.checks),
        })

        for check_idx, raw_check in enumerate(dim.checks, start=1):
            check_id = f"{question_id}_d{dim_idx}_c{check_idx}"
            checks.append(
                Check(
                    id=check_id,
                    text=raw_check.text,
                    category=CheckCategory(dim.category.value),
                    weight=raw_check.weight,
                    rubric_id=rubric_id,
                    dimension_id=f"{question_id}_d{dim_idx}",
                    question_id=question_id,
                    evidence=dim.title,   # dimension title as audit trail
                )
            )

    return Rubric(
        id=rubric_id,
        question_id=question_id,
        title=f"Rubric for {question_id}",
        description=f"Auto-extracted from LLM response (v{version})",
        checks=checks,
        dimensions=dimensions_raw,
        total_points=float(response.total_points),
        version=version,
    )
