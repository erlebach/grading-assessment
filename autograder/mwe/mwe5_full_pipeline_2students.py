"""MWE 5: Multiple Execution Modes for Grading Multiple Students.

This script demonstrates different execution modes for grading multiple students:
1. Sequential: Grade students one at a time (baseline - 4 separate LLM calls)
2. Batched: Grade all students in a single LLM call (optimized - 1 LLM call)
3. Async Concurrent: Grade students concurrently using asyncio.gather (parallel - 4 concurrent LLM calls)

Prerequisites:
- Set environment variables in $HOME/.env (same as previous MWEs)
- Completed MWE 4
- For Ollama: Set OLLAMA_NUM_PARALLEL=4 (or higher) in environment for async concurrent mode

Usage:
    python -m mwe.mwe5_full_pipeline_2students --mode sequential
    python -m mwe.mwe5_full_pipeline_2students --mode batched
    python -m mwe.mwe5_full_pipeline_2students --mode async
    python -m mwe.mwe5_full_pipeline_2students --mode all  # Run all modes and compare

"""

import argparse
import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from config.llm_config import setup_llamaindex_defaults

# Note: OLLAMA_NUM_PARALLEL must be set in the environment before Ollama server starts.
# Setting it here in Python doesn't help because Ollama is a separate process that
# reads its environment at startup. You need to:
# 1. Export it in your shell: export OLLAMA_NUM_PARALLEL=4
# 2. Restart Ollama server for it to take effect
# The verification below will check if it's set in the current environment.
from evidence.build_index import load_saved_index
from evidence.index_builder import create_documents_with_metadata
from evidence.retriever import EvidenceRetriever
from grader.evidence_retriever import GradingEvidenceRetriever
from grader.grade_question import apply_rubric_scoring
from grader.lmql_grading import LMQLGrader


