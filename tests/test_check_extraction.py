"""Tests for grading_pipeline/check_extraction.py (T2.2).

All tests are derived from the T2.2 specification:
  - extract_checks_from_rubric() parses LLM JSON and returns a Rubric
  - Each dimension maps to 1-4 atomic Check objects
  - Each Check: has a unique ID, correct category, positive weight,
    preserves source dimension reference
  - Total checks per rubric: 3–10 (per grading_config.yaml)
  - Rubric total_points == 10 (enforced by schema)
  - Handles markdown code fences in LLM output
  - Raises ValueError on malformed JSON or schema violations

Spec references:
  TASK_LIST.md §T2.2
  grading_pipeline/rubric_generator_template.txt (output schema)
  config/grading_config.yaml §scoring (min/max checks)
"""

import json

import pytest
from pydantic import ValidationError

from grading_pipeline.check_extraction import extract_checks, parse_rubric_json
from grading_pipeline.models import CheckCategory, Rubric


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_valid_json(dimensions: list[dict] | None = None) -> str:
    """Return a valid rubric JSON string with default or custom dimensions."""
    if dimensions is None:
        dimensions = [
            {
                "title": "Conceptual Understanding",
                "category": "semantic",
                "points": 4,
                "checks": [
                    {"text": "Student correctly defines X.", "weight": 2.0},
                    {"text": "Student correctly defines Y.", "weight": 2.0},
                ],
            },
            {
                "title": "Concrete Example",
                "category": "application",
                "points": 4,
                "checks": [
                    {"text": "Student provides a concrete example of Z.", "weight": 2.0},
                    {"text": "Student's example correctly illustrates W.", "weight": 2.0},
                ],
            },
            {
                "title": "Clarity",
                "category": "clarity",
                "points": 2,
                "checks": [
                    {"text": "Student's answer is logically organized.", "weight": 2.0},
                ],
            },
        ]
    return json.dumps({"dimensions": dimensions, "total_points": 10})


# ===========================================================================
# parse_rubric_json
# ===========================================================================

class TestParseRubricJson:
    def test_valid_json_parses(self):
        result = parse_rubric_json(_make_valid_json())
        assert len(result.dimensions) == 3
        assert result.total_points == 10

    def test_strips_markdown_code_fence(self):
        raw = f"```json\n{_make_valid_json()}\n```"
        result = parse_rubric_json(raw)
        assert result.total_points == 10

    def test_strips_plain_code_fence(self):
        raw = f"```\n{_make_valid_json()}\n```"
        result = parse_rubric_json(raw)
        assert result.total_points == 10

    def test_extracts_json_from_surrounding_text(self):
        raw = f"Here is the rubric:\n{_make_valid_json()}\nEnd of response."
        result = parse_rubric_json(raw)
        assert result.total_points == 10

    def test_invalid_json_raises_value_error(self):
        # Spec: raises ValueError on malformed / unparseable input
        with pytest.raises(ValueError):
            parse_rubric_json("not json at all")

    def test_no_json_object_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_rubric_json("just a plain string without braces")

    def test_points_not_summing_to_10_raises(self):
        dims = [
            {"title": "A", "category": "semantic", "points": 6,
             "checks": [{"text": "check.", "weight": 1.0}]},
            {"title": "B", "category": "clarity", "points": 3,
             "checks": [{"text": "check.", "weight": 1.0}]},
        ]
        with pytest.raises(ValueError, match="[Ss]um|total|points"):
            parse_rubric_json(json.dumps({"dimensions": dims, "total_points": 10}))

    def test_invalid_category_raises(self):
        dims = [
            {"title": "A", "category": "invented_category", "points": 5,
             "checks": [{"text": "check.", "weight": 1.0}]},
            {"title": "B", "category": "semantic", "points": 5,
             "checks": [{"text": "check.", "weight": 1.0}]},
        ]
        with pytest.raises(ValueError):
            parse_rubric_json(json.dumps({"dimensions": dims, "total_points": 10}))

    def test_too_many_dimensions_raises(self):
        # Spec: max 5 dimensions
        dims = [
            {"title": f"Dim{i}", "category": "semantic", "points": 1,
             "checks": [{"text": "check.", "weight": 1.0}]}
            for i in range(7)
        ]
        # Adjust points to sum to 10 for first 7 dims won't sum to 10 with 1 each (7≠10)
        # Use 6 dims with varied points to isolate the count violation
        dims6 = [
            {"title": f"Dim{i}", "category": "semantic",
             "points": 10 / 6,
             "checks": [{"text": "check.", "weight": 1.0}]}
            for i in range(6)
        ]
        with pytest.raises(ValueError):
            parse_rubric_json(json.dumps({"dimensions": dims6, "total_points": 10}))

    def test_dimension_missing_checks_raises(self):
        dims = [
            {"title": "A", "category": "semantic", "points": 5, "checks": []},
            {"title": "B", "category": "clarity", "points": 5,
             "checks": [{"text": "check.", "weight": 1.0}]},
        ]
        with pytest.raises(ValueError):
            parse_rubric_json(json.dumps({"dimensions": dims, "total_points": 10}))

    def test_check_weight_must_be_positive(self):
        dims = [
            {"title": "A", "category": "semantic", "points": 5,
             "checks": [{"text": "check.", "weight": 0}]},
            {"title": "B", "category": "clarity", "points": 5,
             "checks": [{"text": "check.", "weight": 1.0}]},
        ]
        with pytest.raises(ValueError):
            parse_rubric_json(json.dumps({"dimensions": dims, "total_points": 10}))


