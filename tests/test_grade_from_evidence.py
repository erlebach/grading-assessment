"""Tests for grade_from_evidence CLI script.

Comprehensive test suite covering:
- Evidence context loading from JSON
- Student submission loading from YAML
- Command-line argument parsing
- Output file writing
- Verbose flag functionality
- Error handling (missing files, invalid arguments)
- Different answer types
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from grading_dynamic_rubrics.grade_from_evidence import (
    load_evidence_context,
    load_student_submission,
    main,
)


# ============================================================================
# Test Data / Fixtures
# ============================================================================


@pytest.fixture
def sample_evidence_json():
    """Sample evidence context JSON structure."""
    return {
        "question_id": "q02",
        "graded_at": "2026-01-24T20:00:00",
        "total_students": 1,
        "successful": 1,
        "failed": 0,
        "students": [
            {
                "question_id": "q02",
                "question_text": "The slides emphasize that an attribute's properties determine valid analyses.",
                "grading_context": [
                    {
                        "criterion_id": "conceptual_understanding_of_attribute_properties",
                        "criterion_description": "Explains attribute properties: distinctness, order, meaningful intervals, ratios.",
                        "max_score": 3,
                        "evidence": [
                            {
                                "source_id": "file_slides_data_type_quality",
                                "texts": ["Properties of Attribute Values."],
                                "reranker_scores": [1.041],
                                "similarity_scores": [0.699],
                                "indexes": ["sentence_index"],
                            }
                        ],
                    },
                    {
                        "criterion_id": "application_to_the_zip_code_example",
                        "criterion_description": "Identifies zip code as nominal.",
                        "max_score": 2,
                        "evidence": [
                            {
                                "source_id": "file_slides_data_type_quality",
                                "texts": ["Zip codes are categorical."],
                                "reranker_scores": [0.926],
                                "similarity_scores": [0.767],
                                "indexes": ["sentence_index"],
                            }
                        ],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_submission_yaml():
    """Sample student submission YAML structure."""
    return {
        "student_id": "student_001",
        "question_id": "q02",
        "question_text": "The slides emphasize...",
        "answer": "Zip code values are categorical despite being stored as integers.",
        "rubric_version": "1.0",
        "metadata": {
            "created_at": "2026-01-20T10:00:00",
        },
    }


@pytest.fixture
def sample_grading_result():
    """Sample grading result."""
    return {
        "student_id": "student_001",
        "question_id": "q02",
        "answer_type": "good",
        "question_text": "The slides emphasize...",
        "student_answer": "Zip codes are categorical...",
        "total_score": 8.5,
        "max_score": 10,
        "criterion_results": [
            {
                "criterion_id": "conceptual_understanding_of_attribute_properties",
                "llm_score": 9,
                "max_score": 3,
                "weighted_score": 2.7,
                "feedback": "Excellent understanding.",
                "evidence_used": ["file_slides_data_type_quality"],
            },
            {
                "criterion_id": "application_to_the_zip_code_example",
                "llm_score": 8,
                "max_score": 2,
                "weighted_score": 1.6,
                "feedback": "Good application.",
                "evidence_used": ["file_slides_data_type_quality"],
            },
        ],
        "graded_at": "2026-01-24T20:45:00.123456",
    }


# ============================================================================
# Test load_evidence_context
# ============================================================================


class TestLoadEvidenceContext:
    """Tests for load_evidence_context function."""

    def test_load_evidence_context_success(self, sample_evidence_json, tmp_path):
        """Test successful evidence context loading."""
        # Create temporary evidence file
        evidence_file = tmp_path / "q02_results.json"
        with open(evidence_file, "w") as f:
            json.dump(sample_evidence_json, f)

        # Patch the Path to use tmp_path
        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            mock_path.return_value = evidence_file
            result = load_evidence_context("q02")

        assert result["question_id"] == "q02"
        assert "grading_context" in result
        assert len(result["grading_context"]) == 2

    def test_load_evidence_context_file_not_found(self):
        """Test error when evidence file doesn't exist."""
        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_class.return_value = mock_path_instance

            with pytest.raises(FileNotFoundError, match="Evidence file not found"):
                load_evidence_context("q99")

    def test_load_evidence_context_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        evidence_file = tmp_path / "q02_results.json"
        with open(evidence_file, "w") as f:
            f.write("not valid json {]")

        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            mock_path.return_value = evidence_file
            with pytest.raises(json.JSONDecodeError):
                load_evidence_context("q02")

    def test_load_evidence_context_missing_students_key(self, tmp_path):
        """Test handling when 'students' key is missing."""
        evidence_data = {"question_id": "q02", "other_data": []}
        evidence_file = tmp_path / "q02_results.json"
        with open(evidence_file, "w") as f:
            json.dump(evidence_data, f)

        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            mock_path.return_value = evidence_file
            result = load_evidence_context("q02")

        assert result["question_id"] == "q02"
        assert result["grading_context"] == []

    def test_load_evidence_context_empty_students(self, tmp_path):
        """Test handling when students list is empty."""
        evidence_data = {"question_id": "q02", "students": []}
        evidence_file = tmp_path / "q02_results.json"
        with open(evidence_file, "w") as f:
            json.dump(evidence_data, f)

        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            mock_path.return_value = evidence_file
            result = load_evidence_context("q02")

        assert result["question_id"] == "q02"
        assert result["grading_context"] == []

    def test_load_evidence_context_returns_first_student(self, sample_evidence_json, tmp_path):
        """Test that function returns evidence from first student."""
        # Add multiple students
        sample_evidence_json["students"].append({
            "question_id": "q02",
            "question_text": "Different question",
            "grading_context": [],
        })

        evidence_file = tmp_path / "q02_results.json"
        with open(evidence_file, "w") as f:
            json.dump(sample_evidence_json, f)

        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            mock_path.return_value = evidence_file
            result = load_evidence_context("q02")

        # Should return first student's evidence
        assert len(result["grading_context"]) == 2
        assert result["grading_context"][0]["criterion_id"] == "conceptual_understanding_of_attribute_properties"


