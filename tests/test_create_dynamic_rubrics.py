"""Comprehensive tests for dynamic rubric generation.

"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest
import yaml
from pydantic import ValidationError

from gp.create_dynamic_rubrics_for_each_question import (
    convert_json_to_rubric_structure,
    extract_json_from_response,
    format_prompt,
    generate_rubric_with_llm,
    load_prompt_template,
    load_source_file,
    parse_questions,
    save_rubric_dual_format,
    slugify,
)
from gp.rubric_schema import RubricJsonResponse


# ============================================================================
# Test prompt template loading
# ============================================================================


def test_load_prompt_template_valid() -> None:
    """Test loading a valid prompt template with placeholders."""
    with TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template.txt"
        template_content = (
            "Question: {QUESTION_TEXT}\n"
            "Source: {SOURCE_FILE_CONTENT}\n"
            "Generate rubric."
        )
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(template_content)

        result = load_prompt_template(template_path)
        assert result == template_content
        assert "{QUESTION_TEXT}" in result
        assert "{SOURCE_FILE_CONTENT}" in result
        print("✓ test_load_prompt_template_valid passed")


def test_load_prompt_template_missing_file() -> None:
    """Test loading a non-existent template file."""
    template_path = Path("/nonexistent/template.txt")
    with pytest.raises(FileNotFoundError):
        load_prompt_template(template_path)
    print("✓ test_load_prompt_template_missing_file passed")


def test_load_prompt_template_missing_placeholder() -> None:
    """Test template missing required placeholders."""
    with TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template.txt"
        template_content = "Question: {QUESTION_TEXT}\nNo source placeholder."
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(template_content)

        with pytest.raises(ValueError, match="missing required placeholder"):
            load_prompt_template(template_path)
        print("✓ test_load_prompt_template_missing_placeholder passed")


# ============================================================================
# Test source file loading
# ============================================================================


def test_load_source_file_text() -> None:
    """Test loading a text file."""
    with TemporaryDirectory() as tmpdir:
        text_file = Path(tmpdir) / "source.txt"
        content = "This is test content for a text file."
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(content)

        result = load_source_file(text_file)
        assert result == content
        print("✓ test_load_source_file_text passed")


def test_load_source_file_markdown() -> None:
    """Test loading a markdown file."""
    with TemporaryDirectory() as tmpdir:
        md_file = Path(tmpdir) / "source.md"
        content = "# Test Markdown\n\nThis is test content."
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(content)

        result = load_source_file(md_file)
        assert result == content
        print("✓ test_load_source_file_markdown passed")


@patch("gp.create_dynamic_rubrics_for_each_question._extract_text_from_pdf")
def test_load_source_file_pdf(mock_extract: Mock) -> None:
    """Test loading a PDF file."""
    mock_extract.return_value = "Extracted PDF content"

    with TemporaryDirectory() as tmpdir:
        pdf_file = Path(tmpdir) / "source.pdf"
        pdf_file.touch()  # Create empty file

        result = load_source_file(pdf_file)
        assert result == "Extracted PDF content"
        mock_extract.assert_called_once_with(pdf_file)
        print("✓ test_load_source_file_pdf passed")


def test_load_source_file_missing() -> None:
    """Test loading a non-existent source file."""
    source_path = Path("/nonexistent/source.txt")
    with pytest.raises(FileNotFoundError):
        load_source_file(source_path)
    print("✓ test_load_source_file_missing passed")


def test_load_source_file_unsupported_type() -> None:
    """Test loading an unsupported file type."""
    with TemporaryDirectory() as tmpdir:
        unsupported_file = Path(tmpdir) / "source.doc"
        unsupported_file.touch()

        with pytest.raises(ValueError, match="Unsupported file type"):
            load_source_file(unsupported_file)
        print("✓ test_load_source_file_unsupported_type passed")


# ============================================================================
# Test prompt formatting
# ============================================================================


def test_format_prompt() -> None:
    """Test formatting prompt with question and source content."""
    template = "Question: {QUESTION_TEXT}\nSource: {SOURCE_FILE_CONTENT}"
    question = "What is an object?"
    source = "Objects are entities in a table."

    result = format_prompt(template, question, source)
    assert "{QUESTION_TEXT}" not in result
    assert "{SOURCE_FILE_CONTENT}" not in result
    assert question in result
    assert source in result
    print("✓ test_format_prompt passed")


def test_format_prompt_long_content() -> None:
    """Test formatting with long source content."""
    template = "Q: {QUESTION_TEXT}\nS: {SOURCE_FILE_CONTENT}"
    question = "Short question"
    source = "A" * 10000  # Very long content

    result = format_prompt(template, question, source)
    assert len(result) > 10000
    assert source in result
    print("✓ test_format_prompt_long_content passed")


# ============================================================================
# Test JSON extraction
# ============================================================================


def test_extract_json_from_response_plain() -> None:
    """Test extracting JSON from plain response."""
    response = '{"dimensions": [{"title": "Test", "points": 10, "description": "Desc"}], "total_points": 10}'
    result = extract_json_from_response(response)
    # Parse to verify it's valid JSON
    parsed = json.loads(result)
    assert "dimensions" in parsed
    print("✓ test_extract_json_from_response_plain passed")


def test_extract_json_from_response_markdown() -> None:
    """Test extracting JSON from markdown code block."""
    response = "Here is the rubric:\n```json\n{\"dimensions\": []}\n```"
    result = extract_json_from_response(response)
    assert result == '{"dimensions": []}'
    print("✓ test_extract_json_from_response_markdown passed")


def test_extract_json_from_response_no_json() -> None:
    """Test extracting JSON when none exists."""
    response = "This is just text with no JSON."
    with pytest.raises(ValueError, match="No JSON found"):
        extract_json_from_response(response)
    print("✓ test_extract_json_from_response_no_json passed")


# ============================================================================
# Test JSON validation
# ============================================================================


def test_rubric_schema_valid() -> None:
    """Test validating a valid rubric JSON structure."""
    valid_data = {
        "dimensions": [
            {"title": "Correctness", "points": 6, "description": "Correct answer"},
            {"title": "Completeness", "points": 4, "description": "Complete answer"},
        ],
        "total_points": 10,
    }
    rubric = RubricJsonResponse.model_validate(valid_data)
    assert len(rubric.dimensions) == 2
    assert rubric.total_points == 10
    print("✓ test_rubric_schema_valid passed")


def test_rubric_schema_wrong_points() -> None:
    """Test validation fails when points don't sum to 10."""
    invalid_data = {
        "dimensions": [
            {"title": "One", "points": 5, "description": "Desc"},
            {"title": "Two", "points": 4, "description": "Desc"},
        ],
        "total_points": 10,
    }
    with pytest.raises(ValidationError):
        RubricJsonResponse.model_validate(invalid_data)
    print("✓ test_rubric_schema_wrong_points passed")


