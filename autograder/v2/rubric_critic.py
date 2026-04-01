"""Rubric critic: receives violations, proposes a rubric fix via LLM."""

from __future__ import annotations

import json
import logging
from typing import Any

from v2.models import OrderingViolation, RubricV2
from v2.rubric_schema import parse_rubric_response

logger = logging.getLogger(__name__)

_CRITIC_SYSTEM = """
You are a rubric critic. Your job is to fix an assessment rubric that has
ordering violations: some wrong answers score higher than less_good answers,
or some less_good answers score higher than good answers.

Rules for a good fix:
1. Do not simply lower thresholds — improve check *discrimination*.
2. Do not add checks that only distinguish the specific failing answers
   (this is overfitting). Generalise the principle.
3. Stay within the complexity budget: max 4 checks per criterion.
4. Keep checks vocabulary-agnostic (concept presence, not keyword match).
5. Return ONLY the fixed rubric JSON with the same schema as the input.
"""


class RubricCritic:
    """Propose rubric improvements to fix ordering violations."""

    def __init__(self, llm: Any):
        self.llm = llm

    def propose_fix(
        self,
        current_rubric: RubricV2,
        violations: list[OrderingViolation],
        answer_examples: dict[str, str],
    ) -> RubricV2:
        """Return a revised rubric that should fix the violations."""
        rubric_json = self._rubric_to_dict(current_rubric)
        violations_text = "\n".join(
            f"  - {v.description} (pair: {v.bad_pair[0]} vs {v.bad_pair[1]})"
            for v in violations
        )
        examples_text = "\n\n".join(
            f"[{label.upper()} answer]\n{text}"
            for label, text in answer_examples.items()
        )
        prompt = (
            f"{_CRITIC_SYSTEM}\n\n"
            f"CURRENT RUBRIC (JSON):\n{json.dumps(rubric_json, indent=2)}\n\n"
            f"ORDERING VIOLATIONS:\n{violations_text}\n\n"
            f"EXAMPLE ANSWERS:\n{examples_text}\n\n"
            "Return the fixed rubric JSON only (same schema):\n"
            "JSON:"
        )
        response = self.llm.complete(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        raw = json.loads(text)
        return parse_rubric_response(
            raw=raw,
            question_id=current_rubric.question_id,
            question_type=current_rubric.question_type,
            version=current_rubric.version + 1,
        )

    def _rubric_to_dict(self, rubric: RubricV2) -> dict:
        from v2.models import PrecisionLevel
        return {
            "criteria": [
                {
                    "criterion_id": crit.criterion_id,
                    "points": crit.points,
                    "checks": [
                        {
                            "check_id": c.check_id,
                            "check_type": c.check_type.value,
                            "concept": c.concept,
                            "points": c.points,
                            "precision_levels": {
                                "full": c.precision_levels[PrecisionLevel.FULL],
                                "partial": c.precision_levels[PrecisionLevel.PARTIAL],
                                "none": c.precision_levels[PrecisionLevel.NONE],
                            },
                        }
                        for c in crit.checks
                    ],
                }
                for crit in rubric.criteria
            ]
        }
