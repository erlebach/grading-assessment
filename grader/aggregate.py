"""Aggregate scores across multiple questions."""

from typing import Any


def aggregate_scores(question_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate scores from multiple question results.

    Args:
        question_results: List of question result dictionaries, each
            containing 'score' and 'max_score' keys.

    Returns:
        Dictionary containing:
        - total_score: Sum of all scores
        - total_max_score: Sum of all max scores
        - percentage: Percentage score (0-100)
        - question_count: Number of questions graded

    """
    total_score = sum(result.get("score", 0.0) for result in question_results)
    total_max_score = sum(
        result.get("max_score", 0.0) for result in question_results
    )

    percentage = (
        (total_score / total_max_score * 100) if total_max_score > 0 else 0.0
    )

    return {
        "total_score": total_score,
        "total_max_score": total_max_score,
        "percentage": percentage,
        "question_count": len(question_results),
    }
