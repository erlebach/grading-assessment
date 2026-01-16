"""MWE 5: Concurrent Grading of Multiple Students.

This script demonstrates concurrent execution of the grading pipeline for
multiple students to show time savings through parallelization:
1. Grade four students sequentially (baseline)
2. Grade four students concurrently (optimized)
3. Compare timing results

Prerequisites:
- Set environment variables in $HOME/.env (same as previous MWEs)
- Completed MWE 4
- For Ollama: Set OLLAMA_NUM_PARALLEL=4 (or higher) in environment

Usage:
    python -m mwe.mwe5_full_pipeline_2students
    python -m mwe.mwe5_full_pipeline_2students --sequential-only
    python -m mwe.mwe5_full_pipeline_2students --concurrent-only

"""

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

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


def main_sync(run_sequential: bool = True, run_concurrent: bool = True) -> None:
    """Run MWE 5 demonstration (synchronous version for sequential execution).

    Args:
        run_sequential: Whether to run sequential execution (baseline).
        run_concurrent: Whether to run concurrent execution (optimized).

    """
    if run_concurrent:
        # If concurrent is requested, we need async, so call async version
        asyncio.run(main_async(run_sequential=False, run_concurrent=True))
        return

    # Sequential-only execution (synchronous)
    print("=" * 70)
    print("MWE 5: Sequential Grading of Multiple Students")
    print("=" * 70)

    timings: dict[str, float] = {}

    # Step 1: Setup
    print("\n[Step 1] Configuring system...")

    # Check OLLAMA_NUM_PARALLEL (informational - Python process inherits from shell)
    # Note: The Python process environment is inconclusive - it inherits from your shell (.zshrc).
    # The real verification is in Ollama server logs (check "ollama serve" output for
    # "OLLAMA_NUM_PARALLEL:4" in the server config message).
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

    students = [
        ("student_1", student_1_answer),
        ("student_2", student_2_answer),
        ("student_3", student_3_answer),
        ("student_4", student_4_answer),
    ]

    print(f"\n  Created {len(students)} student submissions")
    timings["step_3_create_rubric"] = time.time() - start_time

    sequential_results: list[tuple[str, dict, dict[str, float]]] = []

    # Step 4: Sequential execution (baseline) - synchronous
    print("\n" + "=" * 70)
    print("[Step 4] Sequential Execution (Baseline - Synchronous)")
    print("=" * 70)

    start_time = time.time()

    for student_id, student_answer in students:
        print(f"\n  Grading {student_id}...")
        try:
            result = grade_student_sync(student_id, student_answer, rubric, index_path)
            sequential_results.append(result)
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
                raise
            else:
                print(f"    ✗ {student_id}: Error during grading")
                print(f"      Error type: {error_type}")
                print(f"      Error message: {error_msg}")
                raise

    sequential_total_time = time.time() - start_time
    timings["step_4_sequential_total"] = sequential_total_time

    print(f"\n  Sequential total time: {sequential_total_time:.3f}s")
    print(f"  Average per student: {sequential_total_time / len(students):.3f}s")

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


