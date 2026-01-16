"""LMQL program for citation-enforced grading feedback.

This module implements LMQL constraints to ensure that every explanation
sentence includes citations to evidence sources.

"""

import json
from typing import Any


def validate_explanation(explanation: dict[str, Any], valid_evidence_ids: list[str]) -> bool:
    """Validate that an explanation meets citation requirements.

    Args:
        explanation: Dictionary containing explanation structure with sentences.
        valid_evidence_ids: List of valid evidence source IDs.

    Returns:
        True if explanation is valid, False otherwise.

    """
    if "sentences" not in explanation:
        return False

    sentences = explanation["sentences"]
    if not sentences:
        return False

    for sentence in sentences:
        # Each sentence must have text
        if "text" not in sentence or not sentence["text"]:
            return False

        # Each sentence must have citations
        if "citations" not in sentence or not sentence["citations"]:
            return False

        # Each citation must reference a valid evidence ID
        for citation_id in sentence["citations"]:
            if citation_id not in valid_evidence_ids:
                return False

    return True


def format_grading_prompt(
    grading_record: dict[str, Any],
    evidence_spans: list[dict[str, Any]],
    student_answer: str,
) -> str:
    """Format the prompt for LMQL grading with citation enforcement.

    Args:
        grading_record: Dictionary containing assigned scores per criterion.
        evidence_spans: List of evidence dictionaries with source_id and text.
        student_answer: Student's answer text.

    Returns:
        Formatted prompt string.

    """
    # Extract evidence IDs and format evidence
    evidence_lines = []
    for evidence in evidence_spans:
        source_id = evidence["source_id"]
        text = evidence["text"]
        evidence_lines.append(f"[{source_id}]: {text}")

    evidence_text = "\n".join(evidence_lines)

    # Format grading record
    criteria_lines = []
    for criterion_id, score_info in grading_record.items():
        criteria_lines.append(
            f"- {criterion_id}: {score_info['score']}/{score_info['max_score']} points"
        )
    criteria_text = "\n".join(criteria_lines)

    prompt = f"""You are generating an explanation for a grade that has already been assigned.

You MUST:
- Explain each awarded criterion
- Use only the provided evidence spans
- Attach citations to every sentence using evidence IDs in [brackets]
- Never introduce new facts or information not in the evidence

GRADING RECORD (already decided):
{criteria_text}

AVAILABLE EVIDENCE:
{evidence_text}

STUDENT ANSWER:
{student_answer}

Generate a JSON explanation with this exact structure:
{{
  "sentences": [
    {{
      "text": "Your explanation sentence here.",
      "citations": ["evidence_id_1", "evidence_id_2"]
    }}
  ]
}}

CRITICAL: Every sentence MUST include at least one citation from the available evidence.
"""

    return prompt


def format_batched_grading_prompt(
    students_data: list[dict[str, Any]],
    evidence_spans: list[dict[str, Any]],
) -> str:
    """Format the prompt for batched LMQL grading with multiple students.

    Args:
        students_data: List of dicts, each containing:
            - student_id: Student identifier
            - grading_record: Dictionary mapping criterion_id to score information
            - student_answer: Student's answer text
        evidence_spans: List of evidence dictionaries with source_id and text.

    Returns:
        Formatted prompt string for batched grading.

    """
    # Extract evidence IDs and format evidence
    evidence_lines = []
    for evidence in evidence_spans:
        source_id = evidence["source_id"]
        text = evidence["text"]
        evidence_lines.append(f"[{source_id}]: {text}")

    evidence_text = "\n".join(evidence_lines)

    # Format each student's data
    students_sections = []
    for i, student_data in enumerate(students_data, 1):
        student_id = student_data["student_id"]
        grading_record = student_data["grading_record"]
        student_answer = student_data["student_answer"]

        # Format grading record
        criteria_lines = []
        for criterion_id, score_info in grading_record.items():
            criteria_lines.append(
                f"  - {criterion_id}: {score_info['score']}/{score_info['max_score']} points"
            )
        criteria_text = "\n".join(criteria_lines)

        student_section = f"""
STUDENT {i} ({student_id}):
GRADING RECORD (already decided):
{criteria_text}

STUDENT ANSWER:
{student_answer}
"""
        students_sections.append(student_section)

    students_text = "\n".join(students_sections)

    prompt = f"""You are generating explanations for grades that have already been assigned to multiple students.

You MUST:
- Explain each awarded criterion for EACH student
- Use only the provided evidence spans
- Attach citations to every sentence using evidence IDs in [brackets]
- Never introduce new facts or information not in the evidence
- Generate separate explanations for each student

AVAILABLE EVIDENCE (shared across all students):
{evidence_text}

{students_text}

Generate a JSON explanation with this exact structure:
{{
  "students": [
    {{
      "student_id": "student_1",
      "sentences": [
        {{
          "text": "Your explanation sentence here.",
          "citations": ["evidence_id_1", "evidence_id_2"]
        }}
      ]
    }},
    {{
      "student_id": "student_2",
      "sentences": [
        {{
          "text": "Your explanation sentence here.",
          "citations": ["evidence_id_1"]
        }}
      ]
    }}
  ]
}}

CRITICAL: 
- Generate explanations for ALL {len(students_data)} students
- Every sentence MUST include at least one citation from the available evidence
- Each student's explanation must be in a separate object in the "students" array
"""
    return prompt


