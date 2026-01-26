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
import re
from datetime import datetime
from pathlib import Path
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
    question_text: str | None = None,
    include_question: bool = True,
    include_criterion_description: bool = True,
) -> str:
    """Format a prompt for grading a single criterion.

    Args:
        criterion_description: Description of the grading criterion.
        max_score: Maximum score weight for this criterion.
        evidence: List of evidence items from sources.
        student_answer: The student's answer text.
        question_text: Optional question text for additional context.
        include_question: If True, include question in the prompt.
        include_criterion_description: If True, include criterion description in prompt.

    Returns:
        Formatted prompt string for the LLM.
    """
    formatted_evidence = _format_evidence_for_prompt(evidence)

    question_section = ""
    if question_text and include_question:
        question_section = f"""QUESTION POSED TO STUDENT:
{question_text}

"""

    criterion_section = ""
    if include_criterion_description:
        criterion_section = f"""GRADING CRITERION (worth {max_score} points in the final grade):
{criterion_description}

"""

    prompt = f"""You are grading a student's answer to a specific criterion for an academic assignment.

{question_section}{criterion_section}EVIDENCE FROM SOURCE MATERIALS:
{formatted_evidence}

STUDENT ANSWER:
{student_answer}

SCORING INSTRUCTIONS:
1. Begin with a score of 10 points.
2. Deduct points ONLY if the answer falls short of the grading criterion requirements.
3. For each deduction, explicitly state what is missing or incorrect.
4. The score must be between 0 and 10.

EVALUATION:
Evaluate whether the student's answer fully addresses the grading criterion based on the evidence provided.
Consider:
- Does the answer demonstrate the understanding required by this grading criterion?
- Are there gaps or missing elements compared to the grading criterion description?
- How well does the provided evidence support or contradict the answer quality?

Respond ONLY in valid JSON format with no additional text:
{{
  "score": <integer from 0 to 10>,
  "feedback": "<Detailed explanation including: (1) What the grading criterion requires (rephrase grading criterion in your own words), (2) How well the answer meets this requirement, (3) If score < 10, explicitly state each deduction and why it was made>"
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
    question_text: str | None = None,
    include_question: bool = True,
    include_criterion_description: bool = True,
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
        question_text: Optional question text for additional context.
        include_question: If True, include question in the prompt.
        include_criterion_description: If True, include criterion description in prompt.

    Returns:
        Dictionary with grading result including score, feedback, metadata, and prompt.
    """
    prompt = _format_criterion_grading_prompt(
        criterion_description=criterion_description,
        max_score=max_score,
        evidence=evidence,
        student_answer=student_answer,
        question_text=question_text,
        include_question=include_question,
        include_criterion_description=include_criterion_description,
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
    grading_failed = False

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
            grading_failed = False
            break

        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing error: {str(e)}"
            if attempt < max_retries - 1:
                continue
            else:
                grading_failed = True
        except (ValueError, KeyError) as e:
            error_msg = f"Invalid response: {str(e)}"
            if attempt < max_retries - 1:
                continue
            else:
                grading_failed = True

    if error_msg:
        feedback = f"Grading error: {error_msg}. Criterion skipped due to persistent LLM response error."

    # Calculate weighted score
    weighted_score = (llm_score / 10.0) * max_score

    return {
        "criterion_id": criterion_id,
        "llm_score": llm_score,
        "max_score": max_score,
        "weighted_score": weighted_score,
        "feedback": feedback,
        "evidence_used": [ev.get("source_id", "unknown") for ev in evidence],
        "prompt": prompt,
        "grading_failed": grading_failed,
    }


def _slugify(text: str) -> str:
    """Convert text to a slug suitable for filenames.

    Args:
        text: Text to slugify.

    Returns:
        Slugified string.
    """
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug.strip("_")


def _save_prompt_readable(
    output_dir: Path,
    question_id: str,
    answer_type: str,
    criterion_id: str,
    prompt: str,
) -> None:
    """Save exact LLM prompt to a readable text file.

    Args:
        output_dir: Directory to save prompt files.
        question_id: Question ID (e.g., "q02").
        answer_type: Answer type (e.g., "good", "less_good", "wrong").
        criterion_id: Criterion ID.
        prompt: The exact LLM prompt sent to the model.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename from question_id, answer_type, and criterion_id
    criterion_slug = _slugify(criterion_id)
    filename = f"prompt_{question_id}_{answer_type}_{criterion_slug}.txt"
    filepath = output_dir / filename

    # Replace curly braces with backticks for readability
    readable_prompt = prompt.replace("{", "`").replace("}", "`")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(readable_prompt)


def grade_student_with_evidence(
    student_id: str,
    student_answer: str,
    question_text: str,
    rubric: dict[str, Any],
    evidence_context: dict[str, Any],
    answer_type: str | None = None,
    include_question: bool = True,
    include_criterion_description: bool = True,
    save_prompts: bool = False,
    prompts_output_dir: Path | None = None,
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
        include_question: If True, include question text in LLM prompt.
        include_criterion_description: If True, include criterion description in prompt.
        save_prompts: If True, save full prompts to JSON files for analysis.
        prompts_output_dir: Directory to save prompt JSON files (if save_prompts=True).

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
            question_text=question_text,
            include_question=include_question,
            include_criterion_description=include_criterion_description,
        )
        criterion_results.append(result)

        # Optionally save prompt for analysis
        if save_prompts and prompts_output_dir:
            _save_prompt_readable(
                output_dir=prompts_output_dir,
                question_id=evidence_context.get("question_id", "unknown"),
                answer_type=answer_type or "unknown",
                criterion_id=result["criterion_id"],
                prompt=result["prompt"],
            )

    # Separate successful and failed criteria
    successful_results = [r for r in criterion_results if not r.get("grading_failed", False)]
    failed_results = [r for r in criterion_results if r.get("grading_failed", False)]

    # Calculate weighted total score based only on successful criteria
    # Adjust max_score to only include successful criteria, so weights sum to original total
    if successful_results:
        total_max_score_successful = sum(r["max_score"] for r in successful_results)
        total_score = 0

        for r in successful_results:
            # Recalculate weighted score with adjusted max_score
            weight = r["max_score"] / total_max_score_successful if total_max_score_successful > 0 else 0
            adjusted_weighted_score = (r["llm_score"] / 10.0) * weight * total_max_score_successful
            total_score += adjusted_weighted_score
    else:
        total_score = 0
        total_max_score_successful = 0

    return {
        "student_id": student_id,
        "question_id": evidence_context.get("question_id", "unknown"),
        "answer_type": answer_type,
        "question_text": question_text,
        "student_answer": student_answer,
        "total_score": round(total_score, 2),
        "max_score": total_max_score_successful,
        "criteria_graded": len(successful_results),
        "criteria_skipped": len(failed_results),
        "skipped_criteria": [
            {
                "criterion_id": r["criterion_id"],
                "reason": r["feedback"],
            }
            for r in failed_results
        ],
        "criterion_results": criterion_results,
        "graded_at": datetime.now().isoformat(),
    }
