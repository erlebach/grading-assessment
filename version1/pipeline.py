"""Version 1 Pipeline: Dual-index Chroma RAG with reranking.

This script extends MWE 5 with:
- Chroma vector database (persistent storage)
- Dual embedding indexes: word-based (512 chars) + sentence-based
- Cross-encoder reranking for improved relevance
- All execution modes from MWE 5 (sequential, batched, async)

Prerequisites:
- Set environment variables in $HOME/.env
- Optional: Set RERANKER_MODEL env var (defaults to ms-marco-MiniLM-L-6-v2)

Usage:
    python -m version1.pipeline --mode sequential
    python -m version1.pipeline --mode batched
    python -m version1.pipeline --mode async
    python -m version1.pipeline --mode all  # Run all modes and compare

"""

import argparse
import asyncio
import os
import time
from pathlib import Path
from typing import Any, Callable

from config.llm_config import setup_llamaindex_defaults
from evidence.index_builder import create_documents_with_metadata
from grader.grade_question import apply_rubric_scoring
from grader.lmql_grading import LMQLGrader
from version1.index_builder import build_dual_indexes, load_dual_indexes
from version1.retriever import DualIndexRetriever


def create_sample_dual_index() -> tuple[Path, DualIndexRetriever]:
    """Create sample dual indexes for testing.

    Returns:
        Tuple of (persist_dir, retriever).

    """
    # Create sample evidence corpus
    evidence_texts = [
        "Mutual information I(X;Y) measures the reduction in uncertainty "
        "about variable X when we observe variable Y. It quantifies the "
        "amount of information obtained about one random variable through "
        "observing the other random variable.",
        "The mutual information is always non-negative: I(X;Y) >= 0. "
        "It equals zero if and only if X and Y are independent. "
        "It is also symmetric: I(X;Y) = I(Y;X).",
        "Mutual information captures both linear and nonlinear dependencies "
        "between variables. Unlike correlation, which only measures linear "
        "relationships, mutual information is based on the joint probability "
        "distribution and can detect any type of statistical dependence.",
        "The entropy H(X) of a random variable measures the average "
        "information content or uncertainty. For a discrete random variable, "
        "entropy is defined as H(X) = -sum_x p(x) log p(x).",
        "Conditional entropy H(X|Y) measures the average uncertainty "
        "remaining about X after observing Y. It is related to mutual "
        "information by: I(X;Y) = H(X) - H(X|Y).",
    ]

    evidence_sources = [
        {"source_id": "slide_12", "source_type": "slide", "page_number": 12},
        {"source_id": "slide_13", "source_type": "slide", "page_number": 13},
        {"source_id": "slide_14", "source_type": "slide", "page_number": 14},
        {"source_id": "slide_20", "source_type": "slide", "page_number": 20},
        {"source_id": "slide_21", "source_type": "slide", "page_number": 21},
    ]

    from version1.index_builder import build_sentence_index, build_word_index

    documents = create_documents_with_metadata(evidence_texts, evidence_sources)

    # Create directory in version1/tmp/ for Chroma persistence
    persist_dir = Path(__file__).parent / "tmp" / f"test_pipeline_{int(time.time())}"
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Build dual indexes
    word_index = build_word_index(documents, persist_dir, "word_index")
    sentence_index = build_sentence_index(documents, persist_dir, "sentence_index")

    # Create retriever
    retriever = DualIndexRetriever(word_index, sentence_index)

    return persist_dir, retriever


def create_sample_rubric() -> dict:
    """Create a sample rubric for testing.

    Returns:
        Rubric dictionary.

    """
    return {
        "question_id": "q01",
        "question_text": "Explain mutual information and its relationship to entropy",
        "total_points": 10,
        "criteria": [
            {
                "criterion_id": "definition",
                "description": "Correctly defines mutual information",
                "points": 4,
                "evidence_required": True,
                "evaluation_method": "semantic",
            },
            {
                "criterion_id": "properties",
                "description": "Explains key properties like non-negative and symmetric",
                "points": 3,
                "evidence_required": True,
                "evaluation_method": "semantic",
            },
            {
                "criterion_id": "entropy_relation",
                "description": "Relates mutual information to entropy concepts",
                "points": 3,
                "evidence_required": True,
                "evaluation_method": "semantic",
            },
        ],
    }


