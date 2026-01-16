"""LMQL-based grading interface with citation enforcement.

This module provides a high-level interface for generating grading feedback
using LMQL with citation constraints enforced.

"""

from typing import Any

from llama_index.core.llms import ChatMessage, LLM, MessageRole

from config.llm_config import configure_llm, load_env_config
from prompts.grading_lmql import (
    format_explanation_text,
    format_grading_prompt,
    parse_lmql_response,
    validate_explanation,
)


class LMQLGrader:
    """LMQL-based grader with citation enforcement."""

    def __init__(self, llm: LLM | None = None) -> None:
        """Initialize the LMQL grader.

        Args:
            llm: Optional LLM instance. If None, uses default from config.

        """
        if llm is None:
            config = load_env_config()
            provider = config["lmql_backend"]
            model = config.get("lmql_model")
            self.llm = configure_llm(provider, model)
        else:
            self.llm = llm

    async def generate_explanation_async(
        self,
        grading_record: dict[str, Any],
        evidence_spans: list[dict[str, Any]],
        student_answer: str,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Generate citation-enforced explanation for grading decision (async).

        Args:
            grading_record: Dictionary mapping criterion_id to score information.
            evidence_spans: List of evidence dictionaries with source_id and text.
            student_answer: Student's answer text.
            max_retries: Maximum number of retry attempts if validation fails.

        Returns:
            Dictionary containing:
            - explanation: Structured explanation with sentences and citations
            - formatted_text: Human-readable explanation with inline citations
            - valid: Whether explanation passed validation

        """
        # Get valid evidence IDs
        valid_evidence_ids = [e["source_id"] for e in evidence_spans]

        # Format prompt
        prompt = format_grading_prompt(grading_record, evidence_spans, student_answer)

        # Try to generate valid explanation
        for attempt in range(max_retries):
            # Generate response using LLM (async)
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content="You are a precise grading assistant that always follows instructions exactly and provides properly cited explanations."),
                ChatMessage(role=MessageRole.USER, content=prompt),
            ]

            response = await self.llm.achat(messages)
            response_text = response.message.content

            # Parse response
            try:
                explanation = parse_lmql_response(response_text)

                # Validate citation completeness
                if validate_explanation(explanation, valid_evidence_ids):
                    # Success!
                    formatted_text = format_explanation_text(explanation)
                    return {
                        "explanation": explanation,
                        "formatted_text": formatted_text,
                        "valid": True,
                        "attempts": attempt + 1,
                    }
                else:
                    # Validation failed, try again
                    if attempt < max_retries - 1:
                        # Add feedback for next attempt
                        prompt += (
                            "\n\nPREVIOUS ATTEMPT FAILED VALIDATION. "
                            "Ensure EVERY sentence has at least one valid citation ID."
                        )
            except (ValueError, KeyError) as e:
                # Parsing failed, try again
                if attempt < max_retries - 1:
                    prompt += f"\n\nPREVIOUS ATTEMPT FAILED PARSING: {e}. Please return valid JSON."

        # All attempts failed
        return {
            "explanation": None,
            "formatted_text": "Error: Could not generate valid cited explanation.",
            "valid": False,
            "attempts": max_retries,
        }

    def generate_explanation(
        self,
        grading_record: dict[str, Any],
        evidence_spans: list[dict[str, Any]],
        student_answer: str,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Generate citation-enforced explanation for grading decision (synchronous).

        Args:
            grading_record: Dictionary mapping criterion_id to score information.
            evidence_spans: List of evidence dictionaries with source_id and text.
            student_answer: Student's answer text.
            max_retries: Maximum number of retry attempts if validation fails.

        Returns:
            Dictionary containing:
            - explanation: Structured explanation with sentences and citations
            - formatted_text: Human-readable explanation with inline citations
            - valid: Whether explanation passed validation

        """
        # Get valid evidence IDs
        valid_evidence_ids = [e["source_id"] for e in evidence_spans]

        # Format prompt
        prompt = format_grading_prompt(grading_record, evidence_spans, student_answer)

        # Try to generate valid explanation
        for attempt in range(max_retries):
            # Generate response using LLM
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content="You are a precise grading assistant that always follows instructions exactly and provides properly cited explanations."),
                ChatMessage(role=MessageRole.USER, content=prompt),
            ]

            response = self.llm.chat(messages)
            response_text = response.message.content

            # Parse response
            try:
                explanation = parse_lmql_response(response_text)

                # Validate citation completeness
                if validate_explanation(explanation, valid_evidence_ids):
                    # Success!
                    formatted_text = format_explanation_text(explanation)
                    return {
                        "explanation": explanation,
                        "formatted_text": formatted_text,
                        "valid": True,
                        "attempts": attempt + 1,
                    }
                else:
                    # Validation failed, try again
                    if attempt < max_retries - 1:
                        # Add feedback for next attempt
                        prompt += (
                            "\n\nPREVIOUS ATTEMPT FAILED VALIDATION. "
                            "Ensure EVERY sentence has at least one valid citation ID."
                        )
            except (ValueError, KeyError) as e:
                # Parsing failed, try again
                if attempt < max_retries - 1:
                    prompt += f"\n\nPREVIOUS ATTEMPT FAILED PARSING: {e}. Please return valid JSON."

        # All attempts failed
        return {
            "explanation": None,
            "formatted_text": "Error: Could not generate valid cited explanation.",
            "valid": False,
            "attempts": max_retries,
        }

    def grade_with_feedback(
        self,
        rubric: dict[str, Any],
        student_answer: str,
        evidence_by_criterion: dict[str, list[dict[str, Any]]],
        scores: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate complete grading with citation-enforced feedback.

        Args:
            rubric: Rubric dictionary with criteria.
            student_answer: Student's answer text.
            evidence_by_criterion: Evidence retrieved for each criterion.
            scores: Assigned scores per criterion.

        Returns:
            Complete grading result with scores and cited feedback.

        """
        # Flatten evidence spans for prompt
        all_evidence = []
        for evidence_list in evidence_by_criterion.values():
            all_evidence.extend(evidence_list)

        # Remove duplicates (keep first occurrence)
        seen_ids = set()
        unique_evidence = []
        for evidence in all_evidence:
            if evidence["source_id"] not in seen_ids:
                unique_evidence.append(evidence)
                seen_ids.add(evidence["source_id"])

        # Generate explanation with citations
        result = self.generate_explanation(
            grading_record=scores,
            evidence_spans=unique_evidence,
            student_answer=student_answer,
        )

        # Build complete grading result
        grading_result = {
            "question_id": rubric.get("question_id", "unknown"),
            "student_answer": student_answer,
            "scores": scores,
            "total_score": sum(s["score"] for s in scores.values()),
            "max_score": sum(s["max_score"] for s in scores.values()),
            "explanation": result["explanation"],
            "feedback": result["formatted_text"],
            "evidence_used": unique_evidence,
            "validation_passed": result["valid"],
        }

        return grading_result

    async def grade_with_feedback_async(
        self,
        rubric: dict[str, Any],
        student_answer: str,
        evidence_by_criterion: dict[str, list[dict[str, Any]]],
        scores: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate complete grading with citation-enforced feedback (async).

        Args:
            rubric: Rubric dictionary with criteria.
            student_answer: Student's answer text.
            evidence_by_criterion: Evidence retrieved for each criterion.
            scores: Assigned scores per criterion.

        Returns:
            Complete grading result with scores and cited feedback.

        """
        # Flatten evidence spans for prompt
        all_evidence = []
        for evidence_list in evidence_by_criterion.values():
            all_evidence.extend(evidence_list)

        # Remove duplicates (keep first occurrence)
        seen_ids = set()
        unique_evidence = []
        for evidence in all_evidence:
            if evidence["source_id"] not in seen_ids:
                unique_evidence.append(evidence)
                seen_ids.add(evidence["source_id"])

        # Generate explanation with citations (async)
        result = await self.generate_explanation_async(
            grading_record=scores,
            evidence_spans=unique_evidence,
            student_answer=student_answer,
        )

        # Build complete grading result
        grading_result = {
            "question_id": rubric.get("question_id", "unknown"),
            "student_answer": student_answer,
            "scores": scores,
            "total_score": sum(s["score"] for s in scores.values()),
            "max_score": sum(s["max_score"] for s in scores.values()),
            "explanation": result["explanation"],
            "feedback": result["formatted_text"],
            "evidence_used": unique_evidence,
            "validation_passed": result["valid"],
        }

        return grading_result


if __name__ == "__main__":
    # Test LMQL grader
    from config.llm_config import setup_llamaindex_defaults

    print("Testing LMQLGrader...")

    # Configure
    setup_llamaindex_defaults()

    # Create grader
    grader = LMQLGrader()
    print("✓ Grader initialized")

    # Test data
    grading_record = {
        "definition": {"score": 4, "max_score": 4},
        "properties": {"score": 2, "max_score": 3},
    }

    evidence_spans = [
        {
            "source_id": "slide_12",
            "text": "Mutual information I(X;Y) measures the reduction in uncertainty about X when Y is observed.",
        },
        {
            "source_id": "slide_13",
            "text": "The mutual information is symmetric: I(X;Y) = I(Y;X).",
        },
        {
            "source_id": "slide_14",
            "text": "Mutual information is always non-negative: I(X;Y) >= 0.",
        },
    ]

    student_answer = """
    Mutual information tells us how much knowing one variable reduces
    uncertainty about another. It works both ways (symmetric).
    """

    print("\n[Test 1] Generate explanation:")
    result = grader.generate_explanation(
        grading_record, evidence_spans, student_answer, max_retries=3
    )

    print(f"✓ Valid: {result['valid']}")
    print(f"  Attempts: {result['attempts']}")
    print(f"  Formatted text: {result['formatted_text'][:100]}...")

    if result["explanation"]:
        print(f"  Number of sentences: {len(result['explanation']['sentences'])}")

    # Test complete grading
    print("\n[Test 2] Complete grading with feedback:")

    rubric = {
        "question_id": "q01",
        "criteria": [
            {"criterion_id": "definition", "description": "Defines mutual information"},
            {"criterion_id": "properties", "description": "States key properties"},
        ],
    }

    scores = {
        "definition": {"score": 4, "max_score": 4},
        "properties": {"score": 2, "max_score": 3},
    }

    evidence_by_criterion = {
        "definition": [evidence_spans[0]],
        "properties": [evidence_spans[1], evidence_spans[2]],
    }

    grading_result = grader.grade_with_feedback(
        rubric, student_answer, evidence_by_criterion, scores
    )

    print(f"✓ Question ID: {grading_result['question_id']}")
    print(f"  Total score: {grading_result['total_score']}/{grading_result['max_score']}")
    print(f"  Validation passed: {grading_result['validation_passed']}")
    print(f"  Feedback: {grading_result['feedback'][:150]}...")
