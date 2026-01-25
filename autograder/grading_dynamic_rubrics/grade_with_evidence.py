"""Grading function for dynamic rubrics using LLM with preprocessed evidence.

This module implements semantic-only LLM-based grading using preprocessed
evidence context. Each criterion is graded independently by the LLM,
and scores are weighted according to the max_score values.

Key design:
- No keyword overlap checks (semantic only)
- LLM decides scores directly (0-10 scale per criterion)
- Per-criterion LLM calls (one call per criterion)
- Weighted total score based on max_score values
- Error handling with retry logic for LLM failures
"""

import json
from datetime import datetime
from typing import Any

from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole

from config.llm_config import setup_llamaindex_defaults


def _format_evidence_for_prompt(evidence: list[dict]) -> str:
    """Format evidence items into readable text for the LLM prompt.

    Args:
        evidence: List of evidence dicts with texts, scores, and source_ids.

    Returns:
        Formatted evidence string for inclusion in the prompt.
    """
    formatted = []

    for i, item in enumerate(evidence, 1):
        source_id = item.get("source_id", "unknown")
        texts = item.get("texts", [])
        reranker_score = item.get("reranker_scores", [0])[0]

        if texts:
            text_content = texts[0][:500]  # Limit text length
            formatted.append(
                f"[{i}] Source: {source_id}\n"
                f"    Text: {text_content}\n"
                f"    Relevance Score: {reranker_score:.3f}"
            )

    if not formatted:
        return "No evidence provided."

    return "\n\n".join(formatted)


def _format_criterion_grading_prompt(
    criterion_description: str,
    max_score: int,
    evidence: list[dict],
    student_answer: str,
) -> str:
    """Format a prompt for grading a single criterion.

    Args:
        criterion_description: Description of the grading criterion.
        max_score: Maximum score weight for this criterion.
        evidence: List of evidence items from sources.
        student_answer: The student's answer text.

    Returns:
        Formatted prompt string for the LLM.
    """
    formatted_evidence = _format_evidence_for_prompt(evidence)

    prompt = f"""You are grading a student's answer to a specific criterion for an academic assignment.

CRITERION:
{criterion_description}

CRITERION WEIGHT: This criterion is worth {max_score} points in the final grade (out of 10 possible points).

EVIDENCE FROM SOURCE MATERIALS:
{formatted_evidence}

STUDENT ANSWER:
{student_answer}

TASK:
Grade the student's answer on this specific criterion only. Use ONLY the provided evidence to support your grading decision.
Award a score from 0 to 10 based on how well the answer addresses this criterion:
- 0-3: Poor (major gaps or errors; does not address the criterion)
- 4-6: Adequate (partial understanding; addresses some but not all aspects)
- 7-9: Good (solid understanding with minor gaps or incomplete coverage)
- 10: Excellent (comprehensive and accurate; fully addresses the criterion)

Respond ONLY in valid JSON format with no additional text:
{{
  "score": <integer from 0 to 10>,
  "feedback": "<brief explanation of the score and how the answer addresses this criterion>"
}}"""

    return prompt


