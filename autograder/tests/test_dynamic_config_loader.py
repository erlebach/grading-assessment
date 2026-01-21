"""Tests for dynamic rubrics config loader.

Tests loading and validating dynamic rubric configurations.

"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from grading_dynamic_rubrics.config_loader import get_rubric_path, load_rubric_config


def test_load_rubric_config_valid() -> None:
    """Test loading valid dynamic rubric config."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
        config_data = {
            "rubrics": {
                "q01": {
                    "path": "../../rubrics_dynamic/yaml/q01.yaml",
                    "description": "Question 1",
                },
                "q02": {
                    "path": "../../rubrics_dynamic/yaml/q02.yaml",
                    "description": "Question 2",
                },
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_rubric_config(config_path)

        assert "q01" in config
        assert "q02" in config
        assert config["q01"]["path"] == "../../rubrics_dynamic/yaml/q01.yaml"
        assert config["q02"]["description"] == "Question 2"

        print("✓ test_load_rubric_config_valid passed")


def test_load_rubric_config_missing_file() -> None:
    """Test loading config from non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_rubric_config(Path("/nonexistent/rubrics.yaml"))

    print("✓ test_load_rubric_config_missing_file passed")


def test_load_rubric_config_invalid_format() -> None:
    """Test loading config with invalid format."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"

        # Missing 'rubrics' key
        with open(config_path, "w") as f:
            yaml.dump({"questions": {}}, f)

        with pytest.raises(ValueError, match="missing 'rubrics' key"):
            load_rubric_config(config_path)

        print("✓ test_load_rubric_config_invalid_format passed")


def test_get_rubric_path_valid() -> None:
    """Test getting rubric path for valid question."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
        rubric_path = Path(tmpdir) / "q01.yaml"

        # Create rubric file
        with open(rubric_path, "w") as f:
            yaml.dump({"question_id": "q01"}, f)

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

        result = get_rubric_path("q01", config_path)

        assert result == rubric_path
        assert result.exists()

        print("✓ test_get_rubric_path_valid passed")


def test_get_rubric_path_missing_question() -> None:
    """Test getting rubric path for non-existent question."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "rubrics.yaml"
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

        with pytest.raises(ValueError, match="not found in rubric config"):
            get_rubric_path("q99", config_path)

        print("✓ test_get_rubric_path_missing_question passed")


def test_dynamic_rubric_structure() -> None:
    """Test that dynamic rubrics have expected structure."""
    # Test with actual dynamic rubric if it exists
    rubric_path = (
        Path(__file__).parent.parent / "rubrics_dynamic" / "yaml" / "q01.yaml"
    )

    if rubric_path.exists():
        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)

        # Check dynamic rubric fields
        assert "question_id" in rubric
        assert "total_points" in rubric
        assert "criteria" in rubric
        assert "scoring_weights" in rubric  # Dynamic rubric specific
        assert "semantic_decay" in rubric  # Dynamic rubric specific
        assert "semantic_top_k" in rubric  # Dynamic rubric specific

        # Check criteria structure
        for criterion in rubric["criteria"]:
            assert "criterion_id" in criterion
            assert "description" in criterion
            assert "points" in criterion
            assert "evidence_required" in criterion
            assert "evaluation_method" in criterion

        print("✓ test_dynamic_rubric_structure passed")
    else:
        print("⚠ Skipping test_dynamic_rubric_structure (rubric file not found)")


if __name__ == "__main__":
    test_load_rubric_config_valid()
    test_load_rubric_config_missing_file()
    test_load_rubric_config_invalid_format()
    test_get_rubric_path_valid()
    test_get_rubric_path_missing_question()
    test_dynamic_rubric_structure()
    print("\n✓ All dynamic config loader tests passed")
