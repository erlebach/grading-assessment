"""Tests for rubric application and grading logic."""

from pathlib import Path

from grader.aggregate import aggregate_scores
from grader.grade_question import load_rubric, load_submission
from grader.cite import generate_citation, format_citation


def test_load_rubric() -> None:
    """Test loading a rubric from YAML file."""
    rubric_path = Path(__file__).parent.parent / "rubrics" / "q01.yaml"
    rubric = load_rubric(rubric_path)
    
    assert "question_id" in rubric
    assert rubric["question_id"] == "q01"
    assert "total_points" in rubric
    assert "criteria" in rubric
    assert isinstance(rubric["criteria"], list)
    print("✓ load_rubric test passed")


def test_load_submission() -> None:
    """Test loading a submission file."""
    # Create a temporary submission file for testing
    test_submission = Path(__file__).parent / "test_submission.py"
    test_submission.write_text("def factorial(n):\n    return 1\n")
    
    submission = load_submission(test_submission)
    assert isinstance(submission, str)
    assert "factorial" in submission
    
    # Clean up
    test_submission.unlink()
    print("✓ load_submission test passed")


def test_aggregate_scores() -> None:
    """Test score aggregation across multiple questions."""
    question_results = [
        {"score": 7.0, "max_score": 10.0},
        {"score": 8.0, "max_score": 10.0},
    ]
    
    aggregated = aggregate_scores(question_results)
    
    assert aggregated["total_score"] == 15.0
    assert aggregated["total_max_score"] == 20.0
    assert aggregated["percentage"] == 75.0
    assert aggregated["question_count"] == 2
    print("✓ aggregate_scores test passed")


def test_generate_citation() -> None:
    """Test citation generation."""
    citation = generate_citation(
        evidence_text="The function correctly implements factorial",
        source="submission.py",
        location="lines 5-10",
    )
    
    assert citation["text"] == "The function correctly implements factorial"
    assert citation["source"] == "submission.py"
    assert citation["location"] == "lines 5-10"
    print("✓ generate_citation test passed")


def test_format_citation() -> None:
    """Test citation formatting."""
    citation = {
        "text": "Evidence text",
        "source": "submission.py",
        "location": "lines 5-10",
    }
    
    formatted = format_citation(citation)
    assert "submission.py" in formatted
    assert "lines 5-10" in formatted
    print("✓ format_citation test passed")


if __name__ == "__main__":
    test_load_rubric()
    test_load_submission()
    test_aggregate_scores()
    test_generate_citation()
    test_format_citation()
    print("\nAll tests passed!")
