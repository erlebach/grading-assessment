"""v2 Rubric generator: source-grounded, answer-informed, concept checks."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from v2.models import AnswerQuality, RubricV2, SyntheticAnswer
from v2.question_types import get_prompt_template
from v2.rubric_schema import parse_rubric_response

logger = logging.getLogger(__name__)


@dataclass
class RubricGeneratorConfig:
    max_checks_per_criterion: int = 4
    max_criteria: int = 6


class RubricGeneratorV2:
    """Generate a v2 concept-check rubric from source material and synthetic answers."""

    def __init__(self, llm: Any, config: RubricGeneratorConfig | None = None):
        self.llm = llm
        self.config = config or RubricGeneratorConfig()

    def generate(
        self,
        question_id: str,
        question_text: str,
        question_type: str,
        source_material: str,
        synthetic_answers: list[SyntheticAnswer],
        version: int = 1,
    ) -> RubricV2:
        """Generate a rubric from source material and synthetic answers."""
        prompt = self._build_prompt(
            question_text=question_text,
            question_type=question_type,
            source_material=source_material,
            synthetic_answers=synthetic_answers,
        )
        response = self.llm.complete(prompt)
        raw = self._parse_json(response.text)
        return parse_rubric_response(
            raw=raw,
            question_id=question_id,
            question_type=question_type,
            version=version,
        )

    def _build_prompt(
        self,
        question_text: str,
        question_type: str,
        source_material: str,
        synthetic_answers: list[SyntheticAnswer],
    ) -> str:
        type_template = get_prompt_template(question_type)
        answers_block = self._format_answers(synthetic_answers)
        return (
            "You are a grading rubric designer. Generate a concept-based grading rubric.\n\n"
            "RUBRIC DESIGN RULES:\n"
            "- Criteria test concept presence, not vocabulary match.\n"
            "- Each check must be vocabulary-agnostic: judge meaning, not words.\n"
            f"- Max {self.config.max_checks_per_criterion} checks per criterion.\n"
            f"- Max {self.config.max_criteria} criteria total.\n"
            "- Precision levels: full=1.0, partial=0.5, none=0.0.\n"
            "- The rubric must discriminate good > less_good > wrong answers.\n\n"
            f"QUESTION TYPE GUIDANCE:\n{type_template}\n\n"
            f"SOURCE MATERIAL (authoritative concepts):\n{source_material}\n\n"
            f"SYNTHETIC ANSWERS (vocabulary grounding):\n{answers_block}\n\n"
            "Return ONLY valid JSON matching this schema exactly:\n"
            '{"criteria": [{"criterion_id": str, "points": float, "checks": ['
            '{"check_id": str, "check_type": str, "concept": str, "points": float, '
            '"precision_levels": {"full": str, "partial": str, "none": str}}]}]}\n'
            "Allowed values for check_type (use exactly one of these strings): "
            '"definition", "distinction", "mechanism", "positive_example", '
            '"negative_example", "generalization".\n'
            "JSON:"
        )

    def _format_answers(self, answers: list[SyntheticAnswer]) -> str:
        sections = []
        for quality in AnswerQuality:
            subset = [a for a in answers if a.quality == quality]
            header = f"--- {quality.value.upper()} ANSWERS ---"
            texts = "\n".join(f"  [{i+1}] {a.text}" for i, a in enumerate(subset))
            sections.append(f"{header}\n{texts}")
        return "\n\n".join(sections)

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response, stripping markdown fences if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
