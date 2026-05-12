"""Question type registry and rubric-generation prompt templates."""

from enum import Enum


class QuestionType(str, Enum):
    DEFINITION = "definition"
    DISTINCTION = "distinction"
    MECHANISM = "mechanism"
    CLASSIFICATION = "classification"
    ENUMERATION = "enumeration"
    EXAMPLE_GENERATION = "example_generation"
    ERROR_IDENTIFICATION = "error_identification"
    COMPARISON = "comparison"
    APPLICATION = "application"
    PROOF_OR_ARGUMENT = "proof_or_argument"


QUESTION_TYPE_TEMPLATES: dict[str, str] = {
    QuestionType.DEFINITION: (
        "This is a DEFINITION question. Generate checks that test whether the student:\n"
        "  1. States the essential properties (not examples).\n"
        "  2. Uses precise, non-circular language.\n"
        "  3. Distinguishes the defined concept from related ones.\n"
        "Focus checks on concept presence, not vocabulary match.\n"
        "Question: {question}"
    ),
    QuestionType.DISTINCTION: (
        "This is a DISTINCTION question. Generate checks that test whether the student:\n"
        "  1. Names both concepts being contrasted.\n"
        "  2. States the key distinguishing property.\n"
        "  3. Gives at least one example illustrating the distinction.\n"
        "Question: {question}"
    ),
    QuestionType.MECHANISM: (
        "This is a MECHANISM question ('why does X happen?'). Generate checks that test:\n"
        "  1. Presence of the causal chain (A -> B -> C).\n"
        "  2. Correct identification of the breaking point.\n"
        "  3. Statement of what would need to be different for the mechanism to work.\n"
        "Question: {question}"
    ),
    QuestionType.CLASSIFICATION: (
        "This is a CLASSIFICATION question. Generate checks that test:\n"
        "  1. Correct assignment of each item to its category.\n"
        "  2. Stated justification for each assignment.\n"
        "  3. Recognition of edge cases or borderline items.\n"
        "Question: {question}"
    ),
    QuestionType.ENUMERATION: (
        "This is an ENUMERATION question. Generate checks that test:\n"
        "  1. Completeness (all required items listed).\n"
        "  2. Absence of incorrect items.\n"
        "  3. Brief justification for each item if required.\n"
        "Question: {question}"
    ),
    QuestionType.EXAMPLE_GENERATION: (
        "This is an EXAMPLE_GENERATION question. Generate checks that test:\n"
        "  1. The example is valid (satisfies the definition).\n"
        "  2. The student explains why it qualifies.\n"
        "  3. The example is non-trivial (not copied verbatim from course material).\n"
        "Question: {question}"
    ),
    QuestionType.ERROR_IDENTIFICATION: (
        "This is an ERROR_IDENTIFICATION question. Generate checks that test:\n"
        "  1. Correct identification of the specific error.\n"
        "  2. Explanation of why it is an error.\n"
        "  3. Statement of what would be correct instead.\n"
        "Question: {question}"
    ),
    QuestionType.COMPARISON: (
        "This is a COMPARISON question. Generate checks that test:\n"
        "  1. At least one similarity stated.\n"
        "  2. At least one difference stated.\n"
        "  3. Judgment of which approach is better (and under what conditions).\n"
        "Question: {question}"
    ),
    QuestionType.APPLICATION: (
        "This is an APPLICATION question (apply concept to new scenario). Generate checks that test:\n"
        "  1. Correct identification of the relevant concept.\n"
        "  2. Correct application to the specific scenario.\n"
        "  3. Justification grounded in concept properties (not just labeling).\n"
        "Question: {question}"
    ),
    QuestionType.PROOF_OR_ARGUMENT: (
        "This is a PROOF_OR_ARGUMENT question. Generate checks that test:\n"
        "  1. All premises stated explicitly.\n"
        "  2. Each step is logically valid.\n"
        "  3. The conclusion follows from the premises.\n"
        "Question: {question}"
    ),
}


def get_prompt_template(question_type: "QuestionType | str") -> str:
    """Return the rubric-generation prompt fragment for a question type."""
    return QUESTION_TYPE_TEMPLATES[question_type]
