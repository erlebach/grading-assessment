"""Tests for submission_loader module."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from grading_pipeline.submission_loader import (
    load_all_submissions_for_question,
    load_submission,
)


def test_load_submission_valid() -> None:
    """Test loading a valid submission."""
    with TemporaryDirectory() as tmpdir:
        submission_path = Path(tmpdir) / "student_001_q01.yaml"
        submission_data = {
            "student_id": "student_001",
            "question_id": "q01",
            "question_text": "Test question",
            "answer": "Test answer",
            "rubric_version": "1.0",
            "metadata": {"created_at": "2026-01-17T10:30:00"},
        }
        with open(submission_path, "w") as f:
            yaml.dump(submission_data, f)

        result = load_submission(submission_path)
        assert result["student_id"] == "student_001"
        assert result["question_id"] == "q01"
        assert result["answer"] == "Test answer"
        print("✓ test_load_submission_valid passed")


def test_load_submission_missing_fields() -> None:
    """Test loading a submission with missing required fields."""
    with TemporaryDirectory() as tmpdir:
        submission_path = Path(tmpdir) / "student_001_q01.yaml"
        submission_data = {
            "student_id": "student_001",
            # Missing question_id, question_text, answer
        }
        with open(submission_path, "w") as f:
            yaml.dump(submission_data, f)

        with pytest.raises(ValueError, match="missing required fields"):
            load_submission(submission_path)
    print("✓ test_load_submission_missing_fields passed")


def test_load_all_submissions_for_question() -> None:
    """Test loading all submissions for a question."""
    with TemporaryDirectory() as tmpdir:
        submissions_dir = Path(tmpdir)
        # Create multiple submissions for q01
        for i in range(3):
            submission_path = submissions_dir / f"student_{i+1:03d}_q01.yaml"
            submission_data = {
                "student_id": f"student_{i+1:03d}",
                "question_id": "q01",
                "question_text": "Test question",
                "answer": f"Answer {i+1}",
            }
            with open(submission_path, "w") as f:
                yaml.dump(submission_data, f)

        # Create one submission for different question
        other_path = submissions_dir / "student_001_q02.yaml"
        other_data = {
            "student_id": "student_001",
            "question_id": "q02",
            "question_text": "Other question",
            "answer": "Other answer",
        }
        with open(other_path, "w") as f:
            yaml.dump(other_data, f)

        results = load_all_submissions_for_question(submissions_dir, "q01")
        assert len(results) == 3
        assert all(r["question_id"] == "q01" for r in results)
        print("✓ test_load_all_submissions_for_question passed")


def test_load_all_submissions_for_question_none_found() -> None:
    """Test loading submissions when none match the question."""
    with TemporaryDirectory() as tmpdir:
        submissions_dir = Path(tmpdir)
        # Create submission for different question
        submission_path = submissions_dir / "student_001_q02.yaml"
        submission_data = {
            "student_id": "student_001",
            "question_id": "q02",
            "question_text": "Other question",
            "answer": "Other answer",
        }
        with open(submission_path, "w") as f:
            yaml.dump(submission_data, f)

        with pytest.raises(ValueError, match="No submissions found"):
            load_all_submissions_for_question(submissions_dir, "q01")
    print("✓ test_load_all_submissions_for_question_none_found passed")


if __name__ == "__main__":
    test_load_submission_valid()
    test_load_submission_missing_fields()
    test_load_all_submissions_for_question()
    test_load_all_submissions_for_question_none_found()
    print("\n✓ All submission_loader tests passed")
