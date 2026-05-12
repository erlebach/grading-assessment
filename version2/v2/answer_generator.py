"""Generate 3x3 synthetic answers per question (good / less_good / wrong)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from v2.models import AnswerQuality, SyntheticAnswer

logger = logging.getLogger(__name__)

_QUALITY_INSTRUCTIONS: dict[AnswerQuality, str] = {
    AnswerQuality.GOOD: (
        "Write a GOOD student answer: complete, precise, correct, with a concrete example. "
        "Use your own words — do not copy the source verbatim."
    ),
    AnswerQuality.LESS_GOOD: (
        "Write a LESS_GOOD student answer: correct main concept but vague, "
        "missing the causal mechanism or a concrete example."
    ),
    AnswerQuality.WRONG: (
        "Write a WRONG student answer: plausible-sounding but conceptually incorrect. "
        "Include a common misconception."
    ),
}


@dataclass
class AnswerGeneratorConfig:
    variants_per_level: int = 3
    temperature: float = 0.7


class AnswerGenerator:
    """Generate synthetic answers using an LLM."""

    def __init__(self, llm: Any, config: AnswerGeneratorConfig | None = None):
        self.llm = llm
        self.config = config or AnswerGeneratorConfig()

    def generate(
        self,
        question_id: str,
        question_text: str,
        question_type: str,
        source_material: str,
    ) -> list[SyntheticAnswer]:
        """Generate 9 synthetic answers (3 per quality level)."""
        results: list[SyntheticAnswer] = []
        for quality in AnswerQuality:
            for variant in range(1, self.config.variants_per_level + 1):
                prompt = self._build_prompt(
                    question_text=question_text,
                    question_type=question_type,
                    source_material=source_material,
                    quality=quality,
                    variant=variant,
                )
                logger.info("  answer_gen: %s variant %d/%d ...", quality.value, variant, self.config.variants_per_level)
                response = self.llm.complete(prompt)
                logger.info("  answer_gen: %s variant %d done", quality.value, variant)
                results.append(
                    SyntheticAnswer(
                        question_id=question_id,
                        quality=quality,
                        variant=variant,
                        text=response.text.strip(),
                    )
                )
        return results

    def _build_prompt(
        self,
        question_text: str,
        question_type: str,
        source_material: str,
        quality: AnswerQuality,
        variant: int,
    ) -> str:
        instruction = _QUALITY_INSTRUCTIONS[quality]
        return (
            f"You are generating a synthetic student answer for assessment research.\n\n"
            f"Question type: {question_type}\n"
            f"Question: {question_text}\n\n"
            f"Relevant course material:\n{source_material}\n\n"
            f"Task: {instruction}\n"
            f"Variant {variant} of {self.config.variants_per_level} "
            f"(vary phrasing from other variants).\n\n"
            f"Write only the student answer, no preamble:"
        )
