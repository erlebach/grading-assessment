"""Integration tests for pipeline module.

Note: Full pipeline tests require LLM setup and may be slow.
These tests focus on setup, error handling, and result formatting.

"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from grading_pipeline.pipeline import (
    grade_question_batch,
    setup_grading_environment,
    write_results,
)
from grading_pipeline.submission_loader import load_all_submissions_for_question


def test_write_results() -> None:
    """Test writing results to file."""
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "results.json"
        results = [
            {
                "student_id": "student_001",
                "question_id": "q01",
                "score": 8,
                "max_score": 10,
            },
            {
                "student_id": "student_002",
                "question_id": "q01",
                "error": "Test error",
            },
        ]

        write_results(results, "q01", output_path)

        assert output_path.exists()
        import json

        with open(output_path) as f:
            data = json.load(f)

        assert data["question_id"] == "q01"
        assert data["total_students"] == 2
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert len(data["students"]) == 2
        print("✓ test_write_results passed")


def test_write_results_per_student() -> None:
    """Test writing per-student result files."""
    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_path = output_dir / "results.json"
        results = [
            {
                "student_id": "student_001",
                "question_id": "q01",
                "score": 8,
                "max_score": 10,
            }
        ]

        write_results(results, "q01", output_path, per_student=True)

        # Check batch file
        assert output_path.exists()

        # Check per-student file
        student_file = output_dir / "student_001_q01.json"
        assert student_file.exists()
        print("✓ test_write_results_per_student passed")


# Note: Full pipeline integration tests would require:
# - Actual LLM setup (Gemini/Ollama)
# - Real rubric files
# - Real source documents
# - Index building
# These are better suited for manual testing or CI/CD with proper setup


if __name__ == "__main__":
    test_write_results()
    test_write_results_per_student()
    print("\n✓ All pipeline tests passed")
    print("\nNote: Full integration tests require LLM setup.")
    print("Run manual tests with:")
    print("  python -m grading_pipeline.cli grade-question --question q01 ...")