def _grade_criterion(
    criterion_id: str,
    criterion_description: str,
    max_score: int,
    evidence: list[dict],
    student_answer: str,
    llm: Any,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Grade a single criterion using the LLM.

    Args:
        criterion_id: ID of the criterion being graded.
        criterion_description: Description of the criterion.
        max_score: Maximum score weight for this criterion.
        evidence: List of evidence items.
        student_answer: The student's answer text.
        llm: The LLM instance to use for grading.
        max_retries: Maximum number of retry attempts.

    Returns:
        Dictionary with grading result including score, feedback, and metadata.
    """
    prompt = _format_criterion_grading_prompt(
        criterion_description=criterion_description,
        max_score=max_score,
        evidence=evidence,
        student_answer=student_answer,
    )

    messages = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content="You are a precise grading assistant. You respond only with valid JSON.",
        ),
        ChatMessage(role=MessageRole.USER, content=prompt),
    ]

    llm_score = 0
    feedback = "Error: Failed to grade this criterion"
    error_msg = None

    for attempt in range(max_retries):
        try:
            response = llm.chat(messages)
            response_text = response.message.content.strip()

            # Parse JSON response
            result = json.loads(response_text)

            # Validate required fields
            if "score" not in result or "feedback" not in result:
                raise ValueError("Missing required fields: score or feedback")

            # Validate score is numeric and in valid range
            if not isinstance(result["score"], (int, float)):
                raise ValueError(f"Score must be numeric, got {type(result['score'])}")

            llm_score = int(max(0, min(result["score"], 10)))
            feedback = str(result.get("feedback", "No feedback provided"))
            error_msg = None
            break

        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing error: {str(e)}"
            if attempt < max_retries - 1:
                continue
        except (ValueError, KeyError) as e:
            error_msg = f"Invalid response: {str(e)}"
            if attempt < max_retries - 1:
                continue

    if error_msg:
        feedback = f"Grading error: {error_msg}. Defaulting to 0 points."

    # Calculate weighted score
    weighted_score = (llm_score / 10.0) * max_score

    return {
        "criterion_id": criterion_id,
        "llm_score": llm_score,
        "max_score": max_score,
        "weighted_score": weighted_score,
        "feedback": feedback,
        "evidence_used": [ev.get("source_id", "unknown") for ev in evidence],
    }


def grade_student_with_evidence(
    student_id: str,
    student_answer: str,
    question_text: str,
    rubric: dict[str, Any],
    evidence_context: dict[str, Any],
    answer_type: str | None = None,
) -> dict[str, Any]:
    """Grade a student using preprocessed evidence context.

    This function grades each criterion independently using LLM calls.
    The LLM decides scores on a 0-10 scale for each criterion, which are
    then weighted according to the max_score values to produce the final score.

    Args:
        student_id: Student identifier.
        student_answer: Student's answer text.
        question_text: Question text.
        rubric: Rubric dictionary (not used in this approach).
        evidence_context: Evidence context from preprocessing with:
            - question_id: Question ID
            - question_text: Question text
            - grading_context: List of criterion objects with evidence
        answer_type: Optional answer type label (e.g., "good", "less_good").

    Returns:
        Dictionary with grading result including:
        - student_id, question_id, answer_type
        - total_score (weighted sum), max_score
        - criterion_results: List of per-criterion grades
        - graded_at: ISO timestamp
    """
    # Initialize LLM if not already configured
    try:
        llm = Settings.llm
        if llm is None:
            raise ValueError("LLM not configured")
    except (AttributeError, ValueError):
        setup_llamaindex_defaults()
        llm = Settings.llm

    # Grade each criterion
    criterion_results = []

    for criterion_ctx in evidence_context.get("grading_context", []):
        result = _grade_criterion(
            criterion_id=criterion_ctx.get("criterion_id", "unknown"),
            criterion_description=criterion_ctx.get("criterion_description", ""),
            max_score=criterion_ctx.get("max_score", 1),
            evidence=criterion_ctx.get("evidence", []),
            student_answer=student_answer,
            llm=llm,
        )
        criterion_results.append(result)

    # Calculate weighted total score
    # Each criterion's LLM score is 0-10; weighted by max_score
    total_score = sum(r["weighted_score"] for r in criterion_results)
    total_max_score = sum(r["max_score"] for r in criterion_results)

    return {
        "student_id": student_id,
        "question_id": evidence_context.get("question_id", "unknown"),
        "answer_type": answer_type,
        "question_text": question_text,
        "student_answer": student_answer,
        "total_score": round(total_score, 2),
        "max_score": total_max_score,
        "criterion_results": criterion_results,
        "graded_at": datetime.now().isoformat(),
    }