# ============================================================================
# Test load_student_submission
# ============================================================================


class TestLoadStudentSubmission:
    """Tests for load_student_submission function."""

    def test_load_student_submission_success(self, sample_submission_yaml, tmp_path):
        """Test successful submission loading."""
        # Create temporary submission file
        submissions_dir = tmp_path / "submissions"
        submissions_dir.mkdir()
        submission_file = submissions_dir / "student_001_q02_good.yaml"
        with open(submission_file, "w") as f:
            yaml.dump(sample_submission_yaml, f)

        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            # Mock the submission path construction
            def path_side_effect(path_str):
                if "submissions" in path_str:
                    return submission_file
                return Path(path_str)

            mock_path.side_effect = path_side_effect
            result = load_student_submission("student_001", "q02", "good")

        assert result["student_id"] == "student_001"
        assert result["question_id"] == "q02"
        assert result["answer"] == sample_submission_yaml["answer"]

    def test_load_student_submission_file_not_found(self):
        """Test error when submission file doesn't exist."""
        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_class.return_value = mock_path_instance

            with pytest.raises(FileNotFoundError, match="Submission file not found"):
                load_student_submission("student_001", "q02", "good")

    def test_load_student_submission_invalid_yaml(self, tmp_path):
        """Test error handling for invalid YAML."""
        submissions_dir = tmp_path / "submissions"
        submissions_dir.mkdir()
        submission_file = submissions_dir / "student_001_q02_good.yaml"
        with open(submission_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
            mock_path.return_value = submission_file
            with pytest.raises(yaml.YAMLError):
                load_student_submission("student_001", "q02", "good")

    def test_load_student_submission_different_answer_types(self, tmp_path):
        """Test loading different answer types."""
        submissions_dir = tmp_path / "submissions"
        submissions_dir.mkdir()

        answer_types = ["good", "less_good", "wrong"]
        for answer_type in answer_types:
            submission_data = {
                "student_id": "student_001",
                "question_id": "q02",
                "answer": f"Answer for {answer_type} submission",
            }
            submission_file = submissions_dir / f"student_001_q02_{answer_type}.yaml"
            with open(submission_file, "w") as f:
                yaml.dump(submission_data, f)

            with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
                mock_path.return_value = submission_file
                result = load_student_submission("student_001", "q02", answer_type)

            assert result["answer"] == f"Answer for {answer_type} submission"

    def test_load_student_submission_multiple_students(self, tmp_path):
        """Test loading submissions for different students."""
        submissions_dir = tmp_path / "submissions"
        submissions_dir.mkdir()

        for student_id in ["student_001", "student_002", "student_003"]:
            submission_data = {
                "student_id": student_id,
                "question_id": "q02",
                "answer": f"Answer from {student_id}",
            }
            submission_file = submissions_dir / f"{student_id}_q02_good.yaml"
            with open(submission_file, "w") as f:
                yaml.dump(submission_data, f)

            with patch("grading_dynamic_rubrics.grade_from_evidence.Path") as mock_path:
                mock_path.return_value = submission_file
                result = load_student_submission(student_id, "q02", "good")

            assert result["student_id"] == student_id


# ============================================================================
# Test main CLI Function
# ============================================================================


class TestMainCLI:
    """Tests for main CLI function."""

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_default_arguments(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
        tmp_path,
    ):
        """Test main with default arguments."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        # Mock sys.argv
        with patch.object(sys, "argv", ["grade_from_evidence.py"]):
            # Capture output
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()

            output = mock_stdout.getvalue()
            # Should contain JSON output
            assert "student_001" in output or "q02" in output

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_with_question_argument(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test main with --question argument."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(sys, "argv", ["grade_from_evidence.py", "--question", "q05"]):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        mock_load_evidence.assert_called_once_with("q05")

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_with_student_argument(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test main with --student argument."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(sys, "argv", ["grade_from_evidence.py", "--student", "student_042"]):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        mock_load_submission.assert_called_once_with("student_042", "q02", "good")

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_with_answer_type_argument(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test main with --answer_type argument."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(sys, "argv", ["grade_from_evidence.py", "--answer_type", "wrong"]):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        mock_load_submission.assert_called_once_with("student_001", "q02", "wrong")

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_with_output_argument(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
        tmp_path,
    ):
        """Test main with --output argument."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        output_file = tmp_path / "custom_output.json"

        with patch.object(
            sys,
            "argv",
            ["grade_from_evidence.py", "--output", str(output_file)],
        ):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        # Verify output file was created
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert data["student_id"] == "student_001"

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_verbose_flag(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test main with --verbose flag."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(sys, "argv", ["grade_from_evidence.py", "--verbose"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with patch("sys.stdout", new_callable=StringIO):
                    main()

            stderr_output = mock_stderr.getvalue()
            # Verbose output should include status messages
            assert "Loading evidence" in stderr_output or "Grading" in stderr_output

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_verbose_shows_summary(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test that verbose mode shows summary information."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(sys, "argv", ["grade_from_evidence.py", "--verbose"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with patch("sys.stdout", new_callable=StringIO):
                    main()

            stderr_output = mock_stderr.getvalue()
            # Should show summary information
            assert "SUMMARY" in stderr_output or "Total Score" in stderr_output

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_without_verbose_returns_json_only(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test that without verbose, only JSON is printed to stdout."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(sys, "argv", ["grade_from_evidence.py"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO):
                    main()

            stdout_output = mock_stdout.getvalue()
            # Should be valid JSON
            result = json.loads(stdout_output)
            assert result["student_id"] == "student_001"

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_creates_results_directory(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
        tmp_path,
    ):
        """Test that results directory is created if needed."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        results_dir = tmp_path / "results"
        output_file = results_dir / "test_output.json"

        with patch.object(
            sys,
            "argv",
            ["grade_from_evidence.py", "--output", str(output_file)],
        ):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        assert results_dir.exists()
        assert output_file.exists()

    def test_main_error_missing_evidence_file(self):
        """Test error handling when evidence file is missing."""
        with patch.object(sys, "argv", ["grade_from_evidence.py", "--question", "q99"]):
            with patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context") as mock_load:
                mock_load.side_effect = FileNotFoundError("Evidence file not found: reranker_results/q99_results.json")

                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        main()

                assert exc_info.value.code == 1
                assert "Error:" in mock_stderr.getvalue()

    def test_main_error_missing_submission_file(self):
        """Test error handling when submission file is missing."""
        with patch.object(sys, "argv", ["grade_from_evidence.py"]):
            with patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context") as mock_load_ev:
                with patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission") as mock_load_sub:
                    mock_load_ev.return_value = {"question_id": "q02"}
                    mock_load_sub.side_effect = FileNotFoundError("Submission file not found")

                    with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                        with pytest.raises(SystemExit) as exc_info:
                            main()

                    assert exc_info.value.code == 1
                    assert "Error:" in mock_stderr.getvalue()

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_error_during_grading(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
    ):
        """Test error handling during grading."""
        mock_load_evidence.return_value = {"question_id": "q02"}
        mock_load_submission.return_value = {"student_id": "student_001"}
        mock_grade.side_effect = RuntimeError("LLM call failed")

        with patch.object(sys, "argv", ["grade_from_evidence.py"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 1
            stderr_output = mock_stderr.getvalue()
            assert "Error during grading" in stderr_output

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_with_all_answer_types(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
    ):
        """Test that all valid answer types are accepted."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        for answer_type in ["good", "less_good", "wrong"]:
            with patch.object(
                sys,
                "argv",
                ["grade_from_evidence.py", "--answer_type", answer_type],
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    main()

            mock_load_submission.assert_called_with("student_001", "q02", answer_type)

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_main_output_default_path(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
        tmp_path,
        monkeypatch,
    ):
        """Test default output path creation."""
        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        # Change to tmp_path so results/ directory is created there
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, "argv", ["grade_from_evidence.py"]):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        # Default output should be results/student_001_q02_good_grades.json
        expected_path = tmp_path / "results" / "student_001_q02_good_grades.json"
        assert expected_path.exists()


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining CLI with grading functions."""

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_end_to_end_q02_good_answer(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_evidence_json,
        sample_submission_yaml,
        sample_grading_result,
        tmp_path,
        monkeypatch,
    ):
        """Integration test: Grade a good q02 answer end-to-end."""
        monkeypatch.chdir(tmp_path)

        mock_load_evidence.return_value = sample_evidence_json["students"][0]
        mock_load_submission.return_value = sample_submission_yaml
        mock_grade.return_value = sample_grading_result

        with patch.object(
            sys,
            "argv",
            [
                "grade_from_evidence.py",
                "--question", "q02",
                "--student", "student_001",
                "--answer_type", "good",
                "--verbose",
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    main()

        # Check output files created
        results_dir = tmp_path / "results"
        output_file = results_dir / "student_001_q02_good_grades.json"
        assert output_file.exists()

        # Verify file contents
        with open(output_file) as f:
            result = json.load(f)
        assert result["student_id"] == "student_001"
        assert result["total_score"] == 8.5
        assert result["max_score"] == 10

    @patch("grading_dynamic_rubrics.grade_from_evidence.grade_student_with_evidence")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_student_submission")
    @patch("grading_dynamic_rubrics.grade_from_evidence.load_evidence_context")
    def test_end_to_end_different_questions(
        self,
        mock_load_evidence,
        mock_load_submission,
        mock_grade,
        sample_grading_result,
        tmp_path,
        monkeypatch,
    ):
        """Integration test: Grade different questions."""
        monkeypatch.chdir(tmp_path)

        # Test multiple questions
        for question_id in ["q01", "q03", "q05"]:
            evidence_context = {
                "question_id": question_id,
                "question_text": f"Question text for {question_id}",
                "grading_context": [],
            }
            submission = {
                "student_id": "student_001",
                "question_id": question_id,
                "answer": f"Answer for {question_id}",
            }

            mock_load_evidence.return_value = evidence_context
            mock_load_submission.return_value = submission
            mock_grade.return_value = sample_grading_result

            with patch.object(
                sys,
                "argv",
                ["grade_from_evidence.py", "--question", question_id],
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    main()

            # Verify correct calls were made
            mock_load_evidence.assert_called_with(question_id)
