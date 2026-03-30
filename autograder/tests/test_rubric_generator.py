"""Tests for grading_pipeline/rubric_generator.py (T2.5).

All tests derived from T2.5 specification in TASK_LIST.md:
  - All steps execute in correct order
  - Intermediate artifacts stored
  - Final rubric is clean (no dupes, all categorized)
  - Error handling graceful (logs + continues)
  - Reproducible (same input → same output)

Tests use a mock LLM so no running Ollama instance is required.
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grading_pipeline.models import Check, CheckCategory, Rubric
from grading_pipeline.rubric_generator import GenerationResult, generate_complete_rubric


# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------

VALID_RUBRIC_JSON = json.dumps({
    "dimensions": [
        {
            "title": "Concept definition",
            "category": "semantic",
            "points": 5,
            "checks": [
                {"text": "Student defines 'object' correctly.", "weight": 2.5},
                {"text": "Student defines 'attribute' correctly.", "weight": 2.5},
            ],
        },
        {
            "title": "Application",
            "category": "application",
            "points": 5,
            "checks": [
                {"text": "Student provides a concrete example.", "weight": 2.5},
                {"text": "Example correctly illustrates the concept.", "weight": 2.5},
            ],
        },
    ],
    "total_points": 10,
})


def _make_llm(response_text: str) -> MagicMock:
    """Return a mock LLM whose .complete() returns response_text."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_llm.complete.return_value = mock_response
    return mock_llm


# ---------------------------------------------------------------------------
# GenerationResult dataclass smoke test
# ---------------------------------------------------------------------------

def _dummy_result(rubric: Rubric, dupes_removed: int = 0) -> GenerationResult:
    from grading_pipeline.deduplication import DeduplicationResult
    dedup = DeduplicationResult(rubric=rubric, duplicates_removed=dupes_removed)
    return GenerationResult(
        rubric=rubric,
        question_id="q01",
        version=1,
        raw_llm_response="raw",
        rubric_after_extraction=rubric,
        rubric_after_categorization=rubric,
        deduplication_result=dedup,
    )


def test_generation_result_properties():
    rubric = Rubric(
        id="q01_rubric",
        question_id="q01",
        title="Test Rubric",
        description="Test description",
        checks=[
            Check(id="q01_c1", text="A", category=CheckCategory.SEMANTIC, weight=1.0, question_id="q01"),
            Check(id="q01_c2", text="B", category=CheckCategory.APPLICATION, weight=1.0, question_id="q01"),
        ],
    )
    result = _dummy_result(rubric, dupes_removed=1)
    assert result.checks_removed == 1
    assert result.final_check_count == 2


# ---------------------------------------------------------------------------
# Happy path: full pipeline
# ---------------------------------------------------------------------------

def test_generate_complete_rubric_basic(tmp_path):
    """All steps run; returns GenerationResult with expected checks."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    result = generate_complete_rubric(
        question_id="q01",
        question_text="What is an object in OOP?",
        source_content="An object is an instance of a class...",
        llm=llm,
        output_dir=tmp_path,
    )

    assert isinstance(result, GenerationResult)
    assert result.question_id == "q01"
    assert result.version == 1
    assert len(result.rubric.checks) > 0
    assert isinstance(result.rubric, Rubric)


def test_pipeline_steps_order(tmp_path):
    """Rubrics after each step exist and are internally consistent."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    result = generate_complete_rubric(
        question_id="q01",
        question_text="Question text",
        source_content="Source text",
        llm=llm,
        output_dir=tmp_path,
    )

    # All intermediate rubrics are Rubric instances
    assert isinstance(result.rubric_after_extraction, Rubric)
    assert isinstance(result.rubric_after_categorization, Rubric)
    assert isinstance(result.deduplication_result.rubric, Rubric)

    # Extraction populates checks
    assert len(result.rubric_after_extraction.checks) >= 1

    # Final rubric is the dedup result
    assert result.rubric is result.deduplication_result.rubric


def test_all_checks_have_valid_categories(tmp_path):
    """All checks in the final rubric have a valid CheckCategory."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    result = generate_complete_rubric(
        question_id="q01",
        question_text="Q",
        source_content="S",
        llm=llm,
        output_dir=tmp_path,
    )

    valid_cats = {c for c in CheckCategory}
    for check in result.rubric.checks:
        assert check.category in valid_cats, f"Invalid category: {check.category}"


# ---------------------------------------------------------------------------
# Artifact storage
# ---------------------------------------------------------------------------

def test_artifacts_stored(tmp_path):
    """All four intermediate artifact files are written to disk."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    result = generate_complete_rubric(
        question_id="q01",
        question_text="Q",
        source_content="S",
        llm=llm,
        output_dir=tmp_path,
    )

    assert result.artifacts_dir is not None
    expected = [
        "01_raw_llm_response.txt",
        "02_extracted.json",
        "03_categorized.json",
        "04_deduplicated.json",
        "04_dedup_metadata.json",
    ]
    for filename in expected:
        p = result.artifacts_dir / filename
        assert p.exists(), f"Missing artifact: {filename}"


