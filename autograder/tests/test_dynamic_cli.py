"""Tests for dynamic rubrics CLI.

Tests command-line interface for dynamic rubrics grading.

"""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml


def test_cli_help() -> None:
    """Test that CLI help works."""
    result = subprocess.run(
        [sys.executable, "-m", "grading_dynamic_rubrics.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "Dynamic Rubrics Grading Pipeline CLI" in result.stdout
    assert "grade-question" in result.stdout
    assert "grade-student" in result.stdout

    print("✓ test_cli_help passed")


def test_cli_grade_question_help() -> None:
    """Test grade-question command help."""
    result = subprocess.run(
        [sys.executable, "-m", "grading_dynamic_rubrics.cli", "grade-question", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "--question" in result.stdout
    assert "--rubrics-config" in result.stdout
    assert "--submissions-dir" in result.stdout
    assert "--sources-config" in result.stdout
    assert "--output" in result.stdout

    # Should NOT have index-dir or index-backend (in-memory only)
    assert "--index-dir" not in result.stdout
    assert "--index-backend" not in result.stdout

    print("✓ test_cli_grade_question_help passed")


def test_cli_grade_student_help() -> None:
    """Test grade-student command help."""
    result = subprocess.run(
        [sys.executable, "-m", "grading_dynamic_rubrics.cli", "grade-student", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "--submission" in result.stdout
    assert "--rubrics-config" in result.stdout
    assert "--sources-config" in result.stdout
    assert "--output" in result.stdout

    # Should NOT have index-dir or index-backend
    assert "--index-dir" not in result.stdout
    assert "--index-backend" not in result.stdout

    print("✓ test_cli_grade_student_help passed")


def test_cli_missing_rubric_error() -> None:
    """Test error handling for missing rubric."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create config without the requested question
        config_path = tmpdir_path / "rubrics.yaml"
        config_data = {
            "rubrics": {
                "q01": {
                    "path": "q01.yaml",
                    "description": "Question 1",
                }
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Create empty submissions dir
        submissions_dir = tmpdir_path / "submissions"
        submissions_dir.mkdir()

        # Create sources config
        sources_config = tmpdir_path / "sources.yaml"
        with open(sources_config, "w") as f:
            yaml.dump({"sources": []}, f)

        # Try to grade non-existent question
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grading_dynamic_rubrics.cli",
                "grade-question",
                "--question",
                "q99",
                "--rubrics-config",
                str(config_path),
                "--submissions-dir",
                str(submissions_dir),
                "--sources-config",
                str(sources_config),
                "--output",
                str(tmpdir_path / "results.json"),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # Should fail with error message
        assert result.returncode == 0  # CLI handles error gracefully
        assert "not found in rubric config" in result.stdout or "Error:" in result.stdout

        print("✓ test_cli_missing_rubric_error passed")


def test_cli_no_command() -> None:
    """Test CLI with no command shows help."""
    result = subprocess.run(
        [sys.executable, "-m", "grading_dynamic_rubrics.cli"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "Dynamic Rubrics Grading Pipeline CLI" in result.stdout

    print("✓ test_cli_no_command passed")


def test_cli_module_import() -> None:
    """Test that CLI module can be imported."""
    try:
        from grading_dynamic_rubrics import cli

        assert hasattr(cli, "main")
        assert hasattr(cli, "grade_question_command")
        assert hasattr(cli, "grade_student_command")

        print("✓ test_cli_module_import passed")
    except ImportError as e:
        pytest.fail(f"Failed to import CLI module: {e}")


if __name__ == "__main__":
    test_cli_help()
    test_cli_grade_question_help()
    test_cli_grade_student_help()
    test_cli_missing_rubric_error()
    test_cli_no_command()
    test_cli_module_import()
    print("\n✓ All dynamic CLI tests passed")
