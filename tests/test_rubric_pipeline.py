"""T4.2 — Integration tests for the full rubric generation pipeline.

Tests chain: LLM generate → extract checks → validate categories → deduplicate.
LLM calls are mocked so tests run offline and deterministically.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grading_pipeline.models import CheckCategory, Rubric
from grading_pipeline.rubric_generator import GenerationResult, generate_complete_rubric


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_VALID_LLM_JSON = json.dumps(
    {
        "total_points": 10,
        "dimensions": [
            {
                "title": "Concept definition",
                "category": "semantic",
                "points": 6.0,
                "checks": [
                    {"text": "Student defines 'object' as an instance of a class", "weight": 1.0},
                    {"text": "Student mentions attributes and methods", "weight": 1.0},
                ],
            },
            {
                "title": "Application",
                "category": "application",
                "points": 4.0,
                "checks": [
                    {"text": "Student provides a concrete example of an object", "weight": 1.5},
                ],
            },
        ],
    }
)


def _make_llm(response_text: str) -> MagicMock:
    llm = MagicMock()
    resp = MagicMock()
    resp.text = response_text
    llm.complete.return_value = resp
    return llm


@pytest.fixture
def tmp_output_dir(tmp_path):
    return tmp_path / "rubrics"


@pytest.fixture
def valid_llm():
    return _make_llm(_VALID_LLM_JSON)


@pytest.fixture
def config_path():
    return Path(__file__).parent.parent / "config" / "grading_categories.yaml"


# ---------------------------------------------------------------------------
# Happy path: full pipeline
# ---------------------------------------------------------------------------

class TestFullRubricPipeline:
    def test_returns_generation_result(self, valid_llm, tmp_output_dir, config_path):
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        assert isinstance(result, GenerationResult)

    def test_rubric_is_populated(self, valid_llm, tmp_output_dir, config_path):
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        assert isinstance(result.rubric, Rubric)
        assert len(result.rubric.checks) == 3

    def test_question_id_propagated(self, valid_llm, tmp_output_dir, config_path):
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        assert result.question_id == "q01"
        for check in result.rubric.checks:
            assert check.question_id == "q01"

    def test_artifact_files_written(self, valid_llm, tmp_output_dir, config_path):
        generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
            version=1,
        )
        base = tmp_output_dir / "q01" / "v1"
        assert (base / "01_raw_llm_response.txt").exists()
        assert (base / "02_extracted.json").exists()
        assert (base / "03_categorized.json").exists()
        assert (base / "04_deduplicated.json").exists()
        assert (base / "04_dedup_metadata.json").exists()

    def test_all_check_categories_valid(self, valid_llm, tmp_output_dir, config_path):
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        valid_cats = {c.value for c in CheckCategory}
        for check in result.rubric.checks:
            assert check.category.value in valid_cats

    def test_intermediate_rubrics_recorded(self, valid_llm, tmp_output_dir, config_path):
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        # All three intermediate rubrics must be Rubric instances
        assert isinstance(result.rubric_after_extraction, Rubric)
        assert isinstance(result.rubric_after_categorization, Rubric)
        assert isinstance(result.rubric, Rubric)

    def test_version_stored(self, valid_llm, tmp_output_dir, config_path):
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object in OOP?",
            source_content="An object is an instance of a class...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
            version=3,
        )
        assert result.version == 3


# ---------------------------------------------------------------------------
# Deduplication is exercised end-to-end
# ---------------------------------------------------------------------------

class TestPipelineDeduplication:
    def test_duplicate_checks_removed(self, tmp_output_dir, config_path):
        """Two nearly-identical checks should be deduplicated."""
        llm_json = json.dumps(
            {
                "total_points": 10,
                "dimensions": [
                    {
                        "title": "Concept explanation",
                        "category": "semantic",
                        "points": 6.0,
                        "checks": [
                            {"text": "Student defines encapsulation", "weight": 1.0},
                            {"text": "Student defines encapsulation", "weight": 1.0},  # exact duplicate
                        ],
                    },
                    {
                        "title": "Application",
                        "category": "application",
                        "points": 4.0,
                        "checks": [
                            {"text": "Student gives an example of encapsulation", "weight": 1.0},
                        ],
                    },
                ],
            }
        )
        llm = _make_llm(llm_json)

        def always_similar(a: str, b: str) -> float:
            return 1.0  # force deduplication

        result = generate_complete_rubric(
            question_id="q02",
            question_text="Explain encapsulation.",
            source_content="...",
            llm=llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
            similarity_fn=always_similar,
        )
        # always_similar returns 1.0 for all pairs, so both duplicates and the
        # application check are also removed — at least 1 removed and only 1 survives
        assert result.checks_removed >= 1
        assert result.final_check_count == 1

    def test_no_duplicates_preserves_all(self, valid_llm, tmp_output_dir, config_path):
        """Unique checks must not be removed."""
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object?",
            source_content="...",
            llm=valid_llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        assert result.checks_removed == 0
        assert result.final_check_count == 3


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------

class TestPipelineErrorCases:
    def test_llm_empty_response_raises(self, tmp_output_dir, config_path):
        llm = _make_llm("")
        with pytest.raises(ValueError, match="LLM"):
            generate_complete_rubric(
                question_id="q01",
                question_text="Q?",
                source_content="...",
                llm=llm,
                output_dir=tmp_output_dir,
                config_path=config_path,
            )

    def test_llm_invalid_json_raises(self, tmp_output_dir, config_path):
        llm = _make_llm("not valid json at all {{{{")
        with pytest.raises(Exception):
            generate_complete_rubric(
                question_id="q01",
                question_text="Q?",
                source_content="...",
                llm=llm,
                output_dir=tmp_output_dir,
                config_path=config_path,
            )

    def test_llm_retried_on_failure(self, tmp_output_dir, config_path):
        """LLM failure on first attempt should be retried."""
        llm = MagicMock()
        good_resp = MagicMock()
        good_resp.text = _VALID_LLM_JSON
        llm.complete.side_effect = [RuntimeError("timeout"), good_resp]

        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object?",
            source_content="...",
            llm=llm,
            output_dir=tmp_output_dir,
            config_path=config_path,
        )
        assert len(result.rubric.checks) == 3
        assert llm.complete.call_count == 2

    def test_unwritable_output_dir_adds_warning(self, config_path):
        """Artifact write failure should produce a warning, not a crash."""
        llm = _make_llm(_VALID_LLM_JSON)
        # Use a path that cannot be created (file exists where dir would go)
        bad_dir = Path("/dev/null/impossible")
        result = generate_complete_rubric(
            question_id="q01",
            question_text="What is an object?",
            source_content="...",
            llm=llm,
            output_dir=bad_dir,
            config_path=config_path,
        )
        assert any("artifact" in w.lower() or "save" in w.lower() for w in result.warnings)
        assert result.artifacts_dir is None