def format_grading_result(
    grading_result: dict, rubric: dict, student_answer: str = ""
) -> dict:
    """Format grading result to match grade_question output structure.

    Args:
        grading_result: Raw grading result from LMQL grader.
        rubric: The rubric dictionary.
        student_answer: The student's answer text (optional).

    Returns:
        Formatted result dictionary matching grade_question output structure.

    """
    rubric_items = []
    for cid, info in grading_result["scores"].items():
        item = {
            "criterion_id": cid,
            "score": info["score"],
            "max_score": info["max_score"],
            "description": rubric["criteria"][
                next(
                    i
                    for i, c in enumerate(rubric["criteria"])
                    if c["criterion_id"] == cid
                )
            ]["description"],
        }
        # Preserve keyword information if available
        if "keywords" in info:
            item["keywords"] = info.get("keywords", [])
            item["found_keywords"] = info.get("found_keywords", [])
            item["missing_keywords"] = info.get("missing_keywords", [])
        rubric_items.append(item)

    return {
        "question_id": grading_result["question_id"],
        "question_text": rubric.get("question_text", ""),
        "student_answer": student_answer,
        "score": grading_result["total_score"],
        "max_score": grading_result["max_score"],
        "rubric_items": rubric_items,
        "citations": [
            cit for ev in grading_result["evidence_used"] for cit in [ev["source_id"]]
        ],
        "feedback": grading_result["feedback"],
    }


def handle_grading_error(exc: Exception, student_id: str | None = None) -> None:
    """Handle and print grading errors with user-friendly messages.

    Args:
        exc: The exception that occurred.
        student_id: Optional student identifier for context.

    Raises:
        Re-raises the exception after logging.

    """
    error_msg = str(exc)
    error_type = type(exc).__name__
    student_prefix = f"{student_id}: " if student_id else ""

    if "ResourceExhausted" in error_type or "quota" in error_msg.lower():
        print(f"  ✗ {student_prefix}API quota/rate limit exceeded")
        print(f"      Error type: {error_type}")
        print(f"      Error message: {error_msg[:200]}...")
        print("      This is likely due to Gemini free tier limits (20 requests/day)")
        print("      Solution: Switch to Ollama or wait for quota reset")
    else:
        error_context = (
            f"{student_id}: Error during grading"
            if student_id
            else "Error during grading"
        )
        print(f"  ✗ {error_context}")
        print(f"      Error type: {error_type}")
        print(f"      Error message: {error_msg}")
    raise


def print_student_result(
    result: tuple[str, dict, dict[str, float]],
) -> None:
    """Print formatted student grading result with timing breakdown.

    Args:
        result: Tuple of (student_id, grading_result, step_timings).

    """
    student_id, grading_result, step_timings = result

    try:
        student_number = int(student_id.split("_")[1])
    except (IndexError, ValueError):
        student_number = student_id
    print(f"\n  ==> STUDENT {student_number}")

    # Print question text if available
    if grading_result.get("question_text"):
        print(f"  Question: {grading_result['question_text']}")

    # Print student answer if available
    if grading_result.get("student_answer"):
        answer_preview = grading_result["student_answer"].strip()
        # Truncate if too long for display
        if len(answer_preview) > 500:
            answer_preview = answer_preview[:500] + "..."
        print(f"  Student Answer: {answer_preview}")

    print(
        f"  ✓ {student_id}: {grading_result['score']}/{grading_result['max_score']} "
        f"({step_timings['total']:.2f}s)"
    )
    print(f"      - Load indexes: {step_timings['load_indexes']:.3f}s")
    print(f"      - Retrieve evidence: {step_timings['retrieve_evidence']:.3f}s")
    if "rerank_evidence" in step_timings:
        print(f"      - Rerank evidence: {step_timings['rerank_evidence']:.3f}s")
    print(f"      - Apply scoring: {step_timings['apply_scoring']:.3f}s")
    print(f"      - Generate feedback: {step_timings['generate_feedback']:.3f}s")

    # Print rubric criteria evaluation
    if grading_result.get("rubric_items"):
        print("\n      Rubric Criteria Evaluation:")
        for item in grading_result["rubric_items"]:
            criterion_id = item["criterion_id"]
            score = item["score"]
            max_score = item["max_score"]
            description = item.get("description", "")
            print(f"      - {criterion_id}: {score}/{max_score} - {description}")

            if "keywords" in item and item["keywords"]:
                keywords = item["keywords"]
                found = item.get("found_keywords", [])
                missing = item.get("missing_keywords", [])
                print(f"        Keywords: {', '.join(keywords)}")
                if found:
                    print(f"        ✓ Found: {', '.join(found)}")
                if missing:
                    print(f"        ✗ Missing: {', '.join(missing)}")

    # Print citations if available
    if grading_result.get("citations"):
        citations_str = ", ".join(grading_result["citations"])
        print(f"\n      Citations: {citations_str}")

    # Print feedback if available
    if grading_result.get("feedback"):
        print(f"      Feedback: {grading_result['feedback']}")


