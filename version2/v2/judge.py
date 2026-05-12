"""LLM concept-presence judge.

Two modes (controlled by EvaluationMode):
  SINGLE — one LLM call evaluates all checks for a given answer
  MULTI  — one LLM call per check
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from v2.models import CheckEvalV2, PrecisionLevel, RubricV2

logger = logging.getLogger(__name__)


class EvaluationMode(str, Enum):
    SINGLE = "single"
    MULTI = "multi"


class ConceptJudge:
    """Evaluate an answer against a v2 rubric using an LLM judge."""

    def __init__(self, llm: Any, mode: EvaluationMode = EvaluationMode.SINGLE):
        self.llm = llm
        self.mode = mode

    def evaluate(
        self,
        answer_text: str,
        rubric: RubricV2,
        evidence_context: str,
    ) -> list[CheckEvalV2]:
        """Return one CheckEvalV2 per check across all criteria."""
        all_checks = [c for crit in rubric.criteria for c in crit.checks]
        if self.mode == EvaluationMode.SINGLE:
            return self._evaluate_single(answer_text, all_checks, evidence_context, rubric.question_id)
        else:
            return self._evaluate_multi(answer_text, all_checks, evidence_context, rubric.question_id)

    def _evaluate_single(self, answer_text, all_checks, evidence_context, question_id) -> list[CheckEvalV2]:
        checks_block = "\n".join(
            f"  check_id={c.check_id} type={c.check_type.value} concept={c.concept!r}\n"
            f"    full:    {c.precision_levels[PrecisionLevel.FULL]}\n"
            f"    partial: {c.precision_levels[PrecisionLevel.PARTIAL]}\n"
            f"    none:    {c.precision_levels[PrecisionLevel.NONE]}"
            for c in all_checks
        )
        prompt = (
            f"You are a grading judge for question {question_id}.\n\n"
            f"Student answer:\n{answer_text}\n\n"
            f"Evidence context:\n{evidence_context or 'none'}\n\n"
            f"Checks to evaluate:\n{checks_block}\n\n"
            "For each check, assign precision: full | partial | none.\n"
            "Return ONLY JSON:\n"
            '{"evaluations": [{"check_id": str, "precision": str, "rationale": str}, ...]}\n'
            "JSON:"
        )
        logger.info("  judge [single]: %s — %d checks ...", question_id, len(all_checks))
        response = self.llm.complete(prompt)
        logger.info("  judge [single]: done")
        raw = self._parse_json(response.text)
        logger.debug("  judge [single] raw evals: %s", raw.get("evaluations"))
        return [self._build_eval(e, fallback_id=c.check_id) for e, c in zip(raw["evaluations"], all_checks)]

    def _evaluate_multi(self, answer_text, all_checks, evidence_context, question_id) -> list[CheckEvalV2]:
        evals = []
        for i, check in enumerate(all_checks):
            logger.info("  judge [multi]: %s check %d/%d (%s) ...", question_id, i + 1, len(all_checks), check.check_id)
            prompt = (
                f"You are a grading judge for question {question_id}.\n\n"
                f"Student answer:\n{answer_text}\n\n"
                f"Evidence context:\n{evidence_context or 'none'}\n\n"
                f"Evaluate this ONE check:\n"
                f"  check_id: {check.check_id}\n"
                f"  type: {check.check_type.value}\n"
                f"  concept: {check.concept}\n"
                f"  full:    {check.precision_levels[PrecisionLevel.FULL]}\n"
                f"  partial: {check.precision_levels[PrecisionLevel.PARTIAL]}\n"
                f"  none:    {check.precision_levels[PrecisionLevel.NONE]}\n\n"
                "Assign precision: full | partial | none.\n"
                'Return ONLY JSON: {"check_id": str, "precision": str, "rationale": str}\n'
                "JSON:"
            )
            response = self.llm.complete(prompt)
            logger.info("  judge [multi]: check %d done", i + 1)
            raw = self._parse_json(response.text)
            evals.append(self._build_eval(raw))
        return evals

    def _build_eval(self, e: dict, fallback_id: str | None = None) -> CheckEvalV2:
        check_id = e.get("check_id") or fallback_id
        if check_id is None:
            raise ValueError(f"judge response missing check_id and no fallback available: {e}")
        precision = PrecisionLevel(e["precision"])
        return CheckEvalV2(
            check_id=check_id,
            precision=precision,
            score=precision.to_weight(),
            rationale=e.get("rationale", ""),
        )

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
