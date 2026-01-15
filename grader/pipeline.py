"""Grading pipeline orchestration."""

from pathlib import Path
from typing import Any

from .grade_question import grade_question
from .aggregate import aggregate_scores


def run_grading_pipeline(
    submission_path: Path,
    rubric_path: Path,
    evidence_index_path: Path | None = None,
) -> dict[str, Any]:
    """Run the complete grading pipeline for a submission.

    Args:
        submission_path: Path to the student submission file.
        rubric_path: Path to the rubric YAML file.
        evidence_index_path: Optional path to the evidence index.

    Returns:
        Dictionary containing grading results with scores, explanations,
        and citations.

    """
    # Grade the question
    question_result = grade_question(
        submission_path=submission_path,
        rubric_path=rubric_path,
        evidence_index_path=evidence_index_path,
    )

    # Aggregate scores (if multiple questions)
    aggregated = aggregate_scores([question_result])

    return {
        "question_results": [question_result],
        "aggregated": aggregated,
    }