def parse_batched_lmql_response(
    response_text: str, expected_student_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Parse batched LMQL response into structured explanations per student.

    Args:
        response_text: Raw response text from LMQL.
        expected_student_ids: List of student IDs that should be in the response.

    Returns:
        Dictionary mapping student_id to explanation dictionary.

    """
    # Extract JSON from response (handle potential markdown code blocks)
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
        if text.endswith("```"):
            text = text[:-3]  # Remove closing ```
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove closing ```

    text = text.strip()

    # Parse JSON
    try:
        response = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LMQL response as JSON: {e}")

    # Extract explanations per student
    if "students" not in response:
        raise ValueError("Response missing 'students' key")

    explanations: dict[str, dict[str, Any]] = {}
    for student_data in response["students"]:
        if "student_id" not in student_data:
            raise ValueError("Student data missing 'student_id'")
        if "sentences" not in student_data:
            raise ValueError(f"Student {student_data['student_id']} missing 'sentences'")

        student_id = student_data["student_id"]
        explanations[student_id] = {
            "sentences": student_data["sentences"],
        }

    # Verify all expected students are present
    missing = set(expected_student_ids) - set(explanations.keys())
    if missing:
        raise ValueError(f"Missing explanations for students: {missing}")

    return explanations


def create_explanation_schema() -> dict[str, Any]:
    """Create JSON schema for explanation structure.

    Returns:
        JSON schema dictionary.

    """
    return {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "citations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                    },
                    "required": ["text", "citations"],
                },
                "minItems": 1,
            }
        },
        "required": ["sentences"],
    }


def parse_lmql_response(response_text: str) -> dict[str, Any]:
    """Parse LMQL response into structured explanation.

    Args:
        response_text: Raw response text from LMQL.

    Returns:
        Parsed explanation dictionary.

    """
    # Extract JSON from response (handle potential markdown code blocks)
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
        if text.endswith("```"):
            text = text[:-3]  # Remove closing ```
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove closing ```

    text = text.strip()

    # Parse JSON
    try:
        explanation = json.loads(text)
        return explanation
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LMQL response as JSON: {e}")


def format_explanation_text(explanation: dict[str, Any]) -> str:
    """Format structured explanation as readable text with inline citations.

    Args:
        explanation: Structured explanation dictionary.

    Returns:
        Formatted text with inline citations.

    """
    lines = []

    for sentence in explanation["sentences"]:
        text = sentence["text"]
        citations = sentence["citations"]

        # Add inline citations
        citation_str = ", ".join(citations)
        lines.append(f"{text} [{citation_str}]")

    return " ".join(lines)


if __name__ == "__main__":
    # Test validation and formatting
    print("Testing LMQL grading utilities...")

    # Test case 1: Valid explanation
    print("\n[Test 1] Valid explanation:")
    valid_explanation = {
        "sentences": [
            {
                "text": "The answer correctly defines mutual information.",
                "citations": ["slide_12"],
            },
            {
                "text": "It also mentions the symmetric property.",
                "citations": ["slide_13"],
            },
        ]
    }

    valid_ids = ["slide_12", "slide_13", "slide_14"]
    is_valid = validate_explanation(valid_explanation, valid_ids)
    print(f"✓ Validation result: {is_valid}")

    formatted = format_explanation_text(valid_explanation)
    print(f"✓ Formatted text: {formatted}")

    # Test case 2: Invalid explanation (missing citation)
    print("\n[Test 2] Invalid explanation (missing citation):")
    invalid_explanation = {
        "sentences": [
            {"text": "The answer is correct.", "citations": []},  # No citations!
        ]
    }

    is_valid = validate_explanation(invalid_explanation, valid_ids)
    print(f"✓ Validation result: {is_valid} (should be False)")

    # Test case 3: Invalid explanation (unknown citation ID)
    print("\n[Test 3] Invalid explanation (unknown citation):")
    invalid_explanation_2 = {
        "sentences": [
            {"text": "The answer is correct.", "citations": ["slide_99"]},  # Unknown ID!
        ]
    }

    is_valid = validate_explanation(invalid_explanation_2, valid_ids)
    print(f"✓ Validation result: {is_valid} (should be False)")

    # Test case 4: Prompt formatting
    print("\n[Test 4] Prompt formatting:")
    grading_record = {
        "definition": {"score": 4, "max_score": 4},
        "properties": {"score": 2, "max_score": 3},
    }

    evidence_spans = [
        {"source_id": "slide_12", "text": "Mutual information measures dependence."},
        {"source_id": "slide_13", "text": "It is symmetric: I(X;Y) = I(Y;X)."},
    ]

    student_answer = "Mutual information tells us about variable relationships."

    prompt = format_grading_prompt(grading_record, evidence_spans, student_answer)
    print("✓ Prompt generated")
    print(f"  Length: {len(prompt)} characters")

    # Test case 5: Response parsing
    print("\n[Test 5] Response parsing:")
    sample_response = """```json
{
  "sentences": [
    {
      "text": "Test sentence.",
      "citations": ["slide_12"]
    }
  ]
}
```"""

    parsed = parse_lmql_response(sample_response)
    print(f"✓ Parsed response: {parsed}")