def print_timing_summary(timings: dict[str, float]) -> None:
    """Print formatted timing summary table.

    Args:
        timings: Dictionary of timing information.

    """
    print("\n" + "=" * 70)
    print("Complete Timing Summary")
    print("=" * 70)
    total_time = sum(timings.values())
    for step_name, elapsed_time in sorted(timings.items()):
        percentage = (elapsed_time / total_time * 100) if total_time > 0 else 0
        print(f"{step_name:30s}: {elapsed_time:8.3f}s ({percentage:5.1f}%)")
    print("-" * 70)
    print(f"{'Total time':30s}: {total_time:8.3f}s")
    print("=" * 70)


def setup_grading_environment(
    num_students: int = 4,
) -> tuple[Path, DualIndexRetriever, dict, list[tuple[str, str]], dict[str, float]]:
    """Set up the grading environment (shared across all execution modes).

    Args:
        num_students: Number of students to create (1-4).

    Returns:
        Tuple of (persist_dir, retriever, rubric, students, timings).

    """
    timings: dict[str, float] = {}

    # Step 1: Setup
    print("\n[Step 1] Configuring system...")

    # Check OLLAMA_NUM_PARALLEL (informational)
    ollama_parallel = os.environ.get("OLLAMA_NUM_PARALLEL", "not set")
    print(f"  OLLAMA_NUM_PARALLEL in Python process: {ollama_parallel}")

    # Check reranker model
    reranker_model = os.environ.get(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    print(f"  RERANKER_MODEL: {reranker_model}")

    start_time = time.time()
    setup_llamaindex_defaults()
    timings["step_1_setup"] = time.time() - start_time
    print("✓ Configuration loaded")

    # Step 2: Create sample dual indexes
    print("\n[Step 2] Creating sample dual indexes with Chroma...")
    start_time = time.time()
    persist_dir, retriever = create_sample_dual_index()
    timings["step_2_create_indexes"] = time.time() - start_time
    print(f"✓ Dual indexes created at {persist_dir}")

    # Step 3: Create sample rubric and student submissions
    print("\n[Step 3] Creating sample rubric and student submissions...")
    start_time = time.time()

    rubric = create_sample_rubric()
    print(f"✓ Rubric: {rubric['question_text']}")
    print(f"  Criteria: {len(rubric['criteria'])}")
    print(f"  Total points: {rubric['total_points']}")

    # Create four different student answers
    student_1_answer = """
    Mutual information measures how much knowing one variable tells us about
    another variable. It's always non-negative and is symmetric, meaning
    I(X;Y) = I(Y;X). It's related to entropy because mutual information
    equals the entropy of X minus the conditional entropy H(X|Y).
    """

    student_2_answer = """
    Mutual information I(X;Y) quantifies the amount of information that one
    random variable contains about another. It is non-negative and symmetric.
    The relationship to entropy is that I(X;Y) = H(X) - H(X|Y), where H(X)
    is the entropy of X and H(X|Y) is the conditional entropy of X given Y.
    """

    student_3_answer = """
    Mutual information is a measure of the dependence between two random
    variables. It tells us how much information we gain about one variable
    when we observe the other. The key properties are that it's always
    non-negative, symmetric, and can be expressed in terms of entropy as
    I(X;Y) = H(X) - H(X|Y) = H(Y) - H(Y|X).
    """

    student_4_answer = """
    Mutual information I(X;Y) captures how much one random variable tells
    us about another. It's a symmetric measure that's always greater than
    or equal to zero. When X and Y are independent, mutual information is
    zero. The connection to entropy is through the formula I(X;Y) = H(X) - H(X|Y),
    showing it's the reduction in uncertainty about X when Y is known.
    """

    # Create list of all possible student answers
    all_student_answers = [
        ("student_1", student_1_answer),
        ("student_2", student_2_answer),
        ("student_3", student_3_answer),
        ("student_4", student_4_answer),
    ]

    # Select only the requested number of students
    students = all_student_answers[:num_students]

    print(f"\n  Created {len(students)} student submissions")
    timings["step_3_create_rubric"] = time.time() - start_time

    return persist_dir, retriever, rubric, students, timings


def _grade_student_core(
    student_id: str,
    student_answer: str,
    rubric: dict,
    persist_dir: Path,
    retriever: DualIndexRetriever,
    grade_fn: Callable[[LMQLGrader, dict, str, dict, dict], dict],
) -> tuple[str, dict, dict[str, float]]:
    """Core grading pipeline for a single student (shared by sync and async).

    Args:
        student_id: Identifier for the student.
        student_answer: The student's answer text.
        rubric: The rubric dictionary.
        persist_dir: Path to the Chroma persistence directory.
        retriever: DualIndexRetriever instance.
        grade_fn: Callable that performs the LLM grading step.

    Returns:
        Tuple of (student_id, formatted_result, step_timings).

    """
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    # Step 4: Load indexes (already loaded in retriever, just track time)
    step_start = time.time()
    # Indexes are already loaded in the retriever
    step_timings["load_indexes"] = time.time() - step_start

    # Step 5: Retrieve evidence for rubric with dual-index and reranking
    step_start = time.time()
    evidence_by_criterion = {}

    for criterion in rubric.get("criteria", []):
        if criterion.get("evidence_required", False):
            # Use dual-index retriever with reranking
            evidence = retriever.retrieve_for_criterion(
                criterion, student_answer, top_k_per_index=5, final_top_k=3
            )
            evidence_by_criterion[criterion["criterion_id"]] = evidence

    retrieve_time = time.time() - step_start
    step_timings["retrieve_evidence"] = retrieve_time
    # Note: Reranking is included in retrieve_evidence time
    step_timings["rerank_evidence"] = 0.0  # Included in retrieve_evidence

    # Step 6: Apply rubric scoring
    step_start = time.time()
    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)
    step_timings["apply_scoring"] = time.time() - step_start

    # Step 7: Generate LMQL-constrained feedback
    step_start = time.time()
    lmql_grader = LMQLGrader()
    grading_result = grade_fn(
        lmql_grader, rubric, student_answer, evidence_by_criterion, scores
    )
    step_timings["generate_feedback"] = time.time() - step_start

    step_timings["total"] = time.time() - overall_start

    # Format result
    result = format_grading_result(grading_result, rubric, student_answer)

    return (student_id, result, step_timings)


