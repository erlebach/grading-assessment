"""Grading pipeline for dynamic rubrics with two-dimensional scoring.

This module extends grading_pipeline.pipeline to support:
- In-memory vector stores (no persistence)
- Two-dimensional scoring (keyword + semantic)
- Dynamic rubric fields (scoring_weights, semantic_decay, semantic_top_k)

"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from llama_index.core import VectorStoreIndex

from grader.grade_question import extract_keywords, load_rubric
from grader.lmql_grading import LMQLGrader
from grading_pipeline.index_builder_in_memory import (
    InMemoryVectorStore,
    build_multi_indexes_in_memory,
    load_multi_indexes_in_memory,
)
from grading_pipeline.pipeline import write_results
from retrieval_core.multi_retriever import MultiIndexRetriever


def _load_retrieval_params_from_config(cfg: dict[str, Any]) -> dict[str, float | int]:
    """Load retrieval parameters from the sources config.

    The `grading_dynamic_rubrics/config/sources.yaml` file is the source of truth
    for retrieval behavior. Values in the YAML should override any code defaults.

    Args:
        cfg: Parsed YAML configuration dictionary.

    Returns:
        Dictionary containing:
        - top_k_per_index: int
        - final_top_k: int
        - similarity_threshold: float

    """
    retrieval_cfg = (cfg.get("retrieval", {}) or {}) if isinstance(cfg, dict) else {}

    # Defaults are only used when the YAML omits the value.
    top_k_per_index = int(retrieval_cfg.get("top_k_per_index", 10))
    final_top_k = int(retrieval_cfg.get("final_top_k", 5))
    similarity_threshold = float(retrieval_cfg.get("similarity_threshold", 0.0))

    return {
        "top_k_per_index": top_k_per_index,
        "final_top_k": final_top_k,
        "similarity_threshold": similarity_threshold,
    }


def apply_rubric_scoring_dynamic(
    rubric: dict[str, Any],
    student_answer: str,
    evidence_by_criterion: dict[str, list[dict[str, Any]]],
    debug: bool = False,
) -> dict[str, dict[str, Any]]:
    """Apply dynamic rubric scoring with keyword + semantic dimensions.

    This implements two-dimensional scoring as specified in CURRENT_GRADING_STRATEGY.md:
    dimension_score = (keyword_weight × keyword_score + semantic_weight × semantic_score) × max_points

    Args:
        rubric: Dynamic rubric dictionary with criteria and scoring_weights.
        student_answer: Student's answer text.
        evidence_by_criterion: Evidence retrieved for each criterion (with scores).
        debug: If True, print detailed scoring information.

    Returns:
        Dictionary mapping criterion_id to score information.

    """
    scores = {}
    answer_lower = student_answer.lower()

    # Get global defaults from rubric
    semantic_top_k = rubric.get("semantic_top_k", 5)
    # semantic_decay is currently not used for scoring, because scoring does not
    # depend on similarity/reranker numbers (only span selection does).
    semantic_decay = rubric.get("semantic_decay", "linear")

    for criterion in rubric.get("criteria", []):
        criterion_id = criterion["criterion_id"]
        max_points = criterion["points"]
        description = criterion["description"].lower()

        # Get scoring weights for this criterion (default to 50-50)
        scoring_weights = rubric.get("scoring_weights", {}).get(
            criterion_id, {"keyword": 0.5, "semantic": 0.5}
        )
        keyword_weight = scoring_weights.get("keyword", 0.5)
        semantic_weight = scoring_weights.get("semantic", 0.5)

        # 1. Keyword scoring (0-1)
        keywords = extract_keywords(description)
        found_keywords = [kw for kw in keywords if kw in answer_lower]
        missing_keywords = [kw for kw in keywords if kw not in answer_lower]

        if keywords:
            keyword_score = len(found_keywords) / len(keywords)
        else:
            keyword_score = 0.0

        # 2. Semantic scoring (0-1)
        #
        # Per your intended design (and Chu et al. style pipelines):
        # - similarity / reranker scores are ONLY used to *select spans*
        # - grading should NOT use those numeric scores
        #
        # So here we derive a semantic signal purely from the presence/amount of
        # retrieved evidence spans, not their similarity/reranker numbers.
        evidence_list = evidence_by_criterion.get(criterion_id, [])
        if evidence_list:
            # Scale by how many spans we actually have available up to semantic_top_k.
            semantic_score = min(1.0, len(evidence_list) / float(semantic_top_k))
        else:
            semantic_score = 0.0

        # 3. Combine scores using weights
        combined_score = (
            keyword_weight * keyword_score + semantic_weight * semantic_score
        )

        # 4. Scale by max_points
        final_score = int(combined_score * max_points)

        # Debug: Print scoring details
        if debug:
            print(f"[DEBUG] Criterion: {criterion_id}")
            print(
                f"  keyword_score: {keyword_score:.3f} (found {len(found_keywords)}/{len(keywords)} keywords)"
            )
            print(f"  semantic_score: {semantic_score:.3f}")
            print(f"  weights: keyword={keyword_weight}, semantic={semantic_weight}")
            print(f"  combined_score: {combined_score:.3f}")
            print(f"  final_score: {final_score}/{max_points}")

        # Validation: Check for negative scores (always warn)
        if final_score < 0:
            print(f"[WARNING] Negative score detected! final_score={final_score}")
            print(f"  Criterion: {criterion_id}")
            print(f"  keyword_score={keyword_score}, semantic_score={semantic_score}")
            print(f"  combined_score={combined_score}, max_points={max_points}")
            print(f"  Evidence count: {len(evidence_list)}")
            if evidence_list:
                print(
                    f"  Evidence scores: {[e.get('rerank_score', e.get('score', 0.0)) for e in evidence_list[:3]]}"
                )

        scores[criterion_id] = {
            "score": final_score,
            "max_score": max_points,
            "keyword_score": keyword_score,
            "semantic_score": semantic_score,
            "combined_score": combined_score,
            "keywords": keywords,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
        }

    return scores


def setup_grading_environment(
    question_id: str,
    rubric_path: Path,
    config_path: Path,
) -> tuple[
    MultiIndexRetriever, dict[str, Any], dict[str, float], list[str] | None, dict[str, float | int]
]:
    """Setup grading environment for a question (in-memory indexes).

    Args:
        question_id: Question identifier (for logging).
        rubric_path: Path to the rubric YAML file.
        config_path: Path to sources configuration YAML file.

    Returns:
        Tuple of (retriever, rubric, timing_info, index_subset, retrieval_params).

    """
    print("[Index Setup] Loading/building persisted in-memory indexes...", flush=True)
    start_time = time.time()

    # Persist in-memory indexes under grading_dynamic_rubrics/tmp/in_memory_indexes/
    persist_dir = Path(__file__).parent / "tmp" / "in_memory_indexes"

    # Ensure embedding model is initialized before any verification/loading.
    from config.llm_config import setup_llamaindex_defaults

    setup_llamaindex_defaults()

    # Load runtime.active_indexes if present.
    import yaml

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    active_indexes = (cfg.get("runtime", {}) or {}).get("active_indexes")
    index_subset = active_indexes if isinstance(active_indexes, list) else None
    retrieval_params = _load_retrieval_params_from_config(cfg)

    try:
        indexes = load_multi_indexes_in_memory(
            config_path=config_path,
            persist_dir=persist_dir,
            index_subset=index_subset,
        )
    except Exception:
        indexes = build_multi_indexes_in_memory(
            config_path=config_path,
            persist_dir=persist_dir,
            index_subset=index_subset,
            force_rebuild=False,
        )

    build_time = time.time() - start_time

    print(f"[Index Setup] Indexes ready in {build_time:.2f}s", flush=True)

    # Create retriever
    retriever = MultiIndexRetriever(indexes)

    # Load rubric
    rubric = load_rubric(rubric_path)

    timing = {"index_setup": build_time}

    return retriever, rubric, timing, index_subset, retrieval_params


def _grade_student_core(
    student_id: str,
    student_answer: str,
    question_text: str,
    rubric: dict[str, Any],
    retriever: MultiIndexRetriever,
    index_subset: list[str] | None,
    retrieval_params: dict[str, float | int],
    answer_type: str | None = None,
) -> dict[str, Any]:
    """Core grading logic for a single student with dynamic rubrics.

    Uses two-dimensional scoring (keyword + semantic) for dynamic rubrics.

    Args:
        student_id: Student identifier.
        student_answer: Student's answer text.
        question_text: The question text that was asked.
        rubric: Dynamic rubric dictionary.
        retriever: DualIndexRetriever instance.
        answer_type: Optional answer type from submission.

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
            criterion_id = str(criterion.get("criterion_id", "")).strip() or None
            query = f"{criterion['description']} {student_answer}"
            top_k_per_index = int(retrieval_params.get("top_k_per_index", 10))
            final_top_k = int(retrieval_params.get("final_top_k", 5))
            similarity_threshold = float(
                retrieval_params.get("similarity_threshold", 0.0)
            )
            evidence = retriever.retrieve(
                query=query,
                top_k_per_index=top_k_per_index,
                final_top_k=final_top_k,
                similarity_threshold=similarity_threshold,
                index_subset=index_subset,
                trace_label=criterion_id,
            )
            evidence_by_criterion[criterion["criterion_id"]] = evidence

    retrieve_time = time.time() - step_start
    step_timings["retrieve_evidence"] = retrieve_time
    step_timings["rerank_evidence"] = 0.0  # Included in retrieve_evidence

    # Apply dynamic rubric scoring (keyword + semantic)
    step_start = time.time()
    # Enable debug mode via environment variable
    import os

    debug_mode = os.environ.get("GRADING_DEBUG", "").lower() in ("1", "true", "yes")
    scores = apply_rubric_scoring_dynamic(
        rubric, student_answer, evidence_by_criterion, debug=debug_mode
    )
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
        # Preserve keyword and semantic information
        if "keywords" in info:
            item["keywords"] = info.get("keywords", [])
            item["found_keywords"] = info.get("found_keywords", [])
            item["missing_keywords"] = info.get("missing_keywords", [])
        if "keyword_score" in info:
            item["keyword_score"] = info.get("keyword_score", 0.0)
        if "semantic_score" in info:
            item["semantic_score"] = info.get("semantic_score", 0.0)
        if "combined_score" in info:
            item["combined_score"] = info.get("combined_score", 0.0)

        rubric_items.append(item)

    result = {
        "student_id": student_id,
        "question_id": grading_result["question_id"],
        "question_text": question_text,
        "answer": student_answer,
        "score": grading_result["total_score"],
        "max_score": grading_result["max_score"],
        "rubric_items": rubric_items,
        "citations": [ev["source_id"] for ev in grading_result["evidence_used"]],
        "feedback": grading_result["feedback"],
        "timings": step_timings,
    }

    # Include answer_type if provided
    if answer_type is not None:
        result["answer_type"] = answer_type

    return result


