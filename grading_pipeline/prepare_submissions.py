"""Example driving script for preparing self-contained submissions.

This shows how users can create self-contained submissions from simple inputs.
Users can adapt this script to their workflow.

"""

from pathlib import Path
from typing import Any

import yaml

from grading_pipeline.submission_converter import create_self_contained_submission


def prepare_submissions(
    students_data: list[dict[str, Any]],
    rubrics_config_path: Path,
    output_dir: Path,
) -> None:
    """Convert simple student data to self-contained submissions.

    Args:
        students_data: List of dictionaries with keys:
            - student_id: Student identifier
            - question_id: Question identifier
            - answer: Student's answer text
        rubrics_config_path: Path to rubric configuration YAML file.
        output_dir: Directory to write self-contained submission files.

    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for student_data in students_data:
        try:
            submission = create_self_contained_submission(
                student_id=student_data["student_id"],
                question_id=student_data["question_id"],
                answer=student_data["answer"],
                rubrics_config_path=rubrics_config_path,
            )

            output_file = (
                output_dir
                / f"{submission['student_id']}_{submission['question_id']}.yaml"
            )
            with open(output_file, "w") as f:
                yaml.dump(submission, f, default_flow_style=False, sort_keys=False)

            print(
                f"✓ Created submission: {output_file.name}",
                flush=True,
            )
        except Exception as e:
            print(
                f"✗ Failed to create submission for {student_data.get('student_id', 'unknown')}: {e}",
                flush=True,
            )


def main() -> None:
    """Example usage of prepare_submissions."""
    # Student data for factorial question (q01)
    students_data = [
        {
            "student_id": "student_001",
            "question_id": "q01",
            "answer": """def factorial(n):
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result""",
        },
        {
            "student_id": "student_002",
            "question_id": "q01",
            "answer": """def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result = result * i
    return result""",
        },
    ]

    # Paths
    rubrics_config = Path(__file__).parent / "config" / "rubrics.yaml"
    output_dir = Path(__file__).parent / "submissions"

    if not rubrics_config.exists():
        print(f"⚠ Rubrics config not found: {rubrics_config}", flush=True)
        print("  Please create config/rubrics.yaml first", flush=True)
        return

    prepare_submissions(students_data, rubrics_config, output_dir)


if __name__ == "__main__":
    main()
