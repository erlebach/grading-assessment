"""v2 Pipeline: orchestrates answer generation → rubric generation →
Karpathy refinement → LLM-judge scoring for each student answer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from v2.models import GradeV2, SyntheticAnswer
from v2.scoring import compute_grade

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    evaluation_mode: str = "single"
    model_tier: str = "foundational"


class PipelineV2:
    """Full v2 grading pipeline."""

    def __init__(
        self,
        answer_generator: Any,
        rubric_generator: Any,
        karpathy_loop: Any,
        judge: Any,
        config: PipelineConfig | None = None,
    ):
        self.answer_generator = answer_generator
        self.rubric_generator = rubric_generator
        self.karpathy_loop = karpathy_loop
        self.judge = judge
        self.config = config or PipelineConfig()

    def run(
        self,
        question_id: str,
        question_text: str,
        question_type: str,
        source_material: str,
        student_answers: dict[str, str],
        synthetic_answers: list[SyntheticAnswer] | None = None,
        evidence_context: str = "",
    ) -> dict:
        """Run the full pipeline for one question."""
        if synthetic_answers is None:
            synthetic_answers = self.answer_generator.generate(
                question_id=question_id,
                question_text=question_text,
                question_type=question_type,
                source_material=source_material,
            )

        initial_rubric = self.rubric_generator.generate(
            question_id=question_id,
            question_text=question_text,
            question_type=question_type,
            source_material=source_material,
            synthetic_answers=synthetic_answers,
            version=1,
        )

        karpathy_result = self.karpathy_loop.run(
            initial_rubric=initial_rubric,
            answers=synthetic_answers,
            question_id=question_id,
            question_text=question_text,
            question_type=question_type,
            source_material=source_material,
        )
        final_rubric = karpathy_result.final_rubric

        student_grades: dict[str, GradeV2] = {}
        for student_id, answer_text in student_answers.items():
            check_evals = self.judge.evaluate(
                answer_text=answer_text,
                rubric=final_rubric,
                evidence_context=evidence_context,
            )
            grade = compute_grade(
                grade_id=f"{student_id}_{question_id}",
                question_id=question_id,
                student_id=student_id,
                rubric=final_rubric,
                check_evaluations=check_evals,
                evaluation_mode=self.config.evaluation_mode,
                model_tier=self.config.model_tier,
            )
            student_grades[student_id] = grade

        return {
            "rubric": final_rubric,
            "student_grades": student_grades,
            "converged": karpathy_result.converged,
            "iterations": karpathy_result.iterations_used,
        }