def test_rubric_schema_too_few_dimensions() -> None:
    """Test validation fails with too few dimensions."""
    invalid_data = {
        "dimensions": [{"title": "One", "points": 10, "description": "Desc"}],
        "total_points": 10,
    }
    with pytest.raises(ValidationError):
        RubricJsonResponse.model_validate(invalid_data)
    print("✓ test_rubric_schema_too_few_dimensions passed")


def test_rubric_schema_too_many_dimensions() -> None:
    """Test validation fails with too many dimensions."""
    invalid_data = {
        "dimensions": [
            {"title": f"Dim{i}", "points": 1, "description": "Desc"}
            for i in range(6)
        ],
        "total_points": 10,
    }
    with pytest.raises(ValidationError):
        RubricJsonResponse.model_validate(invalid_data)
    print("✓ test_rubric_schema_too_many_dimensions passed")


# ============================================================================
# Test retry logic
# ============================================================================


def test_generate_rubric_with_llm_success() -> None:
    """Test successful LLM generation on first attempt."""
    mock_llm = Mock()
    valid_json = {
        "dimensions": [
            {"title": "Test1", "points": 6, "description": "Test desc 1"},
            {"title": "Test2", "points": 4, "description": "Test desc 2"},
        ],
        "total_points": 10,
    }
    mock_response = Mock()
    mock_response.text = json.dumps(valid_json)
    # Mock needs to return same response each time (prompt gets modified)
    mock_llm.complete.return_value = mock_response

    prompt = "Generate rubric"
    result = generate_rubric_with_llm(prompt, mock_llm, max_retries=3)

    assert result["total_points"] == 10
    assert len(result["dimensions"]) == 2
    mock_llm.complete.assert_called()
    print("✓ test_generate_rubric_with_llm_success passed")