def test_artifact_content_parseable(tmp_path):
    """JSON artifacts are valid JSON."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    result = generate_complete_rubric(
        question_id="q01",
        question_text="Q",
        source_content="S",
        llm=llm,
        output_dir=tmp_path,
    )

    for fname in ["02_extracted.json", "03_categorized.json", "04_deduplicated.json", "04_dedup_metadata.json"]:
        content = (result.artifacts_dir / fname).read_text()
        parsed = json.loads(content)
        assert parsed  # not empty


def test_version_in_artifact_path(tmp_path):
    """Artifact directory includes version prefix."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    result = generate_complete_rubric(
        question_id="q02",
        question_text="Q",
        source_content="S",
        llm=llm,
        output_dir=tmp_path,
        version=3,
    )

    assert result.artifacts_dir is not None
    assert "v3" in str(result.artifacts_dir)


# ---------------------------------------------------------------------------
# Deduplication integration
# ---------------------------------------------------------------------------

def test_duplicates_detected_and_removed(tmp_path):
    """Duplicate checks reported in GenerationResult."""
    # Build JSON with two identical checks across dimensions
    json_with_dup = json.dumps({
        "dimensions": [
            {
                "title": "D1",
                "category": "semantic",
                "points": 5,
                "checks": [{"text": "Student correctly defines an object.", "weight": 2.5},
                            {"text": "Student correctly defines an attribute.", "weight": 2.5}],
            },
            {
                "title": "D2",
                "category": "application",
                "points": 5,
                "checks": [{"text": "Student correctly defines an object.", "weight": 5.0}],
            },
        ],
        "total_points": 10,
    })

    # Use exact-match similarity to guarantee deduplication triggers
    def exact_similarity(a: str, b: str) -> float:
        return 1.0 if a.strip() == b.strip() else 0.0

    llm = _make_llm(json_with_dup)
    result = generate_complete_rubric(
        question_id="q01",
        question_text="Q",
        source_content="S",
        llm=llm,
        output_dir=tmp_path,
        similarity_fn=exact_similarity,
        dedup_threshold=0.9,
    )

    assert result.checks_removed >= 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_llm_retry_on_empty_response(tmp_path):
    """LLM is retried when it returns an empty response."""
    mock_llm = MagicMock()
    empty_resp = MagicMock()
    empty_resp.text = ""
    valid_resp = MagicMock()
    valid_resp.text = VALID_RUBRIC_JSON
    mock_llm.complete.side_effect = [empty_resp, valid_resp]

    result = generate_complete_rubric(
        question_id="q01",
        question_text="Q",
        source_content="S",
        llm=mock_llm,
        output_dir=tmp_path,
        max_retries=3,
    )

    assert len(result.rubric.checks) > 0
    assert mock_llm.complete.call_count == 2


def test_llm_all_retries_fail_raises(tmp_path):
    """ValueError raised when all LLM retries fail."""
    mock_llm = MagicMock()
    bad_resp = MagicMock()
    bad_resp.text = ""
    mock_llm.complete.return_value = bad_resp

    with pytest.raises(ValueError, match="failed after"):
        generate_complete_rubric(
            question_id="q01",
            question_text="Q",
            source_content="S",
            llm=mock_llm,
            output_dir=tmp_path,
            max_retries=2,
        )


def test_artifact_failure_does_not_raise(tmp_path):
    """If artifact saving fails, function still returns the rubric."""
    llm = _make_llm(VALID_RUBRIC_JSON)

    # Pass a path that is actually a file (so mkdir will fail)
    blocker = tmp_path / "blocker"
    blocker.write_text("I am a file, not a directory")

    result = generate_complete_rubric(
        question_id="q01",
        question_text="Q",
        source_content="S",
        llm=llm,
        output_dir=blocker / "subdir",  # can't mkdir through a file
    )

    # Rubric still returned despite save failure
    assert isinstance(result.rubric, Rubric)
    assert result.artifacts_dir is None
    assert any("Could not save" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

def test_same_input_same_output(tmp_path):
    """Same LLM response → same final checks (deterministic pipeline)."""
    llm1 = _make_llm(VALID_RUBRIC_JSON)
    llm2 = _make_llm(VALID_RUBRIC_JSON)

    r1 = generate_complete_rubric("q01", "Q", "S", llm=llm1, output_dir=tmp_path / "r1")
    r2 = generate_complete_rubric("q01", "Q", "S", llm=llm2, output_dir=tmp_path / "r2")

    ids1 = [c.id for c in r1.rubric.checks]
    ids2 = [c.id for c in r2.rubric.checks]
    assert ids1 == ids2
