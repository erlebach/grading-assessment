"""Submission loader for grading pipeline.

This module loads self-contained submission files and groups them by question_id
for batch processing.

"""

from pathlib import Path
from typing import Any

import yaml


def load_submission(submission_path: Path) -> dict[str, Any]:
    """Load self-contained submission from YAML file.

    Args:
        submission_path: Path to the submission YAML file.

    Returns:
        Dictionary containing submission data (student_id, question_id,
        question_text, answer, rubric_version, metadata).

    Raises:
        FileNotFoundError: If submission file doesn't exist.
        ValueError: If submission is missing required fields.

    """
    if not submission_path.exists():
        raise FileNotFoundError(f"Submission file not found: {submission_path}")

    with open(submission_path, "r") as f:
        submission = yaml.safe_load(f)

    if not submission:
        raise ValueError(f"Empty submission file: {submission_path}")

    # Validate required fields
    required_fields = ["student_id", "question_id", "question_text", "answer"]
    missing_fields = [field for field in required_fields if field not in submission]

    if missing_fields:
        raise ValueError(
            f"Submission missing required fields: {', '.join(missing_fields)} "
            f"in {submission_path}"
        )

    return submission


def load_all_submissions_for_question(
    submissions_dir: Path, question_id: str
) -> list[dict[str, Any]]:
    """Load all submissions for a specific question.

    Groups submissions by question_id for batch processing.
    Validates all submissions have matching question_id.

    Args:
        submissions_dir: Directory containing submission YAML files.
        question_id: The question identifier to filter by.

    Returns:
        List of submission dictionaries, all for the specified question_id.

    Raises:
        FileNotFoundError: If submissions directory doesn't exist.
        ValueError: If no submissions found or submissions have mismatched question_ids.

    """
    if not submissions_dir.exists():
        raise FileNotFoundError(f"Submissions directory not found: {submissions_dir}")

    # Find all YAML files in submissions directory
    submission_files = list(submissions_dir.glob("*.yaml")) + list(
        submissions_dir.glob("*.yml")
    )

    if not submission_files:
        raise ValueError(f"No submission files found in {submissions_dir}")

    submissions = []
    mismatched_questions = []

    for submission_file in submission_files:
        try:
            submission = load_submission(submission_file)
            submission_question_id = submission["question_id"]

            if submission_question_id == question_id:
                submissions.append(submission)
            else:
                mismatched_questions.append(
                    (submission_file.name, submission_question_id)
                )
        except Exception as e:
            # Log but continue - some files might be invalid
            print(f"⚠ Warning: Failed to load {submission_file}: {e}", flush=True)
            continue

    if not submissions:
        if mismatched_questions:
            found_questions = ", ".join(set(qid for _, qid in mismatched_questions))
            raise ValueError(
                f"No submissions found for question '{question_id}' in {submissions_dir}. "
                f"Found questions: {found_questions}"
            )
        else:
            raise ValueError(
                f"No valid submissions found for question '{question_id}' in {submissions_dir}"
            )

    return submissions


if __name__ == "__main__":
    # Test submission loading
    test_dir = Path(__file__).parent / "submissions"
    if test_dir.exists():
        try:
            submissions = load_all_submissions_for_question(test_dir, "q01")
            print(f"✓ Loaded {len(submissions)} submissions for q01")
            for sub in submissions:
                print(f"  {sub['student_id']}: {len(sub['answer'])} chars")
        except Exception as e:
            print(f"⚠ Test failed: {e}")
    else:
        print(f"⚠ Test submissions directory not found: {test_dir}")
