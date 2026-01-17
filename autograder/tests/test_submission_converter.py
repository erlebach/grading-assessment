"""Tests for submission_converter module."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from grading_pipeline.submission_converter import create_self_contained_submission


def test_create_self_contained_submission() -> None:
    """Test creating a self-contained submission."""
    with TemporaryDirectory() as tmpdir:
        # Create rubric config
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()
        config_path = config_dir / "rubrics.yaml"

        # Create rubric file
        rubric_dir = Path(tmpdir) / "rubrics"
        rubric_dir.mkdir()
        rubric_path = rubric_dir / "q01.yaml"
        rubric_data = {
            "question_id": "q01",
            "question_text": "What is mutual information?",
            "total_points": 10,
            "criteria": [],
            "metadata": {"version": "1.0"},
        }
        with open(rubric_path, "w") as f:
            yaml.dump(rubric_data, f)

        # Create config
        config_data = {
            "rubrics": {
                "q01": {
                    "path": str(rubric_path),
                    "description": "Question 1",
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Create submission
        result = create_self_contained_submission(
            student_id="student_001",
            question_id="q01",
            answer="Mutual information measures...",
            rubrics_config_path=config_path,
        )

        assert result["student_id"] == "student_001"
        assert result["question_id"] == "q01"
        assert result["question_text"] == "What is mutual information?"
        assert result["answer"] == "Mutual information measures..."
        assert result["rubric_version"] == "1.0"
        assert "metadata" in result
        assert "created_at" in result["metadata"]
        print("✓ test_create_self_contained_submission passed")


def test_create_self_contained_submission_missing_question_text() -> None:
    """Test creating submission when rubric lacks question_text."""
    with TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()
        config_path = config_dir / "rubrics.yaml"

        rubric_dir = Path(tmpdir) / "rubrics"
        rubric_dir.mkdir()
        rubric_path = rubric_dir / "q01.yaml"
        # Rubric without question_text
        rubric_data = {
            "question_id": "q01",
            "total_points": 10,
        }
        with open(rubric_path, "w") as f:
            yaml.dump(rubric_data, f)

        config_data = {
            "rubrics": {
                "q01": {
                    "path": str(rubric_path),
                    "description": "Question 1",
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError, match="missing required 'question_text' field"):
            create_self_contained_submission(
                student_id="student_001",
                question_id="q01",
                answer="Test answer",
                rubrics_config_path=config_path,
            )
    print("✓ test_create_self_contained_submission_missing_question_text passed")


if __name__ == "__main__":
    test_create_self_contained_submission()
    test_create_self_contained_submission_missing_question_text()
    print("\n✓ All submission_converter tests passed")