def create_sample_evidence_index() -> Path:
    """Create a sample evidence index for testing.

    Returns:
        Path to the created index directory.

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

    from evidence.index_builder import build_index_with_metadata

    documents = create_documents_with_metadata(evidence_texts, evidence_sources)
    index = build_index_with_metadata(documents, chunk_size=512, chunk_overlap=50)

    # Save index
    import pickle

    temp_dir = Path(tempfile.mkdtemp())
    index_file = temp_dir / "vector_index.pkl"

    with open(index_file, "wb") as f:
        pickle.dump(index, f)

    return temp_dir


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


def setup_grading_environment(
    num_students: int = 4,
) -> tuple[Path, dict, list[tuple[str, str]], dict[str, float]]:
    """Set up the grading environment (shared across all execution modes).

    Args:
        num_students: Number of students to create (1-4).

    Returns:
        Tuple of (index_path, rubric, students, timings).

    """
    timings: dict[str, float] = {}

    # Step 1: Setup
    print("\n[Step 1] Configuring system...")

    # Check OLLAMA_NUM_PARALLEL (informational - Python process inherits from shell)
    ollama_parallel = os.environ.get("OLLAMA_NUM_PARALLEL", "not set")
    print(f"  OLLAMA_NUM_PARALLEL in Python process: {ollama_parallel}")
    print(f"  → This is inherited from shell environment (e.g., .zshrc)")
    print(
        f"  → Real verification: Check 'ollama serve' logs for 'OLLAMA_NUM_PARALLEL:4'"
    )
    print(
        f"  → If Ollama logs show OLLAMA_NUM_PARALLEL:4, concurrent requests should work"
    )

    start_time = time.time()
    setup_llamaindex_defaults()
    timings["step_1_setup"] = time.time() - start_time
    print("✓ Configuration loaded")

    # Step 2: Create sample evidence index
    print("\n[Step 2] Creating sample evidence index...")
    start_time = time.time()
    index_path = create_sample_evidence_index()
    timings["step_2_create_index"] = time.time() - start_time
    print(f"✓ Index created at {index_path}")

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

    return index_path, rubric, students, timings


def grade_student_sync(
    student_id: str,
    student_answer: str,
    rubric: dict,
    index_path: Path,
) -> tuple[str, dict, dict[str, float]]:
    """Grade a single student submission with detailed step timings (synchronous).

    Args:
        student_id: Identifier for the student.
        student_answer: The student's answer text.
        rubric: The rubric dictionary.
        index_path: Path to the evidence index.

    Returns:
        Tuple of (student_id, grading_result, step_timings).

    """
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    # Step 4: Load evidence index and create retrievers
    step_start = time.time()
    index = load_saved_index(index_path)
    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    step_timings["load_index"] = time.time() - step_start

    # Step 5: Retrieve evidence for rubric
    step_start = time.time()
    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        rubric, student_answer, top_k_per_criterion=2
    )
    step_timings["retrieve_evidence"] = time.time() - step_start

    # Step 6: Apply rubric scoring
    step_start = time.time()
    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)
    step_timings["apply_scoring"] = time.time() - step_start

    # Step 7: Generate LMQL-constrained feedback (synchronous)
    step_start = time.time()
    lmql_grader = LMQLGrader()
    grading_result = lmql_grader.grade_with_feedback(
        rubric=rubric,
        student_answer=student_answer,
        evidence_by_criterion=evidence_by_criterion,
        scores=scores,
    )
    step_timings["generate_feedback"] = time.time() - step_start

    step_timings["total"] = time.time() - overall_start

    # Format result to match grade_question output structure
    result = {
        "question_id": grading_result["question_id"],
        "score": grading_result["total_score"],
        "max_score": grading_result["max_score"],
        "rubric_items": [
            {
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
            for cid, info in grading_result["scores"].items()
        ],
        "citations": [
            cit for ev in grading_result["evidence_used"] for cit in [ev["source_id"]]
        ],
        "feedback": grading_result["feedback"],
    }

    return (student_id, result, step_timings)


async def grade_students_batched_async(
    students: list[tuple[str, str]],
    rubric: dict,
    index_path: Path,
) -> list[tuple[str, dict, dict[str, float]]]:
    """Grade multiple students in a single LLM call (batched).

    Args:
        students: List of (student_id, student_answer) tuples.
        rubric: The rubric dictionary.
        index_path: Path to the evidence index.

    Returns:
        List of tuples (student_id, grading_result, step_timings).

    """
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    # Step 4: Load evidence index and create retrievers (once for all students)
    step_start = time.time()
    index = load_saved_index(index_path)
    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    step_timings["load_index"] = time.time() - step_start

    # Step 5: Retrieve evidence for each student
    step_start = time.time()
    students_evidence: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for student_id, student_answer in students:
        evidence_by_criterion = grading_retriever.retrieve_for_rubric(
            rubric, student_answer, top_k_per_criterion=2
        )
        students_evidence[student_id] = evidence_by_criterion
    step_timings["retrieve_evidence"] = time.time() - step_start

    # Step 6: Apply rubric scoring for each student
    step_start = time.time()
    students_scores: dict[str, dict[str, dict[str, Any]]] = {}
    for student_id, student_answer in students:
        scores = apply_rubric_scoring(
            rubric, student_answer, students_evidence[student_id]
        )
        students_scores[student_id] = scores
    step_timings["apply_scoring"] = time.time() - step_start

    # Step 7: Generate LMQL-constrained feedback (batched - single call for all)
    step_start = time.time()
    lmql_grader = LMQLGrader()

    # Prepare students data for batched grading
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

    # Single batched call
    batch_results = await lmql_grader.grade_batch_async(
        rubric=rubric, students_data=students_data
    )
    step_timings["generate_feedback"] = time.time() - step_start

    step_timings["total"] = time.time() - overall_start

    # Format results
    results = []
    for student_id, student_answer in students:
        grading_result = batch_results[student_id]

        # Format result to match grade_question output structure
        result = {
            "question_id": grading_result["question_id"],
            "score": grading_result["total_score"],
            "max_score": grading_result["max_score"],
            "rubric_items": [
                {
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
                for cid, info in grading_result["scores"].items()
            ],
            "citations": [
                cit
                for ev in grading_result["evidence_used"]
                for cit in [ev["source_id"]]
            ],
            "feedback": grading_result["feedback"],
        }

        # Use the same step_timings for all students (they were graded together)
        results.append((student_id, result, step_timings.copy()))

    return results


async def grade_student_async(
    student_id: str,
    student_answer: str,
    rubric: dict,
    index_path: Path,
) -> tuple[str, dict, dict[str, float]]:
    """Grade a single student submission with detailed step timings (async).

    Args:
        student_id: Identifier for the student.
        student_answer: The student's answer text.
        rubric: The rubric dictionary.
        index_path: Path to the evidence index.

    Returns:
        Tuple of (student_id, grading_result, step_timings).

    """
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    # Step 4: Load evidence index and create retrievers
    step_start = time.time()
    index = load_saved_index(index_path)
    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    step_timings["load_index"] = time.time() - step_start

    # Step 5: Retrieve evidence for rubric
    step_start = time.time()
    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        rubric, student_answer, top_k_per_criterion=2
    )
    step_timings["retrieve_evidence"] = time.time() - step_start

    # Step 6: Apply rubric scoring
    step_start = time.time()
    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)
    step_timings["apply_scoring"] = time.time() - step_start

    # Step 7: Generate LMQL-constrained feedback (async)
    step_start = time.time()
    lmql_grader = LMQLGrader()
    grading_result = await lmql_grader.grade_with_feedback_async(
        rubric=rubric,
        student_answer=student_answer,
        evidence_by_criterion=evidence_by_criterion,
        scores=scores,
    )
    step_timings["generate_feedback"] = time.time() - step_start

    step_timings["total"] = time.time() - overall_start

    # Format result to match grade_question output structure
    result = {
        "question_id": grading_result["question_id"],
        "score": grading_result["total_score"],
        "max_score": grading_result["max_score"],
        "rubric_items": [
            {
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
            for cid, info in grading_result["scores"].items()
        ],
        "citations": [
            cit for ev in grading_result["evidence_used"] for cit in [ev["source_id"]]
        ],
        "feedback": grading_result["feedback"],
    }

    return (student_id, result, step_timings)


def run_sequential_mode(
    index_path: Path,
    rubric: dict,
    students: list[tuple[str, str]],
    timings: dict[str, float],
) -> tuple[list[tuple[str, dict, dict[str, float]]], float]:
    """Run sequential execution mode (one student at a time).

    Args:
        index_path: Path to the evidence index.
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
            result = grade_student_sync(student_id, student_answer, rubric, index_path)
            results.append(result)
            student_timings = result[2]
            print(
                f"    ✓ {student_id}: {result[1]['score']}/{result[1]['max_score']} "
                f"({student_timings['total']:.2f}s)"
            )
            print(f"      - Load index: {student_timings['load_index']:.3f}s")
            print(
                f"      - Retrieve evidence: {student_timings['retrieve_evidence']:.3f}s"
            )
            print(f"      - Apply scoring: {student_timings['apply_scoring']:.3f}s")
            print(
                f"      - Generate feedback: {student_timings['generate_feedback']:.3f}s"
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            if "ResourceExhausted" in error_type or "quota" in error_msg.lower():
                print(f"    ✗ {student_id}: API quota/rate limit exceeded")
                print(f"      Error type: {error_type}")
                print(f"      Error message: {error_msg[:200]}...")
                print(
                    f"      This is likely due to Gemini free tier limits (20 requests/day)"
                )
                print(f"      Solution: Switch to Ollama or wait for quota reset")
            else:
                print(f"    ✗ {student_id}: Error during grading")
                print(f"      Error type: {error_type}")
                print(f"      Error message: {error_msg}")
            raise

    total_time = time.time() - start_time
    timings["sequential_total"] = total_time

    print(f"\n  Sequential total time: {total_time:.3f}s")
    print(f"  Average per student: {total_time / len(students):.3f}s")

    return results, total_time


async def run_batched_mode(
    index_path: Path,
    rubric: dict,
    students: list[tuple[str, str]],
    timings: dict[str, float],
) -> tuple[list[tuple[str, dict, dict[str, float]]], float]:
    """Run batched execution mode (all students in one LLM call).

    Args:
        index_path: Path to the evidence index.
        rubric: The rubric dictionary.
        students: List of (student_id, student_answer) tuples.
        timings: Dictionary to store timing information.

    Returns:
        Tuple of (results, total_time).

    """
    print("\n" + "=" * 70)
    print("[Execution Mode] Batched (Single LLM Call for All Students)")
    print("=" * 70)
    print("  Using batched grading: All students in one LLM prompt")
    print("  This is more efficient than concurrent async calls")

    start_time = time.time()

    try:
        # Grade all students in a single batched LLM call
        results = await grade_students_batched_async(students, rubric, index_path)

        # Process results
        for result in results:
            student_id = result[0]
            student_timings = result[2]
            print(
                f"  ✓ {student_id}: {result[1]['score']}/{result[1]['max_score']} "
                f"({student_timings['total']:.2f}s)"
            )
            print(f"      - Load index: {student_timings['load_index']:.3f}s")
            print(
                f"      - Retrieve evidence: {student_timings['retrieve_evidence']:.3f}s"
            )
            print(f"      - Apply scoring: {student_timings['apply_scoring']:.3f}s")
            print(
                f"      - Generate feedback: {student_timings['generate_feedback']:.3f}s"
            )
    except Exception as exc:
        error_msg = str(exc)
        error_type = type(exc).__name__
        if "ResourceExhausted" in error_type or "quota" in error_msg.lower():
            print(f"  ✗ API quota/rate limit exceeded")
            print(f"      Error type: {error_type}")
            print(f"      Error message: {error_msg[:200]}...")
            print(
                f"      This is likely due to Gemini free tier limits (20 requests/day)"
            )
            print(f"      Solution: Switch to Ollama or wait for quota reset")
        else:
            print(f"  ✗ Error during batched grading")
            print(f"      Error type: {error_type}")
            print(f"      Error message: {error_msg}")
        raise

    total_time = time.time() - start_time
    timings["batched_total"] = total_time

    print(f"\n  Batched total time: {total_time:.3f}s")
    print(f"  Average per student: {total_time / len(students):.3f}s")
    print(f"  ✓ All {len(students)} students graded in a single LLM call")

    return results, total_time


async def run_async_concurrent_mode(
    index_path: Path,
    rubric: dict,
    students: list[tuple[str, str]],
    timings: dict[str, float],
) -> tuple[list[tuple[str, dict, dict[str, float]]], float]:
    """Run async concurrent execution mode (multiple concurrent LLM calls).

    Args:
        index_path: Path to the evidence index.
        rubric: The rubric dictionary.
        students: List of (student_id, student_answer) tuples.
        timings: Dictionary to store timing information.

    Returns:
        Tuple of (results, total_time).

    """
    print("\n" + "=" * 70)
    print("[Execution Mode] Async Concurrent (Parallel LLM Calls)")
    print("=" * 70)
    print("  Using async/await with asyncio.gather for concurrent execution")
    print("  Requires OLLAMA_NUM_PARALLEL to be set for Ollama")

    start_time = time.time()

    try:
        # Run all grading tasks concurrently using asyncio.gather
        tasks = [
            grade_student_async(student_id, student_answer, rubric, index_path)
            for student_id, student_answer in students
        ]
        results = await asyncio.gather(*tasks)

        # Process results as they complete
        for result in results:
            student_id = result[0]
            student_timings = result[2]
            print(
                f"  ✓ {student_id}: {result[1]['score']}/{result[1]['max_score']} "
                f"({student_timings['total']:.2f}s)"
            )
            print(f"      - Load index: {student_timings['load_index']:.3f}s")
            print(
                f"      - Retrieve evidence: {student_timings['retrieve_evidence']:.3f}s"
            )
            print(f"      - Apply scoring: {student_timings['apply_scoring']:.3f}s")
            print(
                f"      - Generate feedback: {student_timings['generate_feedback']:.3f}s"
            )
    except Exception as exc:
        error_msg = str(exc)
        error_type = type(exc).__name__
        if "ResourceExhausted" in error_type or "quota" in error_msg.lower():
            print(f"  ✗ API quota/rate limit exceeded")
            print(f"      Error type: {error_type}")
            print(f"      Error message: {error_msg[:200]}...")
            print(
                f"      This is likely due to Gemini free tier limits (20 requests/day)"
            )
            print(f"      Solution: Switch to Ollama or wait for quota reset")
        else:
            print(f"  ✗ Error during async concurrent grading")
            print(f"      Error type: {error_type}")
            print(f"      Error message: {error_msg}")
        raise

    total_time = time.time() - start_time
    timings["async_concurrent_total"] = total_time

    print(f"\n  Async concurrent total time: {total_time:.3f}s")
    print(f"  Average per student: {total_time / len(students):.3f}s")

    return results, total_time


def main_sync(mode: str = "sequential", num_students: int = 4) -> None:
    """Run MWE 5 demonstration (synchronous version).

    Args:
        mode: Execution mode - "sequential", "batched", "async", or "all".
        num_students: Number of students to grade (1-4).

    """
    print("=" * 70)
    print("MWE 5: Multiple Execution Modes for Grading")
    print("=" * 70)

    # Setup shared environment
    index_path, rubric, students, timings = setup_grading_environment(num_students)

    if mode == "sequential":
        # Run sequential mode
        results, total_time = run_sequential_mode(index_path, rubric, students, timings)

        # Print complete timing summary
        print("\n" + "=" * 70)
        print("Complete Timing Summary")
        print("=" * 70)
        total_time_all = sum(timings.values())
        for step_name, elapsed_time in sorted(timings.items()):
            percentage = (
                (elapsed_time / total_time_all * 100) if total_time_all > 0 else 0
            )
            print(f"{step_name:30s}: {elapsed_time:8.3f}s ({percentage:5.1f}%)")
        print("-" * 70)
        print(f"{'Total time':30s}: {total_time_all:8.3f}s")
        print("=" * 70)
    else:
        # Other modes require async, so call async version
        asyncio.run(main_async(mode))


async def main_async(mode: str = "batched", num_students: int = 4) -> None:
    """Run MWE 5 demonstration (async version).

    Args:
        mode: Execution mode - "sequential", "batched", "async", or "all".
        num_students: Number of students to grade (1-4).

    """
    print("=" * 70)
    print("MWE 5: Multiple Execution Modes for Grading")
    print("=" * 70)

    # Setup shared environment
    index_path, rubric, students, timings = setup_grading_environment(num_students)

    sequential_results: list[tuple[str, dict, dict[str, float]]] = []
    batched_results: list[tuple[str, dict, dict[str, float]]] = []
    async_results: list[tuple[str, dict, dict[str, float]]] = []

    sequential_time = 0.0
    batched_time = 0.0
    async_time = 0.0

    if mode == "sequential":
        sequential_results, sequential_time = run_sequential_mode(
            index_path, rubric, students, timings
        )
    elif mode == "batched":
        batched_results, batched_time = await run_batched_mode(
            index_path, rubric, students, timings
        )
    elif mode == "async":
        async_results, async_time = await run_async_concurrent_mode(
            index_path, rubric, students, timings
        )
    elif mode == "all":
        # Run all modes and compare
        print("\n" + "=" * 70)
        print("Running All Execution Modes for Comparison")
        print("=" * 70)

        # Sequential
        sequential_results, sequential_time = run_sequential_mode(
            index_path, rubric, students, timings
        )

        # Batched
        batched_results, batched_time = await run_batched_mode(
            index_path, rubric, students, timings
        )

        # Async concurrent
        async_results, async_time = await run_async_concurrent_mode(
            index_path, rubric, students, timings
        )

        # Comparison
        print("\n" + "=" * 70)
        print("Execution Mode Comparison")
        print("=" * 70)
        print(f"\n  Overall Timing:")
        print(f"    Sequential:     {sequential_time:.3f}s (baseline)")
        print(f"    Batched:        {batched_time:.3f}s (single LLM call)")
        print(f"    Async Concurrent: {async_time:.3f}s (parallel LLM calls)")

        if sequential_time > 0:
            batched_speedup = sequential_time / batched_time if batched_time > 0 else 0
            async_speedup = sequential_time / async_time if async_time > 0 else 0
            print(f"\n  Speedup vs Sequential:")
            print(f"    Batched:        {batched_speedup:.2f}x")
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

    # Print complete timing summary
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


def main() -> None:
    """Run MWE 5 demonstration with selectable execution mode."""
    parser = argparse.ArgumentParser(
        description="MWE 5: Multiple execution modes for grading multiple students",
        epilog="""
Examples:
  # Run sequential mode with 4 students (one student at a time)
  python -m mwe.mwe5_full_pipeline_2students --mode sequential

  # Run batched mode with 2 students (single LLM call for all students)
  python -m mwe.mwe5_full_pipeline_2students --mode batched --num-students 2

  # Run async concurrent mode with 3 students (parallel LLM calls)
  python -m mwe.mwe5_full_pipeline_2students --mode async --num-students 3

  # Run all modes with 1 student and compare results
  python -m mwe.mwe5_full_pipeline_2students --mode all --num-students 1
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sequential", "batched", "async", "all"],
        default="batched",
        help="Execution mode: sequential (one at a time), batched (single LLM call), "
        "async (concurrent LLM calls), or all (run all modes and compare)",
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

    # Route to appropriate function based on mode
    if mode == "sequential":
        main_sync(mode, num_students)
    else:
        # Batched, async, and all require async
        asyncio.run(main_async(mode, num_students))


if __name__ == "__main__":
    main()
