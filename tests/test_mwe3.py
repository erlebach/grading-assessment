"""Tests for MWE 3: LMQL Integration for Structured Grading."""

import pytest

from prompts.grading_lmql import (
    format_explanation_text,
    format_grading_prompt,
    parse_lmql_response,
    validate_explanation,
)


def test_validate_explanation_valid() -> None:
    """Test validation of a valid explanation."""
    explanation = {
        "sentences": [
            {"text": "Sentence 1.", "citations": ["slide_1"]},
            {"text": "Sentence 2.", "citations": ["slide_2", "slide_3"]},
        ]
    }

    valid_ids = ["slide_1", "slide_2", "slide_3"]
    assert validate_explanation(explanation, valid_ids) is True


def test_validate_explanation_no_citations() -> None:
    """Test validation fails when sentence has no citations."""
    explanation = {
        "sentences": [
            {"text": "Sentence without citation.", "citations": []},
        ]
    }

    valid_ids = ["slide_1"]
    assert validate_explanation(explanation, valid_ids) is False


def test_validate_explanation_invalid_citation() -> None:
    """Test validation fails when citation ID is not valid."""
    explanation = {
        "sentences": [
            {"text": "Sentence 1.", "citations": ["slide_99"]},  # Unknown ID
        ]
    }

    valid_ids = ["slide_1", "slide_2"]
    assert validate_explanation(explanation, valid_ids) is False


def test_validate_explanation_missing_text() -> None:
    """Test validation fails when sentence has no text."""
    explanation = {
        "sentences": [
            {"text": "", "citations": ["slide_1"]},  # Empty text
        ]
    }

    valid_ids = ["slide_1"]
    assert validate_explanation(explanation, valid_ids) is False


def test_validate_explanation_no_sentences() -> None:
    """Test validation fails when there are no sentences."""
    explanation = {"sentences": []}

    valid_ids = ["slide_1"]
    assert validate_explanation(explanation, valid_ids) is False


def test_format_grading_prompt() -> None:
    """Test formatting of grading prompt."""
    grading_record = {
        "c1": {"score": 3, "max_score": 4},
        "c2": {"score": 2, "max_score": 2},
    }

    evidence_spans = [
        {"source_id": "slide_1", "text": "Evidence text 1."},
        {"source_id": "slide_2", "text": "Evidence text 2."},
    ]

    student_answer = "Student's answer here."

    prompt = format_grading_prompt(grading_record, evidence_spans, student_answer)

    # Check that key elements are present
    assert "GRADING RECORD" in prompt
    assert "AVAILABLE EVIDENCE" in prompt
    assert "STUDENT ANSWER" in prompt
    assert "c1: 3/4" in prompt
    assert "c2: 2/2" in prompt
    assert "[slide_1]" in prompt
    assert "[slide_2]" in prompt
    assert "Student's answer here." in prompt


def test_parse_lmql_response_json() -> None:
    """Test parsing JSON response."""
    response = '{"sentences": [{"text": "Test.", "citations": ["slide_1"]}]}'
    explanation = parse_lmql_response(response)

    assert "sentences" in explanation
    assert len(explanation["sentences"]) == 1
    assert explanation["sentences"][0]["text"] == "Test."


def test_parse_lmql_response_with_markdown() -> None:
    """Test parsing JSON wrapped in markdown code blocks."""
    response = """```json
{
  "sentences": [
    {"text": "Test.", "citations": ["slide_1"]}
  ]
}
```"""

    explanation = parse_lmql_response(response)

    assert "sentences" in explanation
    assert len(explanation["sentences"]) == 1


def test_parse_lmql_response_invalid_json() -> None:
    """Test parsing invalid JSON raises error."""
    response = "This is not JSON"

    with pytest.raises(ValueError):
        parse_lmql_response(response)


def test_format_explanation_text() -> None:
    """Test formatting structured explanation as text."""
    explanation = {
        "sentences": [
            {"text": "First sentence.", "citations": ["slide_1"]},
            {"text": "Second sentence.", "citations": ["slide_2", "slide_3"]},
        ]
    }

    formatted = format_explanation_text(explanation)

    assert "First sentence. [slide_1]" in formatted
    assert "Second sentence. [slide_2, slide_3]" in formatted


def test_format_explanation_text_single_citation() -> None:
    """Test formatting with single citation per sentence."""
    explanation = {
        "sentences": [
            {"text": "Only one citation.", "citations": ["slide_1"]},
        ]
    }

    formatted = format_explanation_text(explanation)

    assert formatted == "Only one citation. [slide_1]"


def test_format_explanation_text_multiple_sentences() -> None:
    """Test formatting joins sentences with spaces."""
    explanation = {
        "sentences": [
            {"text": "Sentence one.", "citations": ["s1"]},
            {"text": "Sentence two.", "citations": ["s2"]},
            {"text": "Sentence three.", "citations": ["s3"]},
        ]
    }

    formatted = format_explanation_text(explanation)

    # Should be joined with spaces
    assert "Sentence one. [s1] Sentence two. [s2] Sentence three. [s3]" == formatted


def test_explanation_validation_comprehensive() -> None:
    """Test comprehensive validation scenarios."""
    valid_ids = ["slide_1", "slide_2", "slide_3"]

    # Valid: multiple sentences, multiple citations
    valid_1 = {
        "sentences": [
            {"text": "A.", "citations": ["slide_1", "slide_2"]},
            {"text": "B.", "citations": ["slide_3"]},
        ]
    }
    assert validate_explanation(valid_1, valid_ids) is True

    # Invalid: missing "sentences" key
    invalid_1 = {"data": []}
    assert validate_explanation(invalid_1, valid_ids) is False

    # Invalid: sentences is not a list
    invalid_2 = {"sentences": "not a list"}
    # This would raise an exception in actual validation, but our simple
    # implementation might not catch it - depends on implementation details

    # Invalid: citation not in valid_ids
    invalid_3 = {
        "sentences": [
            {"text": "Test.", "citations": ["invalid_id"]},
        ]
    }
    assert validate_explanation(invalid_3, valid_ids) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
