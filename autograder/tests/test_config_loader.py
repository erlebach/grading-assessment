"""Tests for config_loader module."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from grading_pipeline.config_loader import get_rubric_path, load_rubric_config


def test_load_rubric_config_valid() -> None:
    """Test loading a valid rubric config."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
        config_data = {
            "rubrics": {
                "q01": {
                    "path": "rubrics/q01.yaml",
                    "description": "Question 1",
                },
                "q02": {
                    "path": "rubrics/q02.yaml",
                    "description": "Question 2",
                },
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        result = load_rubric_config(config_path)
        assert len(result) == 2
        assert "q01" in result
        assert "q02" in result
        assert result["q01"]["path"] == "rubrics/q01.yaml"
        assert result["q01"]["description"] == "Question 1"
        print("✓ test_load_rubric_config_valid passed")


def test_load_rubric_config_missing_file() -> None:
    """Test loading a non-existent config file."""
    config_path = Path("/nonexistent/rubrics.yaml")
    with pytest.raises(FileNotFoundError):
        load_rubric_config(config_path)
    print("✓ test_load_rubric_config_missing_file passed")


def test_load_rubric_config_invalid_structure() -> None:
    """Test loading an invalid config structure."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
        # Missing 'rubrics' key
        config_data = {"other_key": "value"}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError, match="missing 'rubrics' key"):
            load_rubric_config(config_path)
    print("✓ test_load_rubric_config_invalid_structure passed")


def test_get_rubric_path_valid() -> None:
    """Test getting rubric path for a valid question ID."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
        rubric_file = Path(tmpdir) / "q01.yaml"
        rubric_file.write_text("question_id: q01\n")

        config_data = {
            "rubrics": {
                "q01": {
                    "path": str(rubric_file),
                    "description": "Question 1",
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        result = get_rubric_path("q01", config_path)
        assert result == rubric_file
        print("✓ test_get_rubric_path_valid passed")


def test_get_rubric_path_relative() -> None:
    """Test getting rubric path with relative path resolution."""
    with TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()
        config_path = config_dir / "rubrics.yaml"

        rubric_dir = Path(tmpdir) / "rubrics"
        rubric_dir.mkdir()
        rubric_file = rubric_dir / "q01.yaml"
        rubric_file.write_text("question_id: q01\n")

        config_data = {
            "rubrics": {
                "q01": {
                    "path": "../rubrics/q01.yaml",  # Relative to config dir
                    "description": "Question 1",
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        result = get_rubric_path("q01", config_path)
        assert result.exists()
        assert result.name == "q01.yaml"
        print("✓ test_get_rubric_path_relative passed")


def test_get_rubric_path_invalid_question() -> None:
    """Test getting rubric path for invalid question ID."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
        config_data = {
            "rubrics": {
                "q01": {
                    "path": "rubrics/q01.yaml",
                    "description": "Question 1",
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError, match="not found in rubric config"):
            get_rubric_path("q99", config_path)
    print("✓ test_get_rubric_path_invalid_question passed")


if __name__ == "__main__":
    test_load_rubric_config_valid()
    test_load_rubric_config_missing_file()
    test_load_rubric_config_invalid_structure()
    test_get_rubric_path_valid()
    test_get_rubric_path_relative()
    test_get_rubric_path_invalid_question()
    print("\n✓ All config_loader tests passed")
