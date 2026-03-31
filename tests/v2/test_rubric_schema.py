"""Tests for v2 rubric schema validation."""

import pytest
from pydantic import ValidationError

from v2.rubric_schema import MAX_CHECKS_PER_CRITERION, RubricV2Response, parse_rubric_response


VALID_JSON = {
    "criteria": [
        {
            "criterion_id": "role_of_zero",
            "points": 1,
            "checks": [
                {
                    "check_id": "c1",
                    "check_type": "definition",
                    "concept": "zero is arbitrary",
                    "points": 1,
                    "precision_levels": {
                        "full": "Names convention and states not absence of heat",
                        "partial": "States zero is arbitrary without specifics",
                        "none": "Absent or wrong",
                    },
                }
            ],
        }
    ]
}

MISSING_PRECISION_JSON = {
    "criteria": [
        {
            "criterion_id": "crit1",
            "points": 1,
            "checks": [
                {
                    "check_id": "c1",
                    "check_type": "definition",
                    "concept": "x",
                    "points": 1,
                    "precision_levels": {
                        "full": "ok",
                        # missing partial and none
                    },
                }
            ],
        }
    ]
}

N = MAX_CHECKS_PER_CRITERION + 1   # 5 checks, exceeds budget of 4
TOO_MANY_CHECKS_JSON = {
    "criteria": [
        {
            "criterion_id": "crit1",
            "points": N * 1.0,   # matches sum of check points
            "checks": [
                {
                    "check_id": f"c{i}",
                    "check_type": "definition",
                    "concept": "x",
                    "points": 1.0,
                    "precision_levels": {"full": "f", "partial": "p", "none": "n"},
                }
                for i in range(N)
            ],
        }
    ]
}

MISMATCHED_POINTS_JSON = {
    "criteria": [
        {
            "criterion_id": "crit1",
            "points": 5,   # does not equal sum of check points (1)
            "checks": [
                {
                    "check_id": "c1",
                    "check_type": "definition",
                    "concept": "x",
                    "points": 1,
                    "precision_levels": {"full": "f", "partial": "p", "none": "n"},
                }
            ],
        }
    ]
}


def test_parse_valid_rubric():
    rubric = parse_rubric_response(VALID_JSON, question_id="q01", question_type="distinction", version=1)
    assert rubric.question_id == "q01"
    assert rubric.version == 1
    assert rubric.rubric_id == "q01_v1"
    assert len(rubric.criteria) == 1
    assert len(rubric.criteria[0].checks) == 1


def test_parse_rejects_missing_precision_levels():
    with pytest.raises(ValidationError):
        parse_rubric_response(MISSING_PRECISION_JSON, question_id="q01", question_type="distinction", version=1)


def test_parse_rejects_too_many_checks():
    with pytest.raises(ValidationError):
        parse_rubric_response(TOO_MANY_CHECKS_JSON, question_id="q01", question_type="distinction", version=1)


def test_parse_rejects_mismatched_criterion_points():
    with pytest.raises(ValidationError):
        parse_rubric_response(MISMATCHED_POINTS_JSON, question_id="q01", question_type="distinction", version=1)


def test_parse_sets_rubric_id_from_question_and_version():
    rubric = parse_rubric_response(VALID_JSON, question_id="q05", question_type="mechanism", version=3)
    assert rubric.rubric_id == "q05_v3"
    assert rubric.question_type == "mechanism"


def test_parse_rejects_empty_criteria():
    with pytest.raises(ValidationError):
        parse_rubric_response({"criteria": []}, question_id="q01", question_type="distinction", version=1)