def grade_question_batch(
    question_id: str,
    rubric_path: Path,
    submissions: list[dict[str, Any]],
    config_path: Path,
    execution_mode: str = "sequential",
    log_path: Path | None = None,
    log_file_name: str = "grading.log",
    enable_transparent: bool = True,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Grade all students for a single question (in-memory indexes).

    Args:
        question_id: Question identifier.
        rubric_path: Path to the rubric YAML file.
        submissions: List of submission dictionaries.
        config_path: Path to sources configuration YAML file.
        execution_mode: Execution mode ("sequential", "batched", "async").
        log_path: Directory where log files are written (default: logs).
        log_file_name: Name of the main log file (default: grading.log).
        enable_transparent: If True, write transparency traces to transparency.log.
        output_path: Optional path to output JSON file.

    Returns:
        List of grading results, one per student.

    """
    # Setup main log file (always write normal stdout messages to log)
    project_root = Path(__file__).resolve().parents[1]
    if log_path is None:
        # Default: logs directory under project root (autograder/logs)
        log_dir = project_root / "logs"
    else:
        candidate = Path(log_path)
        # If relative, interpret relative to project root for consistency
        log_dir = candidate if candidate.is_absolute() else project_root / candidate

    # Clear log directory before starting (files only)
    log_dir.mkdir(parents=True, exist_ok=True)
    for p in log_dir.iterdir():
        if p.is_file():
            p.unlink()

    log_file_path = log_dir / log_file_name
    log_handle = open(log_file_path, "w", buffering=1)  # Line buffered

    def log_print(msg: str) -> None:
        """Print to stdout and log file (unbuffered).

        Args:
            msg: Message to print (should not include trailing newline).

        """
        print(msg, flush=True)
        log_handle.write(msg + "\n")
        log_handle.flush()

    # Setup transparency log (only if enabled)
    transparent_handle = None
    transparent_log_path = None
    if enable_transparent:
        transparent_log_path = log_dir / "transparency.log"
        transparent_handle = open(transparent_log_path, "w", buffering=1)

        def transparent_write(msg: str) -> None:
            """Write transparency traces to file only.

            Args:
                msg: Trace message (may include trailing newline).

            """
            transparent_handle.write(msg)
            transparent_handle.flush()

    # Setup environment (in-memory indexes)
    retriever, rubric, timing, index_subset, retrieval_params = setup_grading_environment(
        question_id,
        rubric_path,
        config_path,
    )
    if enable_transparent:
        retriever.enable_transparency(transparent_write)
        log_print(f"[Transparent] Writing trace log to: {transparent_log_path}")

    results = []

    for submission in submissions:
        student_id = submission["student_id"]
        student_answer = submission["answer"]
        question_text = submission.get("question_text", rubric.get("question_text", ""))
        # Extract answer_type from metadata if present
        metadata = submission.get("metadata", {})
        answer_type = None
        if isinstance(metadata, dict):
            answer_type = metadata.get("answer_type")
        if answer_type is None:
            answer_type = submission.get("answer_type")

        answer_type_str = f" ({answer_type})" if answer_type else ""
        log_print(
            f"[Grading] Processing {student_id} for {question_id}{answer_type_str}..."
        )

        try:
            result = _grade_student_core(
                student_id,
                student_answer,
                question_text,
                rubric,
                retriever,
                index_subset,
                retrieval_params,
                answer_type,
            )
            results.append(result)
            log_print(
                f"[Grading] ✓ {student_id} completed for {question_id}{answer_type_str}"
            )

            # Write results incrementally if output_path is provided
            if output_path is not None:
                write_results(results, question_id, output_path, per_student=False)
        except Exception as e:
            error_msg = f"Error grading {student_id}: {type(e).__name__}: {e}"
            log_print(f"[Grading] ✗ {error_msg}")
            error_result = {
                "student_id": student_id,
                "question_id": question_id,
                "error": error_msg,
            }
            if answer_type is not None:
                error_result["answer_type"] = answer_type
            results.append(error_result)

            # Write results incrementally even on error
            if output_path is not None:
                write_results(results, question_id, output_path, per_student=False)

    if transparent_handle:
        transparent_handle.close()
    log_handle.close()  # Always close main log file

    return results


def grade_single_student(
    question_id: str,
    rubric_path: Path,
    submission: dict[str, Any],
    config_path: Path,
    log_path: Path | None = None,
    log_file_name: str = "grading.log",
    enable_transparent: bool = True,
) -> dict[str, Any]:
    """Grade a single student (wrapper around grade_question_batch).

    Args:
        question_id: Question identifier.
        rubric_path: Path to the rubric YAML file.
        submission: Single submission dictionary.
        config_path: Path to sources configuration YAML file.
        log_path: Directory where log files are written (default: logs).
        log_file_name: Name of the main log file (default: grading.log).
        enable_transparent: If True, write transparency traces to transparency.log.

    Returns:
        Single grading result dictionary.

    """
    results = grade_question_batch(
        question_id=question_id,
        rubric_path=rubric_path,
        submissions=[submission],
        config_path=config_path,
        execution_mode="sequential",
        log_path=log_path,
        log_file_name=log_file_name,
        enable_transparent=enable_transparent,
    )

    return results[0]


def print_index_diagnostics(
    config_path: Path | None = None,
    persist_dir: Path | None = None,
    index_subset: list[str] | None = None,
) -> None:
    """Print diagnostics for all active in-memory indexes.

    Diagnostics include:
    - Number of chunks (nodes) per index
    - Minimum/maximum/average chunk size in characters
    - Approximate min/max/average chunk size in tokens (4 chars ≈ 1 token)

    Args:
        config_path: Optional path to YAML config file. If None, uses default
            location (grading_dynamic_rubrics/config/sources.yaml).
        persist_dir: Optional directory containing persisted indexes. If None, uses
            the default in-memory persist directory (grading_dynamic_rubrics/tmp/in_memory_indexes).
        index_subset: Optional list of index IDs to restrict diagnostics to. If None,
            uses the active indexes from the config.

    """
    # Use default paths if not provided
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "sources.yaml"
    if persist_dir is None:
        persist_dir = Path(__file__).parent / "tmp" / "in_memory_indexes"

    # Load config to determine which indexes are active (without touching any LLM
    # provider / embedder initialization). This function is diagnostics-only and
    # should work without OpenAI keys.
    import yaml

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    configured_indexes = cfg.get("indexes", {}) or {}
    active_indexes_cfg = (cfg.get("runtime", {}) or {}).get("active_indexes")
    active_indexes = (
        active_indexes_cfg
        if isinstance(active_indexes_cfg, list) and active_indexes_cfg
        else list(configured_indexes.keys())
    )
    if index_subset is not None:
        active_indexes = index_subset

    print("\n[Index Diagnostics]")
    print(f"  persist_dir: {persist_dir}")
    print(f"  active_indexes: {active_indexes}")

    for index_id in active_indexes:
        index_cfg = configured_indexes.get(index_id, {}) or {}
        collection_name = str(index_cfg.get("collection_name", index_id))
        pkl_path = Path(persist_dir) / f"{collection_name}.pkl"

        if not pkl_path.exists():
            print(f"- {index_id}: missing pickle file: {pkl_path}")
            continue

        vector_store = InMemoryVectorStore.load_from_pickle(pkl_path)

        # Collect chunk lengths
        texts = [node.text for node in vector_store.nodes.values()]
        num_chunks = len(texts)

        if num_chunks == 0:
            print(f"- {index_id}: 0 chunks")
            continue

        lengths = [len(t) for t in texts]
        min_chars = min(lengths)
        max_chars = max(lengths)
        avg_chars = sum(lengths) / float(num_chunks)

        # Approximate tokens as 4 characters per token
        def _chars_to_tokens(chars: int | float) -> float:
            return float(chars) / 4.0

        min_tokens = _chars_to_tokens(min_chars)
        max_tokens = _chars_to_tokens(max_chars)
        avg_tokens = _chars_to_tokens(avg_chars)

        print(f"- {index_id}:")
        print(f"    chunks       : {num_chunks}")
        print(
            f"    chars        : min={min_chars}, max={max_chars}, "
            f"avg={avg_chars:.1f}"
        )
        print(
            f"    tokens (≈4/ch): min={min_tokens:.1f}, "
            f"max={max_tokens:.1f}, avg={avg_tokens:.1f}"
        )


# Re-export write_results for convenience
__all__ = [
    "apply_rubric_scoring_dynamic",
    "setup_grading_environment",
    "grade_question_batch",
    "grade_single_student",
    "write_results",
    "print_index_diagnostics",
]


if __name__ == "__main__":
    # Test pipeline setup
    test_config = Path(__file__).parent / "config" / "sources.yaml"
    test_rubric = Path(__file__).parent.parent / "rubrics_dynamic" / "yaml" / "q01.yaml"

    if test_config.exists() and test_rubric.exists():
        print("Testing dynamic rubrics pipeline setup...")
        try:
            retriever, rubric, timing, _index_subset, retrieval_params = (
                setup_grading_environment("q01", test_rubric, test_config)
            )
            print(f"✓ Setup complete in {timing['index_setup']:.2f}s")
            print(f"  Rubric: {rubric.get('question_id', 'unknown')}")
            print(f"  Retriever: {type(retriever).__name__}")
            print(f"  Retrieval params: {retrieval_params}")
            print(f"  Scoring weights: {rubric.get('scoring_weights', {})}")
            print(f"  Semantic top_k: {rubric.get('semantic_top_k', 'N/A')}")
            print(f"  Semantic decay: {rubric.get('semantic_decay', 'N/A')}")
        except Exception as e:
            print(f"⚠ Test failed: {e}")
    else:
        print(f"⚠ Test files not found")
        print(f"  Config: {test_config}")
        print(f"  Rubric: {test_rubric}")