def grade_student_sync(
    student_id: str,
    student_answer: str,
    rubric: dict,
    persist_dir: Path,
    retriever: DualIndexRetriever,
) -> tuple[str, dict, dict[str, float]]:
    """Grade a single student submission (synchronous).

    Args:
        student_id: Identifier for the student.
        student_answer: The student's answer text.
        rubric: The rubric dictionary.
        persist_dir: Path to the Chroma persistence directory.
        retriever: DualIndexRetriever instance.

    Returns:
        Tuple of (student_id, grading_result, step_timings).

    """

    def sync_grade_fn(grader, rub, answer, evidence, scrs):
        return grader.grade_with_feedback(
            rubric=rub,
            student_answer=answer,
            evidence_by_criterion=evidence,
            scores=scrs,
        )

    return _grade_student_core(
        student_id, student_answer, rubric, persist_dir, retriever, sync_grade_fn
    )


async def grade_students_batched_async(
    students: list[tuple[str, str]],
    rubric: dict,
    persist_dir: Path,
    retriever: DualIndexRetriever,
) -> list[tuple[str, dict, dict[str, float]]]:
    """Grade multiple students in a single LLM call (batched).

    Args:
        students: List of (student_id, student_answer) tuples.
        rubric: The rubric dictionary.
        persist_dir: Path to the Chroma persistence directory.
        retriever: DualIndexRetriever instance.

    Returns:
        List of tuples (student_id, grading_result, step_timings).

    """
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    # Step 4: Indexes already loaded
    step_start = time.time()
    step_timings["load_indexes"] = time.time() - step_start

    # Step 5: Retrieve evidence for each student
    step_start = time.time()
    students_evidence: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for student_id, student_answer in students:
        evidence_by_criterion = {}
        for criterion in rubric.get("criteria", []):
            if criterion.get("evidence_required", False):
                evidence = retriever.retrieve_for_criterion(
                    criterion, student_answer, top_k_per_index=5, final_top_k=3
                )
                evidence_by_criterion[criterion["criterion_id"]] = evidence
        students_evidence[student_id] = evidence_by_criterion

    step_timings["retrieve_evidence"] = time.time() - step_start
    step_timings["rerank_evidence"] = 0.0  # Included in retrieve_evidence

    # Step 6: Apply rubric scoring for each student
    step_start = time.time()
    students_scores: dict[str, dict[str, dict[str, Any]]] = {}
    for student_id, student_answer in students:
        scores = apply_rubric_scoring(
            rubric, student_answer, students_evidence[student_id]
        )
        students_scores[student_id] = scores
    step_timings["apply_scoring"] = time.time() - step_start

    # Step 7: Generate LMQL-constrained feedback (batched)
    step_start = time.time()
    lmql_grader = LMQLGrader()

    students_data = []
    for student_id, student_answer in students:
        students_data.append(
            {
                "student_id": student_id,
                "student_answer": student_answer,
                "evidence_by_criterion": students_evidence[student_id],
                "scores": students_scores[student_id],
            }
        )

    batch_results = await lmql_grader.grade_batch_async(
        rubric=rubric, students_data=students_data
    )
    step_timings["generate_feedback"] = time.time() - step_start

    step_timings["total"] = time.time() - overall_start

    # Format results
    results = []
    for student_id, student_answer in students:
        grading_result = batch_results[student_id]
        result = format_grading_result(grading_result, rubric, student_answer)
        results.append((student_id, result, step_timings.copy()))

    return results


