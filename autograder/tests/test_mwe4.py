"""Tests for MWE 4: Full Pipeline Integration."""

import tempfile
from pathlib import Path

import pytest
import yaml

from evidence.build_index import build_index, load_saved_index
from evidence.index_builder import (
    build_index_with_metadata,
    create_documents_with_metadata,
)
from grader.grade_question import (
    apply_rubric_scoring,
    extract_keywords,
    generate_simple_feedback,
    grade_question,
    load_rubric,
    load_submission,
)


def test_load_rubric(tmp_path: Path) -> None:
    """Test loading rubric from YAML file."""
    rubric_data = {
        "question_id": "q01",
        "total_points": 10,
        "criteria": [{"criterion_id": "c1", "points": 5}],
    }

    rubric_file = tmp_path / "rubric.yaml"
    with open(rubric_file, "w") as f:
        yaml.dump(rubric_data, f)

    rubric = load_rubric(rubric_file)

    assert rubric["question_id"] == "q01"
    assert rubric["total_points"] == 10
    assert len(rubric["criteria"]) == 1


def test_load_submission(tmp_path: Path) -> None:
    """Test loading submission from file."""
    submission_text = "This is a student submission."

    submission_file = tmp_path / "submission.txt"
    with open(submission_file, "w") as f:
        f.write(submission_text)

    submission = load_submission(submission_file)

    assert submission == submission_text


def test_extract_keywords() -> None:
    """Test keyword extraction from description."""
    description = "Correctly defines mutual information and entropy"

    keywords = extract_keywords(description)

    # Meta-words (instructional words) should be excluded
    assert "correctly" not in keywords
    assert "defines" not in keywords
    # Only substantive keywords should be included
    assert "mutual" in keywords
    assert "information" in keywords
    assert "entropy" in keywords

    # Stop words should be excluded
    assert "and" not in keywords
    assert "the" not in keywords

    # Test with another example containing meta-words
    description2 = "Explains key properties like non-negative and symmetric"
    keywords2 = extract_keywords(description2)
    assert "explains" not in keywords2
    assert "properties" not in keywords2
    assert "like" not in keywords2
    assert "key" not in keywords2
    assert "non-negative" in keywords2
    assert "symmetric" in keywords2


def test_apply_rubric_scoring() -> None:
    """Test applying rubric scoring."""
    rubric = {
        "criteria": [
            {
                "criterion_id": "c1",
                "description": "Define mutual information",
                "points": 5,
            },
            {
                "criterion_id": "c2",
                "description": "Explain entropy concepts",
                "points": 3,
            },
        ]
    }

    student_answer = "Mutual information measures dependence. Entropy measures uncertainty."

    evidence_by_criterion = {"c1": [{"text": "evidence"}], "c2": [{"text": "evidence"}]}

    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)

    assert "c1" in scores
    assert "c2" in scores
    assert scores["c1"]["max_score"] == 5
    assert scores["c2"]["max_score"] == 3
    
    # Verify keyword tracking is included
    assert "keywords" in scores["c1"]
    assert "found_keywords" in scores["c1"]
    assert "missing_keywords" in scores["c1"]
    assert "mutual" in scores["c1"]["keywords"]
    assert "information" in scores["c1"]["keywords"]
    # "mutual" and "information" should be found in the answer
    assert "mutual" in scores["c1"]["found_keywords"]
    assert "information" in scores["c1"]["found_keywords"]


def test_generate_simple_feedback() -> None:
    """Test generating simple feedback without evidence."""
    rubric = {
        "criteria": [
            {"criterion_id": "c1", "description": "Define concept", "points": 5},
            {"criterion_id": "c2", "description": "Give examples", "points": 3},
        ]
    }

    scores = {"c1": {"score": 4, "max_score": 5}, "c2": {"score": 2, "max_score": 3}}

    feedback = generate_simple_feedback(rubric, scores)

    assert "Define concept" in feedback
    assert "4/5" in feedback
    assert "Give examples" in feedback
    assert "2/3" in feedback


def test_grade_question_without_index(tmp_path: Path) -> None:
    """Test grading without evidence index."""
    # Create rubric
    rubric_data = {
        "question_id": "q01",
        "total_points": 10,
        "criteria": [
            {
                "criterion_id": "definition",
                "description": "Define mutual information",
                "points": 5,
                "evidence_required": False,
            },
            {
                "criterion_id": "examples",
                "description": "Provide examples",
                "points": 5,
                "evidence_required": False,
            },
        ],
    }

    rubric_file = tmp_path / "rubric.yaml"
    with open(rubric_file, "w") as f:
        yaml.dump(rubric_data, f)

    # Create submission
    submission_text = "Mutual information measures statistical dependence between variables."
    submission_file = tmp_path / "submission.txt"
    with open(submission_file, "w") as f:
        f.write(submission_text)

    # Grade without index
    result = grade_question(
        submission_path=submission_file, rubric_path=rubric_file, evidence_index_path=None
    )

    assert result["question_id"] == "q01"
    assert result["max_score"] == 10
    assert "feedback" in result
    assert "rubric_items" in result
    assert len(result["rubric_items"]) == 2


def test_grade_question_with_index(tmp_path: Path) -> None:
    """Test grading with evidence index."""
    # Create sample evidence index
    evidence_texts = [
        "Mutual information measures statistical dependence between variables.",
        "Entropy measures the uncertainty in a random variable.",
    ]

    evidence_sources = [
        {"source_id": "slide_1", "source_type": "slide"},
        {"source_id": "slide_2", "source_type": "slide"},
    ]

    documents = create_documents_with_metadata(evidence_texts, evidence_sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    # Save index
    import pickle

    index_dir = tmp_path / "index"
    index_dir.mkdir()
    index_file = index_dir / "vector_index.pkl"

    with open(index_file, "wb") as f:
        pickle.dump(index, f)

    # Create rubric
    rubric_data = {
        "question_id": "q01",
        "total_points": 10,
        "criteria": [
            {
                "criterion_id": "definition",
                "description": "Define mutual information",
                "points": 5,
                "evidence_required": True,
            },
        ],
    }

    rubric_file = tmp_path / "rubric.yaml"
    with open(rubric_file, "w") as f:
        yaml.dump(rubric_data, f)

    # Create submission
    submission_text = "Mutual information tells us about variable relationships."
    submission_file = tmp_path / "submission.txt"
    with open(submission_file, "w") as f:
        f.write(submission_text)

    # Grade with index
    result = grade_question(
        submission_path=submission_file,
        rubric_path=rubric_file,
        evidence_index_path=index_dir,
    )

    assert result["question_id"] == "q01"
    assert result["max_score"] == 10
    assert "feedback" in result
    assert len(result["rubric_items"]) >= 1


def test_saved_index_loading(tmp_path: Path) -> None:
    """Test saving and loading index."""
    # Create sample index
    evidence_texts = ["Test evidence text."]
    evidence_sources = [{"source_id": "test_1", "source_type": "test"}]

    documents = create_documents_with_metadata(evidence_texts, evidence_sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    # Save index
    import pickle

    index_dir = tmp_path / "index"
    index_dir.mkdir()
    index_file = index_dir / "vector_index.pkl"

    with open(index_file, "wb") as f:
        pickle.dump(index, f)

    # Load index
    loaded_index = load_saved_index(index_dir)

    assert loaded_index is not None

    # Test nonexistent index
    nonexistent_path = tmp_path / "nonexistent"
    loaded_none = load_saved_index(nonexistent_path)
    assert loaded_none is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