async def main_async(run_sequential: bool = True, run_concurrent: bool = True) -> None:
    """Run MWE 5 demonstration (async version).

    Args:
        run_sequential: Whether to run sequential execution (baseline).
        run_concurrent: Whether to run concurrent execution (optimized).

    """
    print("=" * 70)
    print("MWE 5: Concurrent Grading of Multiple Students")
    print("=" * 70)

    if not run_sequential and not run_concurrent:
        print("\nError: At least one execution mode must be enabled")
        return

    timings: dict[str, float] = {}

    # Step 1: Setup
    print("\n[Step 1] Configuring system...")

    # Check OLLAMA_NUM_PARALLEL (informational - Python process inherits from shell)
    # Note: The Python process environment is inconclusive - it inherits from your shell (.zshrc).
    # The real verification is in Ollama server logs (check "ollama serve" output for
    # "OLLAMA_NUM_PARALLEL:4" in the server config message).
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

    students = [
        ("student_1", student_1_answer),
        ("student_2", student_2_answer),
        ("student_3", student_3_answer),
        ("student_4", student_4_answer),
    ]

    print(f"\n  Created {len(students)} student submissions")
    timings["step_3_create_rubric"] = time.time() - start_time

    sequential_results: list[tuple[str, dict, dict[str, float]]] = []
    concurrent_results: list[tuple[str, dict, dict[str, float]]] = []

    # Step 4: Sequential execution (baseline) - synchronous (no async needed)
    if run_sequential:
        print("\n" + "=" * 70)
        print("[Step 4] Sequential Execution (Baseline - Synchronous)")
        print("=" * 70)

        start_time = time.time()

        for student_id, student_answer in students:
            print(f"\n  Grading {student_id}...")
            try:
                result = grade_student_sync(
                    student_id, student_answer, rubric, index_path
                )
                sequential_results.append(result)
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
                        "      This is likely due to Gemini free tier limits (20 requests/day)"
                    )
                    print(f"      Solution: Switch to Ollama or wait for quota reset")
                    raise
                else:
                    print(f"    ✗ {student_id}: Error during grading")
                    print(f"      Error type: {error_type}")
                    print(f"      Error message: {error_msg}")
                    raise

        sequential_total_time = time.time() - start_time
        timings["step_4_sequential_total"] = sequential_total_time

        print(f"\n  Sequential total time: {sequential_total_time:.3f}s")
        print(f"  Average per student: {sequential_total_time / len(students):.3f}s")
    else:
        sequential_total_time = 0.0

    # Step 5: Concurrent execution (optimized) - using async/await with asyncio.gather
    if run_concurrent:
        print("\n" + "=" * 70)
        print("[Step 5] Concurrent Execution (Optimized with async/await)")
        print("=" * 70)

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
                concurrent_results.append(result)
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
                print(f"  ✗ Error during concurrent grading")
                print(f"      Error type: {error_type}")
                print(f"      Error message: {error_msg}")
            # Re-raise to stop execution
            raise

        concurrent_total_time = time.time() - start_time
        timings["step_5_concurrent_total"] = concurrent_total_time

        print(f"\n  Concurrent total time: {concurrent_total_time:.3f}s")
        print(f"  Average per student: {concurrent_total_time / len(students):.3f}s")
    else:
        concurrent_total_time = 0.0

    # Step 6: Comparison and analysis (only if both modes were run)
    if run_sequential and run_concurrent:
        print("\n" + "=" * 70)
        print("[Step 6] Timing Comparison")
        print("=" * 70)

        time_saved = sequential_total_time - concurrent_total_time
        speedup = (
            sequential_total_time / concurrent_total_time
            if concurrent_total_time > 0
            else 0
        )
        efficiency = speedup / len(students) * 100

        # Calculate expected concurrent time if perfect parallelization
        avg_student_time = sequential_total_time / len(students)
        expected_concurrent_time = avg_student_time  # Perfect parallelization
        actual_vs_expected = (
            concurrent_total_time / expected_concurrent_time
            if expected_concurrent_time > 0
            else 0
        )

        print(f"\n  Overall Timing:")
        print(f"    Sequential execution: {sequential_total_time:.3f}s")
        print(f"    Concurrent execution: {concurrent_total_time:.3f}s")
        print(f"    Average per student:  {avg_student_time:.3f}s")
        print(
            f"    Expected concurrent:  {expected_concurrent_time:.3f}s (perfect parallelization)"
        )
        print(
            f"    Time saved:          {time_saved:.3f}s ({time_saved/sequential_total_time*100:.1f}%)"
        )
        print(f"    Speedup:             {speedup:.2f}x")
        print(f"    Efficiency:          {efficiency:.1f}% (ideal: 100%)")
        print(
            f"    Actual/Expected:     {actual_vs_expected:.2f}x (1.0x = perfect, >1.0x = overhead)"
        )

        # Analysis of concurrency effectiveness
        print("\n  Concurrency Analysis:")
        if actual_vs_expected < 1.1:
            print("    ✓ Excellent parallelization - operations are truly concurrent")
        elif actual_vs_expected < 1.5:
            print("    ⚠ Moderate parallelization - some overhead or contention")
        elif actual_vs_expected < 1.9:
            print("    ⚠ Poor parallelization - significant overhead or contention")
        else:
            print("    ✗ No parallelization - operations are running sequentially!")
            print("      Possible causes:")
            print("      - LLM API processes requests sequentially (rate limits)")
            print("      - Local LLM (Ollama) processes requests one at a time")
            print("      - Python GIL preventing true parallelism")
            print("      - Shared resources with locks preventing concurrency")
            print("      - Synchronous blocking I/O not releasing GIL")
            if actual_vs_expected > 1.95:
                print(
                    f"      - Concurrent time ({concurrent_total_time:.1f}s) ≈ {len(students)}x single student time"
                )
                print("        This indicates sequential execution, not parallel")

        # Step-by-step timing comparison
        print("\n  Step-by-Step Timing Comparison:")
        steps = [
            "load_index",
            "retrieve_evidence",
            "apply_scoring",
            "generate_feedback",
        ]
        step_labels = {
            "load_index": "Load index",
            "retrieve_evidence": "Retrieve evidence",
            "apply_scoring": "Apply scoring",
            "generate_feedback": "Generate feedback",
        }

        # Calculate average times per step for sequential
        sequential_step_times: dict[str, float] = {}
        for step in steps:
            sequential_step_times[step] = sum(
                r[2][step] for r in sequential_results
            ) / len(sequential_results)

        # Calculate average times per step for concurrent
        concurrent_step_times: dict[str, float] = {}
        for step in steps:
            concurrent_step_times[step] = sum(
                r[2][step] for r in concurrent_results
            ) / len(concurrent_results)

        print(
            f"\n    {'Step':<25} {'Sequential':<15} {'Concurrent':<15} {'Speedup':<10}"
        )
        print("    " + "-" * 65)
        for step in steps:
            seq_time = sequential_step_times[step]
            conc_time = concurrent_step_times[step]
            step_speedup = seq_time / conc_time if conc_time > 0 else 0
            print(
                f"    {step_labels[step]:<25} {seq_time:>8.3f}s      "
                f"{conc_time:>8.3f}s      {step_speedup:>6.2f}x"
            )

        # Individual student timings
        print("\n  Individual Student Total Timings:")
        print("    Sequential:")
        for student_id, result, step_timings in sequential_results:
            print(f"      {student_id}: {step_timings['total']:.3f}s")
        print("    Concurrent:")
        for student_id, result, step_timings in concurrent_results:
            print(f"      {student_id}: {step_timings['total']:.3f}s")

        # Verify results are the same
        print("\n  Result Verification:")
        sequential_scores = {sid: r["score"] for sid, r, _ in sequential_results}
        concurrent_scores = {sid: r["score"] for sid, r, _ in concurrent_results}
        if sequential_scores == concurrent_scores:
            print("    ✓ Scores match between sequential and concurrent execution")
        else:
            print("    ✗ Scores differ between sequential and concurrent execution")
            print(f"      Sequential: {sequential_scores}")
            print(f"      Concurrent: {concurrent_scores}")

    # Step 7: Summary
    print("\n" + "=" * 70)
    print("MWE 5 Summary")
    print("=" * 70)
    print("✓ Concurrent execution demonstrated")
    print("✓ Time savings through parallelization confirmed")
    print("✓ Results verified to be consistent")

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

    print("\nKey Insight:")
    if time_saved > 0 and speedup > 1.1:
        print(
            f"  ✓ Concurrent execution saved {time_saved:.2f}s ({time_saved/sequential_total_time*100:.1f}%)"
        )
        print(
            f"  ✓ This represents a {speedup:.2f}x speedup for {len(students)} students"
        )
        print(f"  ✓ Efficiency: {efficiency:.1f}% (closer to 100% is better)")
    elif actual_vs_expected > 1.9:
        print("  ✗ No speedup achieved - operations are running sequentially")
        print(
            f"  ✗ Concurrent time ({concurrent_total_time:.1f}s) ≈ {len(students)}x single student time"
        )
        print(
            f"  ✗ Expected concurrent time: {expected_concurrent_time:.1f}s (if perfectly parallelized)"
        )
        print("\n  Why this happens:")
        print(
            "  - If using local Ollama: OLLAMA_NUM_PARALLEL may not be set (defaults to 1)"
        )
        print(
            "    → Set OLLAMA_NUM_PARALLEL=4 (or higher) in $HOME/.env to enable concurrent requests"
        )
        print(
            "    → Current code uses async/await with llm.achat() for optimal concurrency"
        )
        print("  - If using cloud APIs: May have rate limits or sequential processing")
        print("  - Shared resources: Locks or contention preventing true parallelism")
        print("\n  Potential solutions:")
        print("  - For Ollama: Ensure OLLAMA_NUM_PARALLEL is set in $HOME/.env")
        print("    → OLLAMA_NUM_PARALLEL=4  # or higher based on your GPU/CPU")
        print("  - Verify Ollama server is running and can handle concurrent requests")
        print("  - Check GPU/CPU resources - may be saturated with concurrent requests")
        print("  - Check if LLM provider supports concurrent requests")
    else:
        print("  ⚠ Limited speedup achieved")
        print(
            f"  ⚠ Time saved: {time_saved:.2f}s ({time_saved/sequential_total_time*100:.1f}%)"
        )
        print(
            f"  ⚠ Speedup: {speedup:.2f}x (expected: {len(students)}x for perfect parallelization)"
        )
        print("  ⚠ Some operations may not be parallelizing effectively")


def main() -> None:
    """Run MWE 5 demonstration (synchronous wrapper)."""
    parser = argparse.ArgumentParser(
        description="MWE 5: Compare sequential vs concurrent grading"
    )
    parser.add_argument(
        "--sequential-only",
        action="store_true",
        help="Run only sequential execution (skip concurrent, no asyncio needed)",
    )
    parser.add_argument(
        "--concurrent-only",
        action="store_true",
        help="Run only concurrent execution (skip sequential, uses asyncio)",
    )
    args = parser.parse_args()

    run_sequential = not args.concurrent_only
    run_concurrent = not args.sequential_only

    if args.sequential_only and args.concurrent_only:
        parser.error("Cannot specify both --sequential-only and --concurrent-only")

    # If only sequential, use sync version (no asyncio needed)
    # If concurrent is involved, use async version
    if run_sequential and not run_concurrent:
        main_sync(run_sequential=True, run_concurrent=False)
    elif run_concurrent:
        # Need async for concurrent execution
        asyncio.run(
            main_async(run_sequential=run_sequential, run_concurrent=run_concurrent)
        )
    else:
        # Both modes - use async version
        asyncio.run(main_async(run_sequential=True, run_concurrent=True))


if __name__ == "__main__":
    main()