async def grade_student_async(
    student_id: str,
    student_answer: str,
    rubric: dict,
    persist_dir: Path,
    retriever: DualIndexRetriever,
) -> tuple[str, dict, dict[str, float]]:
    """Grade a single student submission (async).

    Args:
        student_id: Identifier for the student.
        student_answer: The student's answer text.
        rubric: The rubric dictionary.
        persist_dir: Path to the Chroma persistence directory.
        retriever: DualIndexRetriever instance.

    Returns:
        Tuple of (student_id, grading_result, step_timings).

    """

    async def async_grade_fn(grader, rub, answer, evidence, scrs):
        return await grader.grade_with_feedback_async(
            rubric=rub,
            student_answer=answer,
            evidence_by_criterion=evidence,
            scores=scrs,
        )

    # Inline the core logic with async grade function
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    step_start = time.time()
    step_timings["load_indexes"] = time.time() - step_start

    step_start = time.time()
    evidence_by_criterion = {}
    for criterion in rubric.get("criteria", []):
        if criterion.get("evidence_required", False):
            evidence = retriever.retrieve_for_criterion(
                criterion, student_answer, top_k_per_index=5, final_top_k=3
            )
            evidence_by_criterion[criterion["criterion_id"]] = evidence
    step_timings["retrieve_evidence"] = time.time() - step_start
    step_timings["rerank_evidence"] = 0.0

    step_start = time.time()
    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)
    step_timings["apply_scoring"] = time.time() - step_start

    step_start = time.time()
    lmql_grader = LMQLGrader()
    grading_result = await async_grade_fn(
        lmql_grader, rubric, student_answer, evidence_by_criterion, scores
    )
    step_timings["generate_feedback"] = time.time() - step_start

    step_timings["total"] = time.time() - overall_start

    result = format_grading_result(grading_result, rubric, student_answer)

    return (student_id, result, step_timings)


