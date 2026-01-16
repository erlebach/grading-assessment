"""LMQL-based grading interface with citation enforcement.

This module provides a high-level interface for generating grading feedback
using LMQL with citation constraints enforced.

"""

from typing import Any

from llama_index.core.llms import LLM, ChatMessage, MessageRole

from config.llm_config import configure_llm, load_env_config
from prompts.grading_lmql import (
    format_batched_grading_prompt,
    format_explanation_text,
    format_grading_prompt,
    parse_batched_lmql_response,
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

    def _print_token_usage(
        self, response: Any, prompt: str, response_text: str, mode: str = "single"
    ) -> None:
        """Print token usage information from LLM response.

        Args:
            response: LLM response object.
            prompt: The prompt text sent to the LLM.
            response_text: The response text from the LLM.
            mode: "single" for single student, "batched" for multiple students.

        """
        # Try to extract token usage from response object (use try/except for speed)
        input_tokens = None
        output_tokens = None
        total_tokens = None

        # Try response.usage first (most common location)
        try:
            usage = response.usage
            input_tokens = getattr(usage, "prompt_tokens", None)
            output_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
        except (AttributeError, TypeError):
            pass

        # Try response.raw.usage as fallback
        if input_tokens is None:
            try:
                usage = response.raw.usage
                input_tokens = getattr(usage, "prompt_tokens", None)
                output_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
            except (AttributeError, TypeError):
                pass

        # Estimate tokens if not available (rough approximation: ~4 chars per token)
        if input_tokens is None:
            input_tokens = int((len(prompt) + 150) / 4)  # 150 for system message
        if output_tokens is None:
            output_tokens = int(len(response_text) / 4)
        if total_tokens is None:
            total_tokens = input_tokens + output_tokens

        # Print token usage
        mode_label = "Batched" if mode == "batched" else "Single"
        print(f"\n  [{mode_label} Mode] Context Usage:")
        print(f"    Input tokens:  {input_tokens:,}")
        print(f"    Output tokens: {output_tokens:,}")
        print(f"    Total tokens:  {total_tokens:,}")
        if mode == "batched":
            # Use a faster method to count students (only count "STUDENT " prefix)
            num_students = len([line for line in prompt.split("\n") if "STUDENT " in line])
            if num_students > 0:
                print(f"    Avg per student: {total_tokens // num_students:,} tokens")

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
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a precise grading assistant that always follows instructions exactly and provides properly cited explanations.",
                ),
                ChatMessage(role=MessageRole.USER, content=prompt),
            ]

            response = await self.llm.achat(messages)
            response_text = response.message.content

            # Parse response
            try:
                explanation = parse_lmql_response(response_text)

                # Validate citation completeness
                if validate_explanation(explanation, valid_evidence_ids):
                    # Success! Print token usage only on success
                    self._print_token_usage(response, prompt, response_text, mode="single")
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
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a precise grading assistant that always follows instructions exactly and provides properly cited explanations.",
                ),
                ChatMessage(role=MessageRole.USER, content=prompt),
            ]

            response = self.llm.chat(messages)
            response_text = response.message.content

            # Parse response
            try:
                explanation = parse_lmql_response(response_text)

                # Validate citation completeness
                if validate_explanation(explanation, valid_evidence_ids):
                    # Success! Print token usage only on success
                    self._print_token_usage(response, prompt, response_text, mode="single")
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

    async def grade_batch_async(
        self,
        rubric: dict[str, Any],
        students_data: list[dict[str, Any]],
        max_retries: int = 3,
    ) -> dict[str, dict[str, Any]]:
        """Grade multiple students in a single LLM call (batched).

        Args:
            rubric: Rubric dictionary with criteria.
            students_data: List of dicts, each containing:
                - student_id: Student identifier
                - student_answer: Student's answer text
                - evidence_by_criterion: Evidence retrieved for each criterion
                - scores: Assigned scores per criterion
            max_retries: Maximum number of retry attempts if validation fails.

        Returns:
            Dictionary mapping student_id to complete grading result.

        """
        # Collect all unique evidence across all students
        all_evidence_ids = set()
        all_evidence_map: dict[str, dict[str, Any]] = {}
        for student_data in students_data:
            evidence_by_criterion = student_data["evidence_by_criterion"]
            for evidence_list in evidence_by_criterion.values():
                for evidence in evidence_list:
                    source_id = evidence["source_id"]
                    all_evidence_ids.add(source_id)
                    if source_id not in all_evidence_map:
                        all_evidence_map[source_id] = evidence

        unique_evidence = list(all_evidence_map.values())
        valid_evidence_ids = list(all_evidence_ids)

        # Prepare students data for prompt
        prompt_students_data = []
        for student_data in students_data:
            prompt_students_data.append(
                {
                    "student_id": student_data["student_id"],
                    "grading_record": student_data["scores"],
                    "student_answer": student_data["student_answer"],
                }
            )

        # Format batched prompt
        prompt = format_batched_grading_prompt(prompt_students_data, unique_evidence)

        # Try to generate valid explanations for all students
        for attempt in range(max_retries):
            # Generate response using LLM (async)
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a precise grading assistant that always follows instructions exactly and provides properly cited explanations for multiple students.",
                ),
                ChatMessage(role=MessageRole.USER, content=prompt),
            ]

            response = await self.llm.achat(messages)
            response_text = response.message.content

            # Parse batched response
            try:
                explanations = parse_batched_lmql_response(
                    response_text, [s["student_id"] for s in students_data]
                )

                # Validate all explanations
                all_valid = True
                for student_id, explanation in explanations.items():
                    if not validate_explanation(explanation, valid_evidence_ids):
                        all_valid = False
                        break

                if all_valid:
                    # Success! Print token usage only on success
                    self._print_token_usage(response, prompt, response_text, mode="batched")
                    # Build results for each student
                    results: dict[str, dict[str, Any]] = {}
                    for student_data in students_data:
                        student_id = student_data["student_id"]
                        explanation = explanations[student_id]
                        formatted_text = format_explanation_text(explanation)

                        results[student_id] = {
                            "question_id": rubric.get("question_id", "unknown"),
                            "student_answer": student_data["student_answer"],
                            "scores": student_data["scores"],
                            "total_score": sum(
                                s["score"] for s in student_data["scores"].values()
                            ),
                            "max_score": sum(
                                s["max_score"] for s in student_data["scores"].values()
                            ),
                            "explanation": explanation,
                            "feedback": formatted_text,
                            "evidence_used": unique_evidence,
                            "validation_passed": True,
                        }
                    return results
                else:
                    # Validation failed, try again
                    if attempt < max_retries - 1:
                        prompt += (
                            "\n\nPREVIOUS ATTEMPT FAILED VALIDATION. "
                            "Ensure EVERY sentence for EVERY student has at least one valid citation ID."
                        )
            except (ValueError, KeyError) as e:
                # Parsing failed, try again
                if attempt < max_retries - 1:
                    prompt += f"\n\nPREVIOUS ATTEMPT FAILED PARSING: {e}. Please return valid JSON with all students."

        # All attempts failed - return error results
        results: dict[str, dict[str, Any]] = {}
        for student_data in students_data:
            student_id = student_data["student_id"]
            results[student_id] = {
                "question_id": rubric.get("question_id", "unknown"),
                "student_answer": student_data["student_answer"],
                "scores": student_data["scores"],
                "total_score": sum(s["score"] for s in student_data["scores"].values()),
                "max_score": sum(
                    s["max_score"] for s in student_data["scores"].values()
                ),
                "explanation": None,
                "feedback": "Error: Could not generate valid cited explanation.",
                "evidence_used": unique_evidence,
                "validation_passed": False,
            }
        return results


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
    print(
        f"  Total score: {grading_result['total_score']}/{grading_result['max_score']}"
    )
    print(f"  Validation passed: {grading_result['validation_passed']}")
    print(f"  Feedback: {grading_result['feedback'][:150]}...")
