# tests/v2/test_benchmark.py
import pytest
from v2.benchmark import (
    OrderingBenchmarkResult,
    check_ordering,
    find_violations,
)
from v2.models import AnswerQuality, GradeV2, OrderingViolation


def _make_grade(student_id: str, question_id: str, score: float) -> GradeV2:
    from datetime import datetime
    return GradeV2(
        grade_id=f"{student_id}_{question_id}",
        question_id=question_id,
        student_id=student_id,
        rubric_id="r1",
        rubric_version=1,
        check_evaluations=[],
        raw_score=score / 10.0,
        final_score=score,
    )


def test_no_violations_when_ordering_correct():
    grades = {
        AnswerQuality.GOOD: _make_grade("good_1", "q01", 8.0),
        AnswerQuality.LESS_GOOD: _make_grade("less_good_1", "q01", 5.0),
        AnswerQuality.WRONG: _make_grade("wrong_1", "q01", 2.0),
    }
    violations = find_violations(question_id="q01", grades_by_quality=grades)
    assert violations == []


def test_detects_less_good_less_than_wrong():
    grades = {
        AnswerQuality.GOOD: _make_grade("good_1", "q01", 8.0),
        AnswerQuality.LESS_GOOD: _make_grade("less_good_1", "q01", 1.0),  # BAD
        AnswerQuality.WRONG: _make_grade("wrong_1", "q01", 5.0),
    }
    violations = find_violations(question_id="q01", grades_by_quality=grades)
    assert len(violations) == 1
    assert violations[0].bad_pair == ("less_good", "wrong")


def test_detects_good_less_than_less_good():
    grades = {
        AnswerQuality.GOOD: _make_grade("good_1", "q01", 3.0),  # BAD
        AnswerQuality.LESS_GOOD: _make_grade("less_good_1", "q01", 7.0),
        AnswerQuality.WRONG: _make_grade("wrong_1", "q01", 2.0),
    }
    violations = find_violations(question_id="q01", grades_by_quality=grades)
    assert len(violations) == 1
    assert violations[0].bad_pair == ("good", "less_good")


def test_check_ordering_aggregate():
    all_grades = {
        "q01": {
            AnswerQuality.GOOD: _make_grade("g1", "q01", 8.0),
            AnswerQuality.LESS_GOOD: _make_grade("l1", "q01", 5.0),
            AnswerQuality.WRONG: _make_grade("w1", "q01", 2.0),
        },
        "q02": {
            AnswerQuality.GOOD: _make_grade("g2", "q02", 2.0),   # violation
            AnswerQuality.LESS_GOOD: _make_grade("l2", "q02", 6.0),
            AnswerQuality.WRONG: _make_grade("w2", "q02", 3.0),
        },
    }
    result = check_ordering(all_grades)
    assert result.total_questions == 2
    assert result.questions_with_violations == 1
    assert result.violation_rate == 0.5