def run_sequential_mode(
    persist_dir: Path,
    retriever: DualIndexRetriever,
    rubric: dict,
    students: list[tuple[str, str]],
    timings: dict[str, float],
) -> tuple[list[tuple[str, dict, dict[str, float]]], float]:
    """Run sequential execution mode.

    Args:
        persist_dir: Path to Chroma persistence directory.
        retriever: DualIndexRetriever instance.
        rubric: The rubric dictionary.
        students: List of (student_id, student_answer) tuples.
        timings: Dictionary to store timing information.

    Returns:
        Tuple of (results, total_time).

    """
    print("\n" + "=" * 70)
    print("[Execution Mode] Sequential (One at a Time)")
    print("=" * 70)

    results: list[tuple[str, dict, dict[str, float]]] = []
    start_time = time.time()

    for student_id, student_answer in students:
        print(f"\n  Grading {student_id}...")
        try:
            result = grade_student_sync(
                student_id, student_answer, rubric, persist_dir, retriever
            )
            results.append(result)
            print_student_result(result)
        except Exception as e:
            handle_grading_error(e, student_id)

    total_time = time.time() - start_time
    timings["sequential_total"] = total_time

    print(f"\n  Sequential total time: {total_time:.3f}s")
    print(f"  Average per student: {total_time / len(students):.3f}s")

    return results, total_time


async def run_batched_mode(
    persist_dir: Path,
    retriever: DualIndexRetriever,
    rubric: dict,
    students: list[tuple[str, str]],
    timings: dict[str, float],
) -> tuple[list[tuple[str, dict, dict[str, float]]], float]:
    """Run batched execution mode.

    Args:
        persist_dir: Path to Chroma persistence directory.
        retriever: DualIndexRetriever instance.
        rubric: The rubric dictionary.
        students: List of (student_id, student_answer) tuples.
        timings: Dictionary to store timing information.

    Returns:
        Tuple of (results, total_time).

    """
    print("\n" + "=" * 70)
    print("[Execution Mode] Batched (Single LLM Call for All Students)")
    print("=" * 70)
    print("  Using batched grading with dual-index retrieval and reranking")

    start_time = time.time()

    try:
        results = await grade_students_batched_async(
            students, rubric, persist_dir, retriever
        )

        for result in results:
            print_student_result(result)
    except Exception as exc:
        handle_grading_error(exc)

    total_time = time.time() - start_time
    timings["batched_total"] = total_time

    print(f"\n  Batched total time: {total_time:.3f}s")
    print(f"  Average per student: {total_time / len(students):.3f}s")
    print(f"  ✓ All {len(students)} students graded with dual-index retrieval")

    return results, total_time


async def run_async_concurrent_mode(
    persist_dir: Path,
    retriever: DualIndexRetriever,
    rubric: dict,
    students: list[tuple[str, str]],
    timings: dict[str, float],
) -> tuple[list[tuple[str, dict, dict[str, float]]], float]:
    """Run async concurrent execution mode.

    Args:
        persist_dir: Path to Chroma persistence directory.
        retriever: DualIndexRetriever instance.
        rubric: The rubric dictionary.
        students: List of (student_id, student_answer) tuples.
        timings: Dictionary to store timing information.

    Returns:
        Tuple of (results, total_time).

    """
    print("\n" + "=" * 70)
    print("[Execution Mode] Async Concurrent (Parallel LLM Calls)")
    print("=" * 70)
    print("  Using async/await with dual-index retrieval and reranking")

    start_time = time.time()

    try:
        tasks = [
            grade_student_async(
                student_id, student_answer, rubric, persist_dir, retriever
            )
            for student_id, student_answer in students
        ]
        results = await asyncio.gather(*tasks)

        for result in results:
            print_student_result(result)
    except Exception as exc:
        handle_grading_error(exc)

    total_time = time.time() - start_time
    timings["async_concurrent_total"] = total_time

    print(f"\n  Async concurrent total time: {total_time:.3f}s")
    print(f"  Average per student: {total_time / len(students):.3f}s")

    return results, total_time


def main_sync(num_students: int = 4) -> None:
    """Run pipeline (synchronous version - sequential mode only).

    Args:
        num_students: Number of students to grade (1-4).

    """
    print("=" * 70)
    print("Version 1 Pipeline: Dual-Index Chroma RAG with Reranking")
    print("=" * 70)

    persist_dir, retriever, rubric, students, timings = setup_grading_environment(
        num_students
    )

    results, total_time = run_sequential_mode(
        persist_dir, retriever, rubric, students, timings
    )
    print_timing_summary(timings)