# ===========================================================================
# extract_checks — happy path
# ===========================================================================

class TestExtractChecksHappyPath:
    def test_returns_rubric_instance(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01")
        assert isinstance(rubric, Rubric)

    def test_rubric_id_defaults_to_question_rubric(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01")
        assert rubric.id == "q01_rubric"

    def test_rubric_id_can_be_overridden(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01",
                                rubric_id="custom_rubric_id")
        assert rubric.id == "custom_rubric_id"

    def test_question_id_propagated(self):
        rubric = extract_checks(_make_valid_json(), question_id="q07")
        assert rubric.question_id == "q07"
        for check in rubric.checks:
            assert check.question_id == "q07"

    def test_total_points_is_10(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01")
        assert rubric.total_points == 10.0

    def test_check_count_within_spec_bounds(self):
        # Spec: 3–10 checks per rubric (grading_config.yaml)
        rubric = extract_checks(_make_valid_json(), question_id="q01")
        assert 3 <= len(rubric.checks) <= 10

    def test_default_version_is_1(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01")
        assert rubric.version == 1

    def test_version_can_be_set(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01", version=3)
        assert rubric.version == 3

    def test_dimensions_stored_in_rubric(self):
        rubric = extract_checks(_make_valid_json(), question_id="q01")
        assert rubric.dimensions is not None
        assert len(rubric.dimensions) == 3


# ===========================================================================
# extract_checks — Check-level invariants (spec §T2.2)
# ===========================================================================

class TestExtractChecksCheckInvariants:
    @pytest.fixture(autouse=True)
    def rubric(self):
        self.rubric = extract_checks(_make_valid_json(), question_id="q01")

    def test_check_ids_are_unique(self):
        ids = [c.id for c in self.rubric.checks]
        assert len(ids) == len(set(ids))

    def test_check_ids_contain_question_id(self):
        for c in self.rubric.checks:
            assert c.id.startswith("q01_")

    def test_check_ids_encode_dimension_and_position(self):
        # Expected pattern: q01_d{N}_c{M}
        import re
        pattern = re.compile(r"^q01_d\d+_c\d+$")
        for c in self.rubric.checks:
            assert pattern.match(c.id), f"ID {c.id!r} does not match expected pattern"

    def test_each_check_has_valid_category(self):
        valid = {CheckCategory.SEMANTIC, CheckCategory.APPLICATION, CheckCategory.CLARITY}
        for c in self.rubric.checks:
            assert c.category in valid

    def test_each_check_inherits_category_from_dimension(self):
        # Dimension 1: semantic → checks q01_d1_*
        # Dimension 2: application → checks q01_d2_*
        # Dimension 3: clarity → checks q01_d3_*
        expected = {
            "q01_d1_c1": CheckCategory.SEMANTIC,
            "q01_d1_c2": CheckCategory.SEMANTIC,
            "q01_d2_c1": CheckCategory.APPLICATION,
            "q01_d2_c2": CheckCategory.APPLICATION,
            "q01_d3_c1": CheckCategory.CLARITY,
        }
        by_id = {c.id: c for c in self.rubric.checks}
        for check_id, expected_cat in expected.items():
            assert by_id[check_id].category == expected_cat

    def test_each_check_weight_is_positive(self):
        for c in self.rubric.checks:
            assert c.weight > 0

    def test_each_check_references_rubric_id(self):
        for c in self.rubric.checks:
            assert c.rubric_id == "q01_rubric"

    def test_each_check_references_source_dimension(self):
        # dimension_id must be set (audit trail requirement)
        for c in self.rubric.checks:
            assert c.dimension_id is not None
            assert c.dimension_id != ""

    def test_each_check_text_is_non_empty(self):
        for c in self.rubric.checks:
            assert c.text.strip() != ""


# ===========================================================================
# extract_checks — error cases
# ===========================================================================

class TestExtractChecksErrors:
    def test_malformed_json_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_checks("{not valid json", question_id="q01")

    def test_points_mismatch_raises_value_error(self):
        dims = [
            {"title": "A", "category": "semantic", "points": 7,
             "checks": [{"text": "t", "weight": 1.0}]},
            {"title": "B", "category": "clarity", "points": 2,
             "checks": [{"text": "t", "weight": 1.0}]},
        ]
        with pytest.raises(ValueError):
            extract_checks(json.dumps({"dimensions": dims, "total_points": 10}),
                           question_id="q01")

    def test_fenced_json_still_extracts(self):
        fenced = f"```json\n{_make_valid_json()}\n```"
        rubric = extract_checks(fenced, question_id="q05")
        assert rubric.question_id == "q05"
        assert len(rubric.checks) > 0

    def test_minimal_rubric_two_dimensions(self):
        # Spec allows 2 dimensions minimum
        dims = [
            {"title": "A", "category": "semantic", "points": 5,
             "checks": [{"text": "check one.", "weight": 1.0},
                        {"text": "check two.", "weight": 1.0}]},
            {"title": "B", "category": "application", "points": 5,
             "checks": [{"text": "check three.", "weight": 1.0}]},
        ]
        rubric = extract_checks(json.dumps({"dimensions": dims, "total_points": 10}),
                                question_id="q01")
        assert len(rubric.checks) == 3

    def test_single_check_per_dimension_allowed(self):
        dims = [
            {"title": "A", "category": "semantic", "points": 5,
             "checks": [{"text": "only check.", "weight": 5.0}]},
            {"title": "B", "category": "clarity", "points": 5,
             "checks": [{"text": "only check B.", "weight": 5.0}]},
        ]
        rubric = extract_checks(json.dumps({"dimensions": dims, "total_points": 10}),
                                question_id="q01")
        assert len(rubric.checks) == 2

    def test_four_checks_per_dimension_allowed(self):
        # Spec max: 4 checks per dimension
        dims = [
            {"title": "A", "category": "semantic", "points": 8,
             "checks": [{"text": f"check {i}.", "weight": 1.0} for i in range(4)]},
            {"title": "B", "category": "clarity", "points": 2,
             "checks": [{"text": "check B.", "weight": 1.0}]},
        ]
        rubric = extract_checks(json.dumps({"dimensions": dims, "total_points": 10}),
                                question_id="q01")
        assert len(rubric.checks) == 5

    def test_five_checks_per_dimension_rejected(self):
        # Spec max: 4 checks per dimension
        dims = [
            {"title": "A", "category": "semantic", "points": 8,
             "checks": [{"text": f"check {i}.", "weight": 1.0} for i in range(5)]},
            {"title": "B", "category": "clarity", "points": 2,
             "checks": [{"text": "check B.", "weight": 1.0}]},
        ]
        with pytest.raises(ValueError):
            extract_checks(json.dumps({"dimensions": dims, "total_points": 10}),
                           question_id="q01")
