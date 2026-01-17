"""Batch-by-question grading pipeline.

This module implements the core grading pipeline that processes submissions
in batches grouped by question, with optimized index loading and error handling.

"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from grader.grade_question import apply_rubric_scoring, load_rubric
from grader.lmql_grading import LMQLGrader
from grading_pipeline.index_builder import build_or_update_dual_indexes
from grading_pipeline.manifest import load_manifest
from retrieval_core.retriever import DualIndexRetriever


def setup_grading_environment(
    question_id: str,
    rubric_path: Path,
    persist_dir: Path,
    config_path: Path,
) -> tuple[DualIndexRetriever, dict[str, Any], dict[str, float]]:
    """Setup grading environment for a question.

    - Loads or builds dual indexes (incremental)
    - Times the operation
    - Outputs which files are being indexed
    - Creates DualIndexRetriever
    - Loads rubric

    Args:
        question_id: Question identifier (for logging).
        rubric_path: Path to the rubric YAML file.
        persist_dir: Directory for persistent ChromaDB indexes.
        config_path: Path to sources configuration YAML file.

    Returns:
        Tuple of (retriever, rubric, timing_info).

    """
    print(f"[Index Setup] Building or updating indexes...", flush=True)
    start_time = time.time()

    # Build or update indexes
    word_index, sentence_index = build_or_update_dual_indexes(
        config_path, persist_dir
    )

    build_time = time.time() - start_time

    # Output indexed files (from manifest)
    manifest = load_manifest(persist_dir)
    indexed_files = [
        source["file_path"]
        for source in manifest.get("sources", {}).values()
    ]
    print(f"[Index Setup] Indexed files:", flush=True)
    for file_path in indexed_files:
        print(f"  - {file_path}", flush=True)
    print(f"[Index Setup] Index ready in {build_time:.2f}s", flush=True)

    # Create retriever
    retriever = DualIndexRetriever(word_index, sentence_index)

    # Load rubric
    rubric = load_rubric(rubric_path)

    timing = {"index_setup": build_time}

    return retriever, rubric, timing


def _grade_student_core(
    student_id: str,
    student_answer: str,
    rubric: dict[str, Any],
    retriever: DualIndexRetriever,
) -> dict[str, Any]:
    """Core grading logic for a single student.

    Reuses logic from retrieval_core/pipeline.py but adapted for grading_pipeline:
    - Uses DualIndexRetriever (already initialized)
    - Retrieves evidence per criterion
    - Applies rubric scoring
    - Generates LMQL feedback

    Args:
        student_id: Student identifier.
        student_answer: Student's answer text.
        rubric: Rubric dictionary.
        retriever: DualIndexRetriever instance.

    Returns:
        Formatted grading result dictionary.

    """
    step_timings: dict[str, float] = {}
    overall_start = time.time()

    # Retrieve evidence for rubric with dual-index and reranking
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
    step_timings["rerank_evidence"] = 0.0  # Included in retrieve_evidence

    # Apply rubric scoring
    step_start = time.time()
    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)
    step_timings["apply_scoring"] = time.time() - step_start

    # Generate LMQL-constrained feedback
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

    # Format result to match expected structure
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

    result = {
        "student_id": student_id,
        "question_id": grading_result["question_id"],
        "score": grading_result["total_score"],
        "max_score": grading_result["max_score"],
        "rubric_items": rubric_items,
        "citations": [
            ev["source_id"] for ev in grading_result["evidence_used"]
        ],
        "feedback": grading_result["feedback"],
        "timings": step_timings,
    }

    return result


def grade_question_batch(
    question_id: str,
    rubric_path: Path,
    submissions: list[dict[str, Any]],
    persist_dir: Path,
    config_path: Path,
    execution_mode: str = "sequential",
    log_file: Path | None = None,
) -> list[dict[str, Any]]:
    """Grade all students for a single question.

    Error Handling:
    - Continue on error (don't stop batch)
    - Mark failed students with error field
    - Unbuffered output to stdout or log file

    Args:
        question_id: Question identifier.
        rubric_path: Path to the rubric YAML file.
        submissions: List of submission dictionaries.
        persist_dir: Directory for persistent ChromaDB indexes.
        config_path: Path to sources configuration YAML file.
        execution_mode: Execution mode ("sequential", "batched", "async").
            Currently only "sequential" is implemented.
        log_file: Optional path to log file for unbuffered output.

    Returns:
        List of grading results, one per student.
        Failed students have {"error": "error message"} instead of full result.

    """
    # Setup logging (unbuffered)
    log_handle = None
    if log_file:
        log_handle = open(log_file, "w", buffering=1)  # Line buffered

    def log_print(msg: str) -> None:
        """Print with unbuffered output."""
        print(msg, flush=True)
        if log_handle:
            log_handle.write(msg + "\n")
            log_handle.flush()

    # Setup environment
    retriever, rubric, timing = setup_grading_environment(
        question_id, rubric_path, persist_dir, config_path
    )

    results = []

    for submission in submissions:
        student_id = submission["student_id"]
        student_answer = submission["answer"]

        log_print(f"[Grading] Processing {student_id}...")

        try:
            result = _grade_student_core(
                student_id, student_answer, rubric, retriever
            )
            results.append(result)
            log_print(f"[Grading] ✓ {student_id} completed")
        except Exception as e:
            error_msg = f"Error grading {student_id}: {type(e).__name__}: {e}"
            log_print(f"[Grading] ✗ {error_msg}")
            results.append(
                {
                    "student_id": student_id,
                    "question_id": question_id,
                    "error": error_msg,
                }
            )

    if log_handle:
        log_handle.close()

    return results


def write_results(
    results: list[dict[str, Any]],
    question_id: str,
    output_path: Path,
    per_student: bool = False,
) -> None:
    """Write grading results to file(s).

    Development: One file per question
    Future: Option to write per-student files too

    Args:
        results: List of grading result dictionaries.
        question_id: Question identifier.
        output_path: Path to output JSON file (batch file).
        per_student: If True, also write individual files per student.

    """
    if per_student:
        # Write individual files
        for result in results:
            if "error" not in result:
                student_id = result["student_id"]
                student_file = output_path.parent / f"{student_id}_{question_id}.json"
                with open(student_file, "w") as f:
                    json.dump(result, f, indent=2)

    # Always write batch file
    batch_result = {
        "question_id": question_id,
        "graded_at": datetime.now().isoformat(),
        "total_students": len(results),
        "successful": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
        "students": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(batch_result, f, indent=2)


def grade_single_student(
    question_id: str,
    rubric_path: Path,
    submission: dict[str, Any],
    persist_dir: Path,
    config_path: Path,
) -> dict[str, Any]:
    """Grade a single student (wrapper around grade_question_batch).

    This is just grade_question_batch with a batch of size 1.

    Args:
        question_id: Question identifier.
        rubric_path: Path to the rubric YAML file.
        submission: Single submission dictionary.
        persist_dir: Directory for persistent ChromaDB indexes.
        config_path: Path to sources configuration YAML file.

    Returns:
        Single grading result dictionary.

    """
    results = grade_question_batch(
        question_id=question_id,
        rubric_path=rubric_path,
        submissions=[submission],
        persist_dir=persist_dir,
        config_path=config_path,
        execution_mode="sequential",
    )

    return results[0]


if __name__ == "__main__":
    # Test pipeline setup
    test_config = Path(__file__).parent / "config" / "sources.yaml"
    
    # Use test directory if running from test script, otherwise use production tmp
    # Check if we're in a test environment by looking for tests/ directory
    tests_dir = Path(__file__).parent.parent / "tests"
    if tests_dir.exists():
        # Running from test - use test directory
        test_persist = tests_dir / "tmp_chroma_indexes" / "pipeline_test"
    else:
        # Production use - use production tmp
        test_persist = Path(__file__).parent / "tmp" / "chroma_db"
    
    test_rubric = Path(__file__).parent.parent / "rubrics" / "q01.yaml"

    if test_config.exists() and test_rubric.exists():
        print("Testing pipeline setup...")
        try:
            retriever, rubric, timing = setup_grading_environment(
                "q01", test_rubric, test_persist, test_config
            )
            print(f"✓ Setup complete in {timing['index_setup']:.2f}s")
            print(f"  Rubric: {rubric.get('question_id', 'unknown')}")
            print(f"  Retriever: {type(retriever).__name__}")
        except Exception as e:
            print(f"⚠ Test failed: {e}")
    else:
        print(f"⚠ Test files not found")