def test_generate_rubric_with_llm_retry_success() -> None:
    """Test LLM generation succeeds after retry."""
    mock_llm = Mock()
    invalid_json = '{"invalid": "structure"}'
    valid_json = {
        "dimensions": [
            {"title": "Test1", "points": 6, "description": "Test desc 1"},
            {"title": "Test2", "points": 4, "description": "Test desc 2"},
        ],
        "total_points": 10,
    }

    # First call fails, subsequent calls succeed
    mock_response1 = Mock()
    mock_response1.text = invalid_json
    mock_response2 = Mock()
    mock_response2.text = json.dumps(valid_json)
    # Use return_value after side_effect is exhausted
    mock_llm.complete.side_effect = [mock_response1, mock_response2, mock_response2]

    prompt = "Generate rubric"
    result = generate_rubric_with_llm(prompt, mock_llm, max_retries=3, verbose=False)

    assert result["total_points"] == 10
    assert len(result["dimensions"]) == 2
    assert mock_llm.complete.call_count == 2
    print("✓ test_generate_rubric_with_llm_retry_success passed")


def test_generate_rubric_with_llm_max_retries_exceeded() -> None:
    """Test LLM generation fails after max retries."""
    mock_llm = Mock()
    invalid_json = '{"invalid": "structure"}'
    mock_response = Mock()
    mock_response.text = invalid_json
    mock_llm.complete.return_value = mock_response

    prompt = "Generate rubric"
    with pytest.raises(ValueError, match="Failed to generate valid rubric"):
        generate_rubric_with_llm(prompt, mock_llm, max_retries=3)

    assert mock_llm.complete.call_count == 3
    print("✓ test_generate_rubric_with_llm_max_retries_exceeded passed")


# ============================================================================
# Test rubric conversion
# ============================================================================


def test_convert_json_to_rubric_structure() -> None:
    """Test converting JSON to rubric structure."""
    json_rubric = {
        "dimensions": [
            {
                "title": "Correctness",
                "points": 6,
                "description": "Answer is correct",
            },
            {
                "title": "Completeness",
                "points": 4,
                "description": "Answer is complete",
            },
        ],
        "total_points": 10,
    }

    result = convert_json_to_rubric_structure(
        json_rubric, "q03", "What is an object?"
    )

    assert result["question_id"] == "q03"
    assert result["total_points"] == 10
    assert len(result["criteria"]) == 2
    assert result["criteria"][0]["criterion_id"] == "correctness"
    assert result["criteria"][0]["points"] == 6
    assert result["criteria"][1]["criterion_id"] == "completeness"
    assert result["criteria"][1]["points"] == 4
    assert "scoring_weights" in result
    assert result["metadata"]["generated_by"] == "llm"
    print("✓ test_convert_json_to_rubric_structure passed")


def test_slugify() -> None:
    """Test slugification of criterion IDs."""
    assert slugify("Correctness & Accuracy") == "correctness_accuracy"
    assert slugify("Test-Criterion") == "test_criterion"
    assert slugify("Simple Title") == "simple_title"
    assert slugify("Multiple   Spaces") == "multiple_spaces"
    print("✓ test_slugify passed")


# ============================================================================
# Test dual format saving
# ============================================================================


