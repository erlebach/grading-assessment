"""Submission converter utilities for driving scripts.

This module provides utility functions for driving scripts to convert
from simple inputs to self-contained submission format.

"""

from datetime import datetime
from pathlib import Path
from typing import Any

from grader.grade_question import load_rubric
from grading_pipeline.config_loader import get_rubric_path


def create_self_contained_submission(
    student_id: str,
    question_id: str,
    answer: str,
    rubrics_config_path: Path,
) -> dict[str, Any]:
    """Create self-contained submission from simple inputs.

    Loads rubric config, finds rubric file, embeds question_text.
    Returns dict ready to write as YAML.

    This is used by driving scripts, not the main pipeline.

    Args:
        student_id: Student identifier.
        question_id: Question identifier (must exist in rubric config).
        answer: Student's answer text.
        rubrics_config_path: Path to rubric configuration YAML file.

    Returns:
        Dictionary ready to write as YAML with all required fields:
        - student_id
        - question_id
        - question_text (from rubric)
        - answer
        - rubric_version (from rubric metadata)
        - metadata (created_at, rubric_path)

    Raises:
        ValueError: If question_id not found in config or rubric missing question_text.

    """
    # Get rubric path from config
    rubric_path = get_rubric_path(question_id, rubrics_config_path)

    # Load rubric to extract question_text and version
    rubric = load_rubric(rubric_path)

    # Extract question_text from rubric
    if "question_text" not in rubric:
        raise ValueError(f"Rubric {rubric_path} missing required 'question_text' field")

    question_text = rubric["question_text"]

    # Extract rubric version from metadata
    rubric_version = "1.0"  # Default
    if "metadata" in rubric and "version" in rubric["metadata"]:
        rubric_version = str(rubric["metadata"]["version"])
    elif "rubric_version" in rubric:
        rubric_version = str(rubric["rubric_version"])

    # Create self-contained submission
    submission = {
        "student_id": student_id,
        "question_id": question_id,
        "question_text": question_text,
        "rubric_version": rubric_version,
        "answer": answer,
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "rubric_path": str(rubric_path),
        },
    }

    return submission


if __name__ == "__main__":
    # Test conversion
    test_config = Path(__file__).parent / "config" / "rubrics.yaml"
    if test_config.exists():
        try:
            submission = create_self_contained_submission(
                student_id="student_001",
                question_id="q01",
                answer="This is a test answer.",
                rubrics_config_path=test_config,
            )
            print("✓ Created self-contained submission:")
            print(f"  student_id: {submission['student_id']}")
            print(f"  question_id: {submission['question_id']}")
            print(f"  question_text: {submission['question_text'][:50]}...")
            print(f"  answer length: {len(submission['answer'])} chars")
            print(f"  rubric_version: {submission['rubric_version']}")
        except Exception as e:
            print(f"⚠ Test failed: {e}")
    else:
        print(f"⚠ Test config not found: {test_config}")
