"""Ordering benchmark: checks good > less_good > wrong for each question."""

from __future__ import annotations

from dataclasses import dataclass, field

from v2.models import AnswerQuality, GradeV2, OrderingViolation

_EXPECTED_ORDER = [AnswerQuality.GOOD, AnswerQuality.LESS_GOOD, AnswerQuality.WRONG]


@dataclass
class OrderingBenchmarkResult:
    total_questions: int
    questions_with_violations: int
    all_violations: list[OrderingViolation] = field(default_factory=list)

    @property
    def violation_rate(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return self.questions_with_violations / self.total_questions

    def passed(self) -> bool:
        return self.questions_with_violations == 0


def find_violations(
    question_id: str,
    grades_by_quality: dict[AnswerQuality, GradeV2],
) -> list[OrderingViolation]:
    """Return ordering violations for one question."""
    violations = []
    pairs = [
        (AnswerQuality.GOOD, AnswerQuality.LESS_GOOD),
        (AnswerQuality.LESS_GOOD, AnswerQuality.WRONG),
    ]
    for higher, lower in pairs:
        score_higher = grades_by_quality[higher].final_score
        score_lower = grades_by_quality[lower].final_score
        if score_higher <= score_lower:
            violations.append(
                OrderingViolation(
                    question_id=question_id,
                    criterion_id="overall",
                    bad_pair=(higher.value, lower.value),
                    bad_scores=(score_higher, score_lower),
                    description=(
                        f"{higher.value} score ({score_higher:.2f}) <= "
                        f"{lower.value} score ({score_lower:.2f})"
                    ),
                )
            )
    return violations


def check_ordering(
    all_grades: dict[str, dict[AnswerQuality, GradeV2]],
) -> OrderingBenchmarkResult:
    """Check ordering across all questions."""
    all_violations: list[OrderingViolation] = []
    questions_with_violations = 0
    for question_id, grades_by_quality in all_grades.items():
        viols = find_violations(question_id=question_id, grades_by_quality=grades_by_quality)
        if viols:
            questions_with_violations += 1
            all_violations.extend(viols)
    return OrderingBenchmarkResult(
        total_questions=len(all_grades),
        questions_with_violations=questions_with_violations,
        all_violations=all_violations,
    )
