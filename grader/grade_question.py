"""Grade a single question against a rubric."""

from pathlib import Path
from typing import Any

import yaml

from config.llm_config import setup_llamaindex_defaults
from evidence.build_index import load_saved_index
from evidence.retriever import EvidenceRetriever
from grader.evidence_retriever import GradingEvidenceRetriever
from grader.lmql_grading import LMQLGrader


def load_rubric(rubric_path: Path) -> dict[str, Any]:
    """Load rubric from YAML file.

    Args:
        rubric_path: Path to the rubric YAML file.

    Returns:
        Dictionary containing rubric structure.

    """
    with open(rubric_path, "r") as f:
        return yaml.safe_load(f)


def load_submission(submission_path: Path) -> str:
    """Load student submission content.

    Args:
        submission_path: Path to the submission file.

    Returns:
        Content of the submission file as a string.

    """
    with open(submission_path, "r") as f:
        return f.read()


def apply_rubric_scoring(
    rubric: dict[str, Any],
    student_answer: str,
    evidence_by_criterion: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Apply rubric criteria to assign scores.

    This is a simplified implementation that uses keyword matching.
    In a production system, this would use more sophisticated semantic
    analysis or human-in-the-loop grading.

    Args:
        rubric: Rubric dictionary with criteria.
        student_answer: Student's answer text.
        evidence_by_criterion: Evidence retrieved for each criterion.

    Returns:
        Dictionary mapping criterion_id to score information, including
        keyword tracking for feedback purposes.

    """
    scores = {}
    answer_lower = student_answer.lower()

    for criterion in rubric.get("criteria", []):
        criterion_id = criterion["criterion_id"]
        max_points = criterion["points"]
        description = criterion["description"].lower()

        # Simple heuristic scoring based on keyword presence
        # In production, this would be more sophisticated
        keywords = extract_keywords(description)

        # Track which keywords were found and which were missing
        found_keywords = [kw for kw in keywords if kw in answer_lower]
        missing_keywords = [kw for kw in keywords if kw not in answer_lower]
        matches = len(found_keywords)

        # Score proportionally to keyword matches
        if keywords:
            score = int((matches / len(keywords)) * max_points)
        else:
            # If no keywords, check if evidence was found
            score = max_points if criterion_id in evidence_by_criterion else 0

        scores[criterion_id] = {
            "score": score,
            "max_score": max_points,
            "keywords": keywords,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
        }

    return scores


def extract_keywords(description: str) -> list[str]:
    """Extract key terms from criterion description.

    Filters out meta-words (instructional words about what students should do)
    and keeps only substantive keywords related to the subject matter.

    Args:
        description: Criterion description text.

    Returns:
        List of keywords related to the subject matter.

    """
    # Common stop words (articles, prepositions, etc.)
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "is",
        "are",
        "was",
        "were",
    }

    # Meta-words: instructional words that describe the task, not the subject
    # These should not be required keywords since they're about what to do,
    # not what the answer should contain
    meta_words = {
        "correctly",
        "defines",
        "define",
        "explains",
        "explain",
        "relates",
        "relate",
        "describes",
        "describe",
        "discusses",
        "discuss",
        "identifies",
        "identify",
        "lists",
        "list",
        "properties",  # "key properties" is about structure, not content
        "property",
        "concepts",  # "entropy concepts" - "concepts" is meta
        "concept",
        "key",  # "key properties" - "key" is meta
        "like",  # "like X and Y" - "like" is a comparison word
        "such",  # "such as" - comparison word
        "should",
        "must",
        "needs",
        "need",
    }

    words = description.lower().split()
    keywords = [
        w.strip(",.!?")
        for w in words
        if w not in stop_words and w not in meta_words and len(w) > 3
    ]

    return keywords


def grade_question(
    submission_path: Path,
    rubric_path: Path,
    evidence_index_path: Path | None = None,
) -> dict[str, Any]:
    """Grade a single question using the provided rubric.

    This implements the complete grading pipeline:
    1. Load rubric and submission
    2. Retrieve evidence (if index provided)
    3. Apply rubric-driven scoring
    4. Generate LMQL-constrained feedback with citations

    Args:
        submission_path: Path to the student submission file.
        rubric_path: Path to the rubric YAML file.
        evidence_index_path: Optional path to the evidence index for RAG.

    Returns:
        Dictionary containing:
        - question_id: Question identifier
        - score: Total numeric score
        - max_score: Maximum possible score
        - feedback: Text feedback with citations
        - citations: List of evidence citations
        - rubric_items: Breakdown by rubric criterion

    """
    # Setup
    setup_llamaindex_defaults()

    # Load rubric and submission
    rubric = load_rubric(rubric_path)
    submission = load_submission(submission_path)

    # Initialize evidence retrieval if index provided
    evidence_by_criterion = {}
    if evidence_index_path and evidence_index_path.exists():
        # Load index
        index = load_saved_index(evidence_index_path)

        if index:
            # Create retrievers
            base_retriever = EvidenceRetriever(index)
            grading_retriever = GradingEvidenceRetriever(base_retriever)

            # Retrieve evidence for rubric criteria
            evidence_by_criterion = grading_retriever.retrieve_for_rubric(
                rubric, submission, top_k_per_criterion=3
            )

    # Apply rubric-driven scoring (deterministic, before feedback)
    scores = apply_rubric_scoring(rubric, submission, evidence_by_criterion)

    # Calculate total score
    total_score = sum(s["score"] for s in scores.values())
    max_score = rubric.get("total_points", sum(s["max_score"] for s in scores.values()))

    # Generate feedback with LMQL citation enforcement (if evidence available)
    if evidence_by_criterion:
        lmql_grader = LMQLGrader()

        grading_result = lmql_grader.grade_with_feedback(
            rubric=rubric,
            student_answer=submission,
            evidence_by_criterion=evidence_by_criterion,
            scores=scores,
        )

        feedback = grading_result["feedback"]
        citations = grading_result.get("evidence_used", [])
    else:
        # No evidence index, generate simple feedback
        feedback = generate_simple_feedback(rubric, scores)
        citations = []

    # Build rubric items breakdown
    rubric_items = []
    for criterion in rubric.get("criteria", []):
        criterion_id = criterion["criterion_id"]
        if criterion_id in scores:
            item = {
                "criterion_id": criterion_id,
                "description": criterion["description"],
                "score": scores[criterion_id]["score"],
                "max_score": scores[criterion_id]["max_score"],
            }
            # Preserve keyword information if available
            if "keywords" in scores[criterion_id]:
                item["keywords"] = scores[criterion_id].get("keywords", [])
                item["found_keywords"] = scores[criterion_id].get("found_keywords", [])
                item["missing_keywords"] = scores[criterion_id].get(
                    "missing_keywords", []
                )
            rubric_items.append(item)

    return {
        "question_id": rubric.get("question_id", "unknown"),
        "score": total_score,
        "max_score": max_score,
        "feedback": feedback,
        "citations": citations,
        "rubric_items": rubric_items,
    }


def generate_simple_feedback(
    rubric: dict[str, Any], scores: dict[str, dict[str, Any]]
) -> str:
    """Generate simple feedback without evidence citations.

    Args:
        rubric: Rubric dictionary.
        scores: Score information per criterion.

    Returns:
        Feedback text with keyword information.

    """
    lines = ["Grading Summary:\n"]

    for criterion in rubric.get("criteria", []):
        criterion_id = criterion["criterion_id"]
        if criterion_id in scores:
            score_info = scores[criterion_id]
            lines.append(
                f"- {criterion['description']}: "
                f"{score_info['score']}/{score_info['max_score']} points"
            )

            # Add keyword information if available
            if "keywords" in score_info:
                keywords = score_info.get("keywords", [])
                found_keywords = score_info.get("found_keywords", [])
                missing_keywords = score_info.get("missing_keywords", [])

                if keywords:
                    lines.append(f"  Keywords checked: {', '.join(keywords)}")
                    if found_keywords:
                        lines.append(f"  ✓ Found: {', '.join(found_keywords)}")
                    if missing_keywords:
                        lines.append(f"  ✗ Missing: {', '.join(missing_keywords)}")
                    lines.append("")  # Empty line for spacing

    return "\n".join(lines)
