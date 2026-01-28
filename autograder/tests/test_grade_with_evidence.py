"""Tests for grade_with_evidence module.

Comprehensive test suite covering:
- Evidence formatting
- Prompt generation
- Criterion grading with LLM
- Full student grading workflow
- Error handling and retry logic
- Score validation and calculations
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from grading_dynamic_rubrics.grade_with_evidence import (
    _format_criterion_grading_prompt,
    _format_evidence_for_prompt,
    _grade_criterion,
    grade_student_with_evidence,
)


# ============================================================================
# Test Data / Fixtures
# ============================================================================


@pytest.fixture
def sample_evidence():
    """Sample evidence items for testing."""
    return [
        {
            "source_id": "file_slides_data_type_quality",
            "texts": ["Properties of Attribute Values. Nominal, ordinal, interval, ratio."],
            "reranker_scores": [1.041],
            "similarity_scores": [0.699],
            "indexes": ["sentence_index"],
        },
        {
            "source_id": "file_slides_data_type_quality",
            "texts": ["Zip codes are categorical attributes despite integer storage."],
            "reranker_scores": [0.926],
            "similarity_scores": [0.767],
            "indexes": ["sentence_index"],
        },
    ]


@pytest.fixture
def sample_criterion_context():
    """Sample criterion context for testing."""
    return {
        "criterion_id": "conceptual_understanding",
        "criterion_description": "Explains attribute properties and their role in analysis.",
        "max_score": 3,
    }


@pytest.fixture
def sample_evidence_context():
    """Sample full evidence context for testing."""
    return {
        "question_id": "q02",
        "question_text": "Explain the principle using the zip code example.",
        "grading_context": [
            {
                "criterion_id": "conceptual_understanding_of_attribute_properties",
                "criterion_description": "A full-credit answer explains that an attribute's valid analyses are determined by its intrinsic properties.",
                "max_score": 3,
                "evidence": [
                    {
                        "source_id": "file_slides",
                        "texts": ["Nominal, ordinal, interval, ratio attributes."],
                        "reranker_scores": [1.041],
                        "similarity_scores": [0.699],
                        "indexes": ["sentence_index"],
                    }
                ],
            },
            {
                "criterion_id": "application_to_zip_code",
                "criterion_description": "Correctly identifies zip code as nominal despite integer storage.",
                "max_score": 2,
                "evidence": [
                    {
                        "source_id": "file_slides",
                        "texts": ["Zip codes are categorical."],
                        "reranker_scores": [0.926],
                        "similarity_scores": [0.767],
                        "indexes": ["sentence_index"],
                    }
                ],
            },
        ],
    }


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return MagicMock()


# ============================================================================
# Test _format_evidence_for_prompt
# ============================================================================


class TestFormatEvidenceForPrompt:
    """Tests for evidence formatting function."""

    def test_format_with_valid_evidence(self, sample_evidence):
        """Test formatting valid evidence items."""
        result = _format_evidence_for_prompt(sample_evidence)

        assert "[1] Source: file_slides_data_type_quality" in result
        assert "[2] Source: file_slides_data_type_quality" in result
        assert "Relevance Score: 1.041" in result
        assert "Relevance Score: 0.926" in result
        assert "Properties of Attribute Values" in result

    def test_format_with_empty_evidence(self):
        """Test formatting empty evidence list."""
        result = _format_evidence_for_prompt([])
        assert result == "No evidence provided."

    def test_format_truncates_long_text(self):
        """Test that long evidence text is truncated."""
        long_text = "A" * 1000
        evidence = [
            {
                "source_id": "test_source",
                "texts": [long_text],
                "reranker_scores": [0.9],
                "similarity_scores": [0.8],
                "indexes": ["test_index"],
            }
        ]

        result = _format_evidence_for_prompt(evidence)
        assert len(result) < len(long_text)
        assert result.count("A") == 500  # Truncated to 500 chars

    def test_format_missing_text_field(self):
        """Test evidence with missing texts field."""
        evidence = [
            {
                "source_id": "test_source",
                "texts": [],
                "reranker_scores": [0.9],
                "similarity_scores": [0.8],
                "indexes": ["test_index"],
            }
        ]

        result = _format_evidence_for_prompt(evidence)
        assert result == "No evidence provided."

    def test_format_missing_reranker_score(self, sample_evidence):
        """Test evidence with missing reranker_scores."""
        sample_evidence[0].pop("reranker_scores")
        result = _format_evidence_for_prompt(sample_evidence)

        assert "[1] Source:" in result
        # Should default to 0 for missing score
        assert "Relevance Score: 0" in result or "Relevance Score: 0.000" in result


# ============================================================================
# Test _format_criterion_grading_prompt
# ============================================================================


class TestFormatCriterionGradingPrompt:
    """Tests for criterion grading prompt formatting."""

    def test_prompt_includes_criterion_description(self, sample_evidence, sample_criterion_context):
        """Test that prompt includes criterion description."""
        prompt = _format_criterion_grading_prompt(
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Student's answer text.",
        )

        assert "CRITERION:" in prompt
        assert sample_criterion_context["criterion_description"] in prompt

    def test_prompt_includes_evidence(self, sample_evidence, sample_criterion_context):
        """Test that prompt includes formatted evidence."""
        prompt = _format_criterion_grading_prompt(
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Student's answer text.",
        )

        assert "EVIDENCE FROM SOURCE MATERIALS:" in prompt
        assert "file_slides_data_type_quality" in prompt

    def test_prompt_includes_student_answer(self, sample_evidence, sample_criterion_context):
        """Test that prompt includes student answer."""
        student_answer = "This is the student's answer to the criterion."
        prompt = _format_criterion_grading_prompt(
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer=student_answer,
        )

        assert "STUDENT ANSWER:" in prompt
        assert student_answer in prompt

    def test_prompt_includes_max_score(self, sample_evidence, sample_criterion_context):
        """Test that prompt includes max_score information."""
        prompt = _format_criterion_grading_prompt(
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
        )

        assert "CRITERION WEIGHT:" in prompt
        assert "3 points" in prompt

    def test_prompt_requests_json_response(self, sample_evidence, sample_criterion_context):
        """Test that prompt requests JSON response format."""
        prompt = _format_criterion_grading_prompt(
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
        )

        assert "JSON" in prompt
        assert '"score":' in prompt
        assert '"feedback":' in prompt

    def test_prompt_includes_scoring_scale(self, sample_evidence, sample_criterion_context):
        """Test that prompt includes scoring scale guidance."""
        prompt = _format_criterion_grading_prompt(
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
        )

        assert "0-3: Poor" in prompt
        assert "4-6: Adequate" in prompt
        assert "7-9: Good" in prompt
        assert "10: Excellent" in prompt


# ============================================================================
# Test _grade_criterion
# ============================================================================


class TestGradeCriterion:
    """Tests for single criterion grading."""

    def test_grade_criterion_valid_response(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test grading with valid LLM response."""
        mock_response = MagicMock()
        mock_response.message.content = '{"score": 8, "feedback": "Good understanding demonstrated."}'
        mock_llm.chat.return_value = mock_response

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Student answer here.",
            llm=mock_llm,
        )

        assert result["criterion_id"] == sample_criterion_context["criterion_id"]
        assert result["llm_score"] == 8
        assert result["max_score"] == 3
        assert result["weighted_score"] == (8 / 10.0) * 3
        assert result["feedback"] == "Good understanding demonstrated."
        assert len(result["evidence_used"]) == 2

    def test_grade_criterion_score_at_boundaries(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test score boundary validation (0 and 10)."""
        # Test score = 0
        mock_response = MagicMock()
        mock_response.message.content = '{"score": 0, "feedback": "No understanding."}'
        mock_llm.chat.return_value = mock_response

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Bad answer",
            llm=mock_llm,
        )

        assert result["llm_score"] == 0
        assert result["weighted_score"] == 0

        # Test score = 10
        mock_response.message.content = '{"score": 10, "feedback": "Perfect."}'
        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Perfect answer",
            llm=mock_llm,
        )

        assert result["llm_score"] == 10
        assert result["weighted_score"] == 3.0

    def test_grade_criterion_invalid_score_clamped(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test that invalid scores are clamped to [0, 10]."""
        # Test score > 10 (should be clamped to 10)
        mock_response = MagicMock()
        mock_response.message.content = '{"score": 15, "feedback": "Over max."}'
        mock_llm.chat.return_value = mock_response

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
            llm=mock_llm,
        )

        assert result["llm_score"] == 10

        # Test score < 0 (should be clamped to 0)
        mock_response.message.content = '{"score": -5, "feedback": "Negative."}'
        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
            llm=mock_llm,
        )

        assert result["llm_score"] == 0

    def test_grade_criterion_json_parse_error_retries(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test that JSON parse errors trigger retries."""
        # First two attempts fail with invalid JSON, third succeeds
        mock_response_bad = MagicMock()
        mock_response_bad.message.content = "{invalid json"

        mock_response_good = MagicMock()
        mock_response_good.message.content = '{"score": 7, "feedback": "Good."}'

        mock_llm.chat.side_effect = [mock_response_bad, mock_response_bad, mock_response_good]

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
            llm=mock_llm,
            max_retries=3,
        )

        assert result["llm_score"] == 7
        assert mock_llm.chat.call_count == 3

    def test_grade_criterion_missing_fields_error(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test error handling for missing required fields."""
        # Missing 'feedback' field
        mock_response = MagicMock()
        mock_response.message.content = '{"score": 5}'
        mock_llm.chat.return_value = mock_response

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
            llm=mock_llm,
            max_retries=1,
        )

        assert result["llm_score"] == 0
        assert "error" in result["feedback"].lower() or "Grading error" in result["feedback"]

    def test_grade_criterion_non_numeric_score_error(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test error handling for non-numeric scores."""
        mock_response = MagicMock()
        mock_response.message.content = '{"score": "eight", "feedback": "Not numeric."}'
        mock_llm.chat.return_value = mock_response

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
            llm=mock_llm,
            max_retries=1,
        )

        assert result["llm_score"] == 0
        assert "error" in result["feedback"].lower() or "Grading error" in result["feedback"]

    def test_grade_criterion_max_retries_exceeded(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test behavior when max retries exceeded."""
        mock_response = MagicMock()
        mock_response.message.content = "not valid json at all"
        mock_llm.chat.return_value = mock_response

        result = _grade_criterion(
            criterion_id=sample_criterion_context["criterion_id"],
            criterion_description=sample_criterion_context["criterion_description"],
            max_score=sample_criterion_context["max_score"],
            evidence=sample_evidence,
            student_answer="Answer",
            llm=mock_llm,
            max_retries=3,
        )

        # Should default to 0 score and error feedback
        assert result["llm_score"] == 0
        assert "Grading error" in result["feedback"]
        assert mock_llm.chat.call_count == 3

    def test_grade_criterion_weighted_score_calculation(self, sample_evidence, sample_criterion_context, mock_llm):
        """Test weighted score calculation."""
        test_cases = [
            (0, 3, 0.0),
            (5, 3, 1.5),
            (10, 3, 3.0),
            (7, 2, 1.4),
            (8, 2, 1.6),
        ]

        for llm_score, max_score, expected_weighted in test_cases:
            mock_response = MagicMock()
            mock_response.message.content = f'{{"score": {llm_score}, "feedback": "Test"}}'
            mock_llm.chat.return_value = mock_response

            result = _grade_criterion(
                criterion_id="test_criterion",
                criterion_description="Test description",
                max_score=max_score,
                evidence=sample_evidence,
                student_answer="Answer",
                llm=mock_llm,
            )

            assert abs(result["weighted_score"] - expected_weighted) < 0.01


# ============================================================================
# Test grade_student_with_evidence
# ============================================================================


class TestGradeStudentWithEvidence:
    """Tests for full student grading workflow."""

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_grade_student_valid_evidence_context(self, mock_settings, sample_evidence_context):
        """Test grading student with valid evidence context."""
        mock_llm = MagicMock()
        mock_settings.llm = mock_llm

        # Mock LLM responses for each criterion
        responses = [
            MagicMock(message=MagicMock(content='{"score": 9, "feedback": "Excellent understanding."}')),
            MagicMock(message=MagicMock(content='{"score": 8, "feedback": "Good application."}')),
        ]
        mock_llm.chat.side_effect = responses

        result = grade_student_with_evidence(
            student_id="student_001",
            student_answer="The student correctly identifies zip code as nominal...",
            question_text="Explain the principle using the zip code example.",
            rubric={},
            evidence_context=sample_evidence_context,
            answer_type="good",
        )

        assert result["student_id"] == "student_001"
        assert result["question_id"] == "q02"
        assert result["answer_type"] == "good"
        assert result["total_score"] == pytest.approx(9.0 * 3 / 10.0 + 8.0 * 2 / 10.0, rel=0.01)
        assert result["max_score"] == 5
        assert len(result["criterion_results"]) == 2
        assert "graded_at" in result

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_grade_student_multiple_criteria(self, mock_settings):
        """Test grading with multiple criteria."""
        mock_llm = MagicMock()
        mock_settings.llm = mock_llm

        evidence_context = {
            "question_id": "q01",
            "question_text": "Test question",
            "grading_context": [
                {
                    "criterion_id": "criterion_1",
                    "criterion_description": "First criterion",
                    "max_score": 2,
                    "evidence": [],
                },
                {
                    "criterion_id": "criterion_2",
                    "criterion_description": "Second criterion",
                    "max_score": 3,
                    "evidence": [],
                },
                {
                    "criterion_id": "criterion_3",
                    "criterion_description": "Third criterion",
                    "max_score": 2,
                    "evidence": [],
                },
                {
                    "criterion_id": "criterion_4",
                    "criterion_description": "Fourth criterion",
                    "max_score": 3,
                    "evidence": [],
                },
            ],
        }

        responses = [
            MagicMock(message=MagicMock(content='{"score": 10, "feedback": "Perfect"}')),
            MagicMock(message=MagicMock(content='{"score": 8, "feedback": "Good"}')),
            MagicMock(message=MagicMock(content='{"score": 6, "feedback": "Adequate"}')),
            MagicMock(message=MagicMock(content='{"score": 4, "feedback": "Needs work"}')),
        ]
        mock_llm.chat.side_effect = responses

        result = grade_student_with_evidence(
            student_id="student_002",
            student_answer="Student answer",
            question_text="Test question",
            rubric={},
            evidence_context=evidence_context,
        )

        assert len(result["criterion_results"]) == 4
        # Total: (10/10)*2 + (8/10)*3 + (6/10)*2 + (4/10)*3 = 2 + 2.4 + 1.2 + 1.2 = 6.8
        assert result["total_score"] == pytest.approx(6.8, rel=0.01)
        assert result["max_score"] == 10

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_grade_student_empty_grading_context(self, mock_settings):
        """Test grading with empty grading context."""
        mock_llm = MagicMock()
        mock_settings.llm = mock_llm

        evidence_context = {
            "question_id": "q01",
            "question_text": "Test question",
            "grading_context": [],
        }

        result = grade_student_with_evidence(
            student_id="student_003",
            student_answer="Answer",
            question_text="Question",
            rubric={},
            evidence_context=evidence_context,
        )

        assert len(result["criterion_results"]) == 0
        assert result["total_score"] == 0.0
        assert result["max_score"] == 0

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_grade_student_partial_criterion_failure(self, mock_settings):
        """Test grading continues when one criterion fails."""
        mock_llm = MagicMock()
        mock_settings.llm = mock_llm

        evidence_context = {
            "question_id": "q01",
            "question_text": "Test question",
            "grading_context": [
                {
                    "criterion_id": "criterion_1",
                    "criterion_description": "First criterion",
                    "max_score": 5,
                    "evidence": [],
                },
                {
                    "criterion_id": "criterion_2",
                    "criterion_description": "Second criterion",
                    "max_score": 5,
                    "evidence": [],
                },
            ],
        }

        # First criterion succeeds, second fails
        responses = [
            MagicMock(message=MagicMock(content='{"score": 9, "feedback": "Good"}')),
            MagicMock(message=MagicMock(content="invalid json")),
        ]
        mock_llm.chat.side_effect = responses

        result = grade_student_with_evidence(
            student_id="student_004",
            student_answer="Answer",
            question_text="Question",
            rubric={},
            evidence_context=evidence_context,
        )

        # Should have results for both criteria
        assert len(result["criterion_results"]) == 2
        # First criterion: normal score
        assert result["criterion_results"][0]["llm_score"] == 9
        # Second criterion: error defaults to 0
        assert result["criterion_results"][1]["llm_score"] == 0

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_grade_student_llm_initialization(self, mock_settings):
        """Test LLM initialization when not already configured."""
        # First call: Settings.llm is None, should call setup_llamaindex_defaults
        mock_settings.llm = None
        mock_llm = MagicMock()

        with patch("grading_dynamic_rubrics.grade_with_evidence.setup_llamaindex_defaults") as mock_setup:
            mock_settings.llm = mock_llm

            response = MagicMock(message=MagicMock(content='{"score": 5, "feedback": "Test"}'))
            mock_llm.chat.return_value = response

            evidence_context = {
                "question_id": "q01",
                "question_text": "Test",
                "grading_context": [
                    {
                        "criterion_id": "c1",
                        "criterion_description": "Test",
                        "max_score": 1,
                        "evidence": [],
                    }
                ],
            }

            result = grade_student_with_evidence(
                student_id="student",
                student_answer="Answer",
                question_text="Question",
                rubric={},
                evidence_context=evidence_context,
            )

            assert result["total_score"] == pytest.approx(0.5, rel=0.01)

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_grade_student_result_structure(self, mock_settings):
        """Test that result has all required fields."""
        mock_llm = MagicMock()
        mock_settings.llm = mock_llm

        evidence_context = {
            "question_id": "q02",
            "question_text": "Test question",
            "grading_context": [
                {
                    "criterion_id": "c1",
                    "criterion_description": "Criterion 1",
                    "max_score": 5,
                    "evidence": [],
                },
            ],
        }

        response = MagicMock(message=MagicMock(content='{"score": 7, "feedback": "Good"}'))
        mock_llm.chat.return_value = response

        result = grade_student_with_evidence(
            student_id="student_001",
            student_answer="Student answer",
            question_text="Question text",
            rubric={},
            evidence_context=evidence_context,
            answer_type="good",
        )

        # Check all required fields
        assert "student_id" in result
        assert "question_id" in result
        assert "answer_type" in result
        assert "question_text" in result
        assert "student_answer" in result
        assert "total_score" in result
        assert "max_score" in result
        assert "criterion_results" in result
        assert "graded_at" in result

        # Check criterion_results structure
        assert len(result["criterion_results"]) == 1
        crit = result["criterion_results"][0]
        assert "criterion_id" in crit
        assert "llm_score" in crit
        assert "max_score" in crit
        assert "weighted_score" in crit
        assert "feedback" in crit
        assert "evidence_used" in crit


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple components."""

    @patch("grading_dynamic_rubrics.grade_with_evidence.Settings")
    def test_end_to_end_grading_q02_like(self, mock_settings):
        """Integration test simulating q02 grading scenario."""
        mock_llm = MagicMock()
        mock_settings.llm = mock_llm

        # Simulate q02-like scenario
        evidence_context = {
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
                            "texts": ["Properties of Attribute Values: Nominal, ordinal, interval, ratio."],
                            "reranker_scores": [1.041],
                            "similarity_scores": [0.699],
                            "indexes": ["sentence_index"],
                        }
                    ],
                },
                {
                    "criterion_id": "application_to_the_zip_code_example",
                    "criterion_description": "Identifies zip code as nominal despite integer storage.",
                    "max_score": 2,
                    "evidence": [
                        {
                            "source_id": "file_slides_data_type_quality",
                            "texts": ["Zip codes are categorical even when stored as integers."],
                            "reranker_scores": [0.926],
                            "similarity_scores": [0.767],
                            "indexes": ["sentence_index"],
                        }
                    ],
                },
                {
                    "criterion_id": "identification_of_an_inappropriate_analysis",
                    "criterion_description": "Names an inappropriate analysis if zip codes treated as numeric.",
                    "max_score": 2,
                    "evidence": [
                        {
                            "source_id": "file_slides_data_type_quality",
                            "texts": ["Averaging zip codes would be inappropriate."],
                            "reranker_scores": [0.850],
                            "similarity_scores": [0.700],
                            "indexes": ["sentence_index"],
                        }
                    ],
                },
                {
                    "criterion_id": "clarity_and_completeness_of_the_response",
                    "criterion_description": "Response is clear and complete.",
                    "max_score": 3,
                    "evidence": [
                        {
                            "source_id": "file_slides_data_type_quality",
                            "texts": ["Clear explanations with examples."],
                            "reranker_scores": [0.750],
                            "similarity_scores": [0.650],
                            "indexes": ["sentence_index"],
                        }
                    ],
                },
            ],
        }

        good_answer = """
        The principle is that attribute properties, not the data type, determine valid analyses.
        Zip codes are nominal attributes despite being stored as integers.
        Only distinctness is meaningful; order and arithmetic operations are not.
        Averaging zip codes would be inappropriate.
        """

        # Mock LLM responses for each criterion
        responses = [
            MagicMock(message=MagicMock(content='{"score": 9, "feedback": "Excellent understanding of properties."}')),
            MagicMock(message=MagicMock(content='{"score": 10, "feedback": "Correctly identifies zip code as nominal."}')),
            MagicMock(message=MagicMock(content='{"score": 8, "feedback": "Identifies averaging as inappropriate."}')),
            MagicMock(message=MagicMock(content='{"score": 9, "feedback": "Clear and complete explanation."}')),
        ]
        mock_llm.chat.side_effect = responses

        result = grade_student_with_evidence(
            student_id="student_001",
            student_answer=good_answer,
            question_text=evidence_context["question_text"],
            rubric={},
            evidence_context=evidence_context,
            answer_type="good",
        )

        # Verify results
        assert result["student_id"] == "student_001"
        assert result["question_id"] == "q02"
        assert result["answer_type"] == "good"
        assert len(result["criterion_results"]) == 4

        # Calculate expected score
        # c1: 9/10 * 3 = 2.7
        # c2: 10/10 * 2 = 2.0
        # c3: 8/10 * 2 = 1.6
        # c4: 9/10 * 3 = 2.7
        # Total: 9.0 out of 10
        assert result["total_score"] == pytest.approx(9.0, rel=0.1)
        assert result["max_score"] == 10
