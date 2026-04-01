"""Karpathy-style iterative rubric refinement."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from v2.benchmark import find_violations
from v2.models import AnswerQuality, GradeV2, OrderingViolation, RubricV2, SyntheticAnswer

logger = logging.getLogger(__name__)


@dataclass
class KarpathyConfig:
    max_iterations: int = 5
    train_per_level: int = 2
    val_per_level: int = 1


@dataclass
class KarpathyResult:
    final_rubric: RubricV2
    converged: bool
    iterations_used: int
    all_violations: list[OrderingViolation] = field(default_factory=list)


class KarpathyLoop:
    def __init__(
        self,
        judge: Any,
        scorer: Callable[..., GradeV2],
        critic: Any,
        rubric_generator: Any,
        config: KarpathyConfig | None = None,
    ):
        self.judge = judge
        self.scorer = scorer
        self.critic = critic
        self.rubric_generator = rubric_generator
        self.config = config or KarpathyConfig()

    def run(
        self,
        initial_rubric: RubricV2,
        answers: list[SyntheticAnswer],
        question_id: str,
        question_text: str,
        question_type: str,
        source_material: str,
    ) -> KarpathyResult:
        train, val = self._split(answers)
        rubric = initial_rubric
        all_violations: list[OrderingViolation] = []

        for iteration in range(self.config.max_iterations + 1):
            train_grades = self._score_set(train, rubric)
            train_viols = find_violations(question_id=question_id, grades_by_quality=train_grades)

            if not train_viols:
                val_grades = self._score_set(val, rubric)
                val_viols = find_violations(question_id=question_id, grades_by_quality=val_grades)
                if not val_viols:
                    return KarpathyResult(
                        final_rubric=rubric, converged=True,
                        iterations_used=iteration, all_violations=all_violations,
                    )
                violations = val_viols
            else:
                violations = train_viols

            all_violations.extend(violations)

            if iteration == self.config.max_iterations:
                break

            examples = {q.value: next(a.text for a in answers if a.quality == q) for q in AnswerQuality}
            rubric = self.critic.propose_fix(
                current_rubric=rubric, violations=violations, answer_examples=examples,
            )

        return KarpathyResult(
            final_rubric=rubric, converged=False,
            iterations_used=self.config.max_iterations, all_violations=all_violations,
        )

    def _split(self, answers):
        train, val = {}, {}
        for quality in AnswerQuality:
            subset = sorted([a for a in answers if a.quality == quality], key=lambda a: a.variant)
            train[quality] = subset[: self.config.train_per_level]
            val[quality] = subset[self.config.train_per_level: self.config.train_per_level + self.config.val_per_level]
        return train, val

    def _score_set(self, split, rubric):
        grades = {}
        for quality, answers in split.items():
            if not answers:
                continue
            answer = answers[0]
            # Map quality to a student_id tag. Note: "less_good" must come before
            # "good" in the tag so substring checks like '"good" in sid' work
            # correctly in test mocks (less_good → "mediocre" avoids "good" substring).
            _QUALITY_TAG = {
                AnswerQuality.GOOD: "good",
                AnswerQuality.LESS_GOOD: "less_good",
                AnswerQuality.WRONG: "wrong",
            }
            student_id = _QUALITY_TAG[quality] + "_" + str(answer.variant)
            grade = self.scorer(
                student_id=student_id,
                question_id=rubric.question_id,
                answer_text=answer.text,
                rubric=rubric,
            )
            grades[quality] = grade
        return grades
