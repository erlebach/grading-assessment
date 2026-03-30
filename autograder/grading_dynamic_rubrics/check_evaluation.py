"""T3.1 — Evaluate individual rubric checks against student answers using an LLM.

Public API
----------
evaluate_check_llm(
    check, question_text, student_answer,
    evidence=None, llm=None, max_retries=3,
) -> CheckEvaluation

evaluate_checks_llm(
    checks, question_text, student_answer,
    evidence=None, llm=None, max_retries=3,
) -> list[CheckEvaluation]
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from grading_pipeline.models import Check, CheckEvaluation, CheckEvaluationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_EVAL_PROMPT_TEMPLATE = """\
You are a fair and precise academic grader. Your task is to decide whether a \
student's answer satisfies a single grading check.

## Question
{QUESTION_TEXT}

## Grading Check
{CHECK_TEXT}

## Relevant Evidence (course materials / model answer)
{EVIDENCE}

## Student Answer
{STUDENT_ANSWER}

## Instructions
1. Read the check carefully.
2. Decide whether the student's answer satisfies the check.
3. Choose one result:
   - "pass"    — the answer clearly satisfies the check
   - "fail"    — the answer clearly does NOT satisfy the check
   - "unclear" — the answer partially satisfies the check or is ambiguous
4. Provide a brief explanation (1-3 sentences) citing specific phrases from the student's answer.
5. Estimate your confidence (0.0 – 1.0) in your decision.

Respond with ONLY a JSON object in this exact format (no other text):
{{
  "result": "pass" | "fail" | "unclear",
  "evidence": "<brief explanation citing the student's answer>",
  "confidence": <float between 0.0 and 1.0>
}}
"""

_NO_EVIDENCE = "(No additional evidence provided — evaluate based on the question and student answer only.)"


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _call_llm(prompt: str, llm: Any, max_retries: int = 3) -> str:
    """Call the LLM with retries, returning its raw text response."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = llm.complete(prompt)
            raw = response.text
            if raw.strip():
                return raw
            raise ValueError("LLM returned empty response")
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "LLM call attempt %d/%d failed: %s", attempt + 1, max_retries, exc
            )
    raise ValueError(
        f"LLM call failed after {max_retries} attempts"
    ) from last_exc


def _default_llm() -> Any:
    """Create a default Ollama LLM instance."""
    from config.llm_config import configure_llm
    return configure_llm("ollama")


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_llm_response(raw: str, check_id: str) -> dict:
    """Extract the JSON object from the LLM response.

    Handles responses with surrounding whitespace or markdown fences.
    Raises ValueError if no valid JSON with required keys is found.
    """
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()

    # Try the whole string first, then find first {...} block
    candidates = [raw]
    match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
    if match:
        candidates.append(match.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if "result" in data and "evidence" in data:
                return data
        except json.JSONDecodeError:
            continue

    raise ValueError(
        f"Cannot parse LLM response for check '{check_id}'. "
        f"Raw response: {raw[:200]!r}"
    )


# ---------------------------------------------------------------------------
# Result mapping
# ---------------------------------------------------------------------------

_RESULT_MAP: dict[str, CheckEvaluationResult] = {
    "pass": CheckEvaluationResult.PASS,
    "fail": CheckEvaluationResult.FAIL,
    "unclear": CheckEvaluationResult.UNCLEAR,
}

_SCORE_MAP: dict[CheckEvaluationResult, float] = {
    CheckEvaluationResult.PASS: 1.0,
    CheckEvaluationResult.FAIL: 0.0,
    CheckEvaluationResult.UNCLEAR: 0.0,  # unclear treated as fail for scoring
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_check_llm(
    check: Check,
    question_text: str,
    student_answer: str,
    evidence: str | None = None,
    llm: Any = None,
    max_retries: int = 3,
) -> CheckEvaluation:
    """Evaluate a single check against a student answer using an LLM.

    Args:
        check:          The Check object to evaluate.
        question_text:  The original question text.
        student_answer: The student's submitted answer.
        evidence:       Optional reference material / model answer context.
        llm:            LlamaIndex-compatible LLM instance.  If None, a
                        default Ollama instance is created.
        max_retries:    Number of LLM call retries on failure.

    Returns:
        CheckEvaluation with result, score, evidence, and confidence.

    Raises:
        ValueError: If the LLM response cannot be parsed after all retries.
    """
    if llm is None:
        llm = _default_llm()

    evidence_text = evidence if evidence else _NO_EVIDENCE

    prompt = _EVAL_PROMPT_TEMPLATE.format(
        QUESTION_TEXT=question_text,
        CHECK_TEXT=check.text,
        EVIDENCE=evidence_text,
        STUDENT_ANSWER=student_answer,
    )

    raw = _call_llm(prompt, llm, max_retries=max_retries)
    logger.debug("Raw LLM evaluation for check '%s': %s", check.id, raw[:200])

    data = _parse_llm_response(raw, check.id)

    result_str = str(data.get("result", "")).lower().strip()
    result = _RESULT_MAP.get(result_str, CheckEvaluationResult.UNCLEAR)
    if result_str not in _RESULT_MAP:
        logger.warning(
            "Unrecognised result '%s' for check '%s'; defaulting to 'unclear'",
            result_str, check.id,
        )

    score = _SCORE_MAP[result]

    confidence_raw = data.get("confidence", 1.0)
    try:
        confidence = float(confidence_raw)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        logger.warning(
            "Invalid confidence '%s' for check '%s'; defaulting to 1.0",
            confidence_raw, check.id,
        )
        confidence = 1.0

    evidence_text_out = str(data.get("evidence", "")).strip() or "(no explanation provided)"

    return CheckEvaluation(
        check_id=check.id,
        result=result,
        score=score,
        evidence=evidence_text_out,
        confidence=confidence,
        grader="llm",
    )


def evaluate_checks_llm(
    checks: list[Check],
    question_text: str,
    student_answer: str,
    evidence: str | None = None,
    llm: Any = None,
    max_retries: int = 3,
) -> list[CheckEvaluation]:
    """Evaluate a list of checks for a student answer.

    Each check is evaluated independently.  If a single check evaluation
    fails after all retries, the error is logged and a FAIL result with
    confidence=0 is returned for that check so the rest can proceed.

    Args:
        checks:         List of Check objects to evaluate.
        question_text:  The original question text.
        student_answer: The student's submitted answer.
        evidence:       Optional reference material / model answer context.
        llm:            LlamaIndex-compatible LLM instance.
        max_retries:    Number of LLM call retries per check.

    Returns:
        List of CheckEvaluation objects (same order as input checks).
    """
    if llm is None:
        llm = _default_llm()

    results: list[CheckEvaluation] = []
    for check in checks:
        try:
            evaluation = evaluate_check_llm(
                check=check,
                question_text=question_text,
                student_answer=student_answer,
                evidence=evidence,
                llm=llm,
                max_retries=max_retries,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to evaluate check '%s': %s — recording FAIL with confidence=0",
                check.id, exc,
            )
            evaluation = CheckEvaluation(
                check_id=check.id,
                result=CheckEvaluationResult.FAIL,
                score=0.0,
                evidence=f"Evaluation failed: {exc}",
                confidence=0.0,
                grader="llm",
            )
        results.append(evaluation)

    return results