async def main_async(mode: str = "batched", num_students: int = 4) -> None:
    """Run pipeline (async version - batched, async, or all modes).

    Args:
        mode: Execution mode - "batched", "async", or "all".
        num_students: Number of students to grade (1-4).

    """
    print("=" * 70)
    print("Version 1 Pipeline: Dual-Index Chroma RAG with Reranking")
    print("=" * 70)

    persist_dir, retriever, rubric, students, timings = setup_grading_environment(
        num_students
    )

    sequential_results: list[tuple[str, dict, dict[str, float]]] = []
    batched_results: list[tuple[str, dict, dict[str, float]]] = []
    async_results: list[tuple[str, dict, dict[str, float]]] = []

    sequential_time = 0.0
    batched_time = 0.0
    async_time = 0.0

    if mode == "batched":
        batched_results, batched_time = await run_batched_mode(
            persist_dir, retriever, rubric, students, timings
        )
    elif mode == "async":
        async_results, async_time = await run_async_concurrent_mode(
            persist_dir, retriever, rubric, students, timings
        )
    elif mode == "all":
        print("\n" + "=" * 70)
        print("Running All Execution Modes for Comparison")
        print("=" * 70)

        sequential_results, sequential_time = run_sequential_mode(
            persist_dir, retriever, rubric, students, timings
        )

        batched_results, batched_time = await run_batched_mode(
            persist_dir, retriever, rubric, students, timings
        )

        async_results, async_time = await run_async_concurrent_mode(
            persist_dir, retriever, rubric, students, timings
        )

        # Comparison
        print("\n" + "=" * 70)
        print("Execution Mode Comparison")
        print("=" * 70)
        print("\n  Overall Timing:")
        print(f"    Sequential:       {sequential_time:.3f}s (baseline)")
        print(f"    Batched:          {batched_time:.3f}s (single LLM call)")
        print(f"    Async Concurrent: {async_time:.3f}s (parallel LLM calls)")

        if sequential_time > 0:
            batched_speedup = sequential_time / batched_time if batched_time > 0 else 0
            async_speedup = sequential_time / async_time if async_time > 0 else 0
            print("\n  Speedup vs Sequential:")
            print(f"    Batched:          {batched_speedup:.2f}x")
            print(f"    Async Concurrent: {async_speedup:.2f}x")

        # Verify results are consistent
        print("\n  Result Verification:")
        sequential_scores = {sid: r["score"] for sid, r, _ in sequential_results}
        batched_scores = {sid: r["score"] for sid, r, _ in batched_results}
        async_scores = {sid: r["score"] for sid, r, _ in async_results}

        if sequential_scores == batched_scores == async_scores:
            print("    ✓ Scores match across all execution modes")
        else:
            print("    ✗ Scores differ between execution modes")
            print(f"      Sequential: {sequential_scores}")
            print(f"      Batched: {batched_scores}")
            print(f"      Async: {async_scores}")

    print_timing_summary(timings)


def main() -> None:
    """Run Version 1 pipeline with selectable execution mode."""
    parser = argparse.ArgumentParser(
        description="Version 1 Pipeline: Dual-Index Chroma RAG with Reranking",
        epilog="""
Examples:
  # Run sequential mode with 4 students
  python -m version1.pipeline --mode sequential

  # Run batched mode with 2 students
  python -m version1.pipeline --mode batched --num-students 2

  # Run async concurrent mode with 3 students
  python -m version1.pipeline --mode async --num-students 3

  # Run all modes with 1 student and compare
  python -m version1.pipeline --mode all --num-students 1
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sequential", "batched", "async", "all"],
        default="batched",
        help="Execution mode",
    )
    parser.add_argument(
        "--num-students",
        type=int,
        choices=[1, 2, 3, 4],
        default=4,
        help="Number of students to grade (1-4, default: 4)",
    )
    args = parser.parse_args()

    mode = args.mode
    num_students = args.num_students

    time_start = time.time()
    if mode == "sequential":
        main_sync(num_students)
    else:
        asyncio.run(main_async(mode, num_students))
    time_end = time.time()
    print(f"\nTime taken (main): {time_end - time_start:.2f} seconds")


if __name__ == "__main__":
    main()