def test_save_rubric_dual_format() -> None:
    """Test saving rubric in both JSON and YAML formats."""
    with TemporaryDirectory() as tmpdir:
        rubrics_dir = Path(tmpdir) / "rubrics"
        rubric_dict = {
            "question_id": "q03",
            "question_text": "Test question",
            "total_points": 10,
            "criteria": [{"criterion_id": "test", "points": 10}],
        }
        rubric_json = {
            "dimensions": [{"title": "Test", "points": 10, "description": "Desc"}],
            "total_points": 10,
        }

        save_rubric_dual_format(rubric_dict, rubric_json, "q03", rubrics_dir)

        # Check JSON file
        json_file = rubrics_dir / "json" / "q03.json"
        assert json_file.exists()
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        assert "llm_output" in json_data
        assert "converted_rubric" in json_data

        # Check YAML file
        yaml_file = rubrics_dir / "yaml" / "q03.yaml"
        assert yaml_file.exists()
        with open(yaml_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        assert yaml_data["question_id"] == "q03"
        print("✓ test_save_rubric_dual_format passed")


# ============================================================================
# Test question parsing
# ============================================================================


def test_parse_questions() -> None:
    """Test parsing questions from markdown file."""
    with TemporaryDirectory() as tmpdir:
        questions_file = Path(tmpdir) / "questions.md"
        content = """1. First question text here.
This continues on multiple lines.

2. Second question text.
More text for question 2.

3. Third question."""
        with open(questions_file, "w", encoding="utf-8") as f:
            f.write(content)

        result = parse_questions(questions_file)
        assert len(result) == 3
        assert result[0]["question_id"] == "q01"
        assert "First question" in result[0]["question_text"]
        assert result[1]["question_id"] == "q02"
        assert result[2]["question_id"] == "q03"
        print("✓ test_parse_questions passed")


# ============================================================================
# Integration test
# ============================================================================


@patch("gp.create_dynamic_rubrics_for_each_question.configure_llm")
@patch("gp.create_dynamic_rubrics_for_each_question.load_env_config")
def test_integration_end_to_end(
    mock_config: Mock, mock_llm_config: Mock
) -> None:
    """Test end-to-end integration with mock LLM."""
    with TemporaryDirectory() as tmpdir:
        # Setup test files
        questions_file = Path(tmpdir) / "questions.md"
        with open(questions_file, "w", encoding="utf-8") as f:
            f.write("3. Test question about objects?")

        source_file = Path(tmpdir) / "source.txt"
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("Objects are entities in tables.")

        template_file = Path(tmpdir) / "template.txt"
        with open(template_file, "w", encoding="utf-8") as f:
            f.write("Q: {QUESTION_TEXT}\nS: {SOURCE_FILE_CONTENT}")

        rubrics_dir = Path(tmpdir) / "rubrics"

        # Mock LLM
        mock_llm = Mock()
        valid_json = {
            "dimensions": [
                {"title": "Test1", "points": 6, "description": "Test desc 1"},
                {"title": "Test2", "points": 4, "description": "Test desc 2"},
            ],
            "total_points": 10,
        }
        mock_response = Mock()
        mock_response.text = json.dumps(valid_json)
        mock_llm.complete.return_value = mock_response
        mock_llm_config.return_value = mock_llm
        mock_config.return_value = {
            "lmql_backend": "ollama",
            "lmql_model": "gpt-oss:20b",
        }

        # Import and run main components
        from gp.create_dynamic_rubrics_for_each_question import (
            format_prompt,
            generate_rubric_with_llm,
            load_prompt_template,
            load_source_file,
            parse_questions,
        )

        # Load files
        template = load_prompt_template(template_file)
        source_content = load_source_file(source_file)
        questions = parse_questions(questions_file)

        # Generate rubric
        question = questions[0]
        prompt = format_prompt(template, question["question_text"], source_content)
        rubric_json = generate_rubric_with_llm(prompt, mock_llm)
        rubric_dict = convert_json_to_rubric_structure(
            rubric_json, question["question_id"], question["question_text"]
        )

        # Save
        save_rubric_dual_format(
            rubric_dict, rubric_json, question["question_id"], rubrics_dir
        )

        # Verify output
        json_file = rubrics_dir / "json" / "q03.json"
        yaml_file = rubrics_dir / "yaml" / "q03.yaml"
        assert json_file.exists()
        assert yaml_file.exists()

        with open(yaml_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        assert yaml_data["question_id"] == "q03"
        print("✓ test_integration_end_to_end passed")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
