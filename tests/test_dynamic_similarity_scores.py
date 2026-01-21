"""Tests for similarity score validation in dynamic rubrics pipeline.

This test verifies that similarity scores from evidence retrieval are handled
correctly. Note that:

1. Cosine similarity scores (from initial retrieval) should be in [-1, 1]
2. Cross-encoder reranker scores (`reranker_score`) can be outside [-1, 1]
3. The grading pipeline should use cosine similarity for scoring, not reranker logits

The test checks that:
- Initial cosine similarity scores are in valid range
- Cross-encoder scores are detected and handled
- Final scores don't become negative due to invalid input scores
"""

from pathlib import Path

import pytest

from config.llm_config import setup_llamaindex_defaults
from grading_dynamic_rubrics.config_loader import get_rubric_path
from grading_dynamic_rubrics.pipeline import setup_grading_environment
from retrieval_core.retriever import DualIndexRetriever


def test_similarity_scores_in_valid_range() -> None:
    """Test similarity scores from evidence retrieval.

    This test verifies:
    1. Initial cosine similarity scores (from vector search) are in [-1, 1]
    2. Cross-encoder rerank scores are detected (may be outside [-1, 1])
    3. Invalid scores are flagged for proper handling

    Note: Cross-encoder rerankers produce raw relevance scores that can be
    negative or > 1, which is different from cosine similarity.

    """
    # Setup
    setup_llamaindex_defaults()

    config_path = (
        Path(__file__).parent.parent
        / "grading_dynamic_rubrics"
        / "config"
        / "sources.yaml"
    )
    rubric_path = Path(__file__).parent.parent / "rubrics_dynamic" / "yaml" / "q01.yaml"

    if not (config_path.exists() and rubric_path.exists()):
        pytest.skip("Required files not found for similarity score test")

    # Setup grading environment (in-memory indexes)
    retriever, rubric, _, _ = setup_grading_environment("q01", rubric_path, config_path)

    # Test query
    test_answer = "An object is a row-level entity in the dataset. An attribute is a column-level variable."

    # Retrieve evidence once with a stable query to ensure we have results to validate.
    query = "object attribute data table nominal ordinal interval ratio"
    results = retriever.retrieve(
        query=query,
        top_k_per_index=10,
        final_top_k=10,
        index_subset=None,
    )

    all_scores = []
    invalid_scores = []

    # Check all similarity scores on returned results
    for evidence in results:
        # Check reranker_score (from cross-encoder reranking)
        # NOTE: Cross-encoder scores can be outside [-1, 1] - this is expected.
        reranker_score = evidence.get("reranker_score")
        if reranker_score is not None:
            all_scores.append(("reranker_score", reranker_score, evidence))
            if not (-1.0 <= reranker_score <= 1.0):
                invalid_scores.append(
                    (
                        "reranker_score",
                        reranker_score,
                        evidence.get("source_id", "unknown"),
                    )
                )

        # Check score (cosine similarity from vector search)
        score = evidence.get("score")
        if score is not None:
            all_scores.append(("score", score, evidence))
            if not (-1.0 <= float(score) <= 1.0):
                invalid_scores.append(
                    ("score", score, evidence.get("source_id", "unknown"))
                )

    # Report results
    print(f"\n[Test] Found {len(all_scores)} similarity scores")
    print(f"[Test] Scores outside [-1, 1]: {len(invalid_scores)}")

    # Separate reranker scores (expected to be outside range) from cosine scores (should be in range)
    rerank_out_of_range = [s for s in invalid_scores if s[0] == "reranker_score"]
    cosine_out_of_range = [s for s in invalid_scores if s[0] == "score"]

    print(
        f"[Test]   - reranker_score outside [-1, 1]: {len(rerank_out_of_range)} "
        "(expected for cross-encoder)"
    )
    print(
        f"[Test]   - score (cosine) outside [-1, 1]: {len(cosine_out_of_range)} (should be 0)"
    )

    if invalid_scores:
        print("\n[Test] Scores outside [-1, 1] detected:")
        for score_type, score_value, source_id in invalid_scores:
            score_type_label = (
                "reranker_score (cross-encoder)"
                if score_type == "reranker_score"
                else "score (cosine)"
            )
            print(f"  {score_type_label}: {score_value:.6f} from {source_id}")

    # Assertions
    assert len(results) > 0, (
        "No evidence retrieved to validate scores. "
        "This likely indicates indexes are empty or retrieval failed."
    )
    assert len(all_scores) > 0, "No scores present in retrieved evidence objects."

    if invalid_scores:
        # Print detailed information for debugging
        print("\n[Test] Detailed evidence information for invalid scores:")
        for score_type, score_value, source_id in invalid_scores[:3]:  # Show first 3
            print(f"\n  {score_type}: {score_value}")
            print(f"  Source: {source_id}")
            # Find the evidence object
            for evidence in [
                ev
                for ev_type, ev_score, ev in all_scores
                if ev_type == score_type and abs(ev_score - score_value) < 0.001
            ]:
                print(f"  Evidence keys: {list(evidence.keys())}")
                print(
                    f"  Evidence text (first 100 chars): {evidence.get('text', '')[:100]}"
                )

    # Main assertion: cosine similarity scores must be in [-1, 1]
    # Cross-encoder rerank scores can be outside this range (this is expected)
    assert (
        len(cosine_out_of_range) == 0
    ), f"Found {len(cosine_out_of_range)} cosine similarity scores outside [-1, 1] range. This indicates a bug in the vector store."

    # Warn about rerank scores outside range (they need normalization in scoring)
    if rerank_out_of_range:
        print(
            f"\n[WARNING] Found {len(rerank_out_of_range)} cross-encoder scores outside [-1, 1]"
        )
        print(
            "  These scores need to be normalized/clamped in apply_rubric_scoring_dynamic()"
        )
        print("  Example scores:", [f"{s[1]:.3f}" for s in rerank_out_of_range[:3]])

    print("✓ test_similarity_scores_in_valid_range passed")


def test_similarity_scores_from_retriever_interface() -> None:
    """Test similarity scores directly from DualIndexRetriever interface.

    This test checks the raw scores from the retriever before any processing.

    """
    setup_llamaindex_defaults()

    config_path = (
        Path(__file__).parent.parent
        / "grading_dynamic_rubrics"
        / "config"
        / "sources.yaml"
    )
    rubric_path = Path(__file__).parent.parent / "rubrics_dynamic" / "yaml" / "q01.yaml"

    if not (config_path.exists() and rubric_path.exists()):
        pytest.skip("Required files not found for retriever interface test")

    # Setup
    retriever, rubric, _, _ = setup_grading_environment("q01", rubric_path, config_path)

    # Test with a simple query
    query = "object attribute data table"
    results = retriever.retrieve(query, top_k_per_index=5, final_top_k=3)

    invalid_scores = []
    all_scores = []

    for result in results:
        # Check reranker_score (cross-encoder)
        reranker_score = result.get("reranker_score")
        if reranker_score is not None:
            all_scores.append(("reranker_score", reranker_score))
            if not (-1.0 <= reranker_score <= 1.0):
                invalid_scores.append(("reranker_score", reranker_score))

        # Check score
        score = result.get("score")
        if score is not None:
            all_scores.append(("score", score))
            if not (-1.0 <= score <= 1.0):
                invalid_scores.append(("score", score))

    print(f"\n[Test] Retrieved {len(results)} results")
    print(f"[Test] Found {len(all_scores)} scores")
    print(f"[Test] Invalid scores: {len(invalid_scores)}")

    if invalid_scores:
        print("\n[Test] Invalid scores from retriever:")
        for score_type, score_value in invalid_scores:
            print(f"  {score_type}: {score_value:.6f}")

    assert len(all_scores) > 0, "No scores found from retriever"

    # All scores must be in valid range
    assert (
        len(invalid_scores) == 0
    ), f"Retriever returned {len(invalid_scores)} scores outside [-1, 1] range"

    print("✓ test_similarity_scores_from_retriever_interface passed")


def test_similarity_scores_in_pipeline() -> None:
    """Test similarity scores as they flow through the grading pipeline.

    This test verifies scores are valid when used in apply_rubric_scoring_dynamic.

    """
    setup_llamaindex_defaults()

    config_path = (
        Path(__file__).parent.parent
        / "grading_dynamic_rubrics"
        / "config"
        / "sources.yaml"
    )
    rubric_path = Path(__file__).parent.parent / "rubrics_dynamic" / "yaml" / "q01.yaml"

    if not (config_path.exists() and rubric_path.exists()):
        pytest.skip("Required files not found for pipeline test")

    import yaml

    from grading_dynamic_rubrics.pipeline import apply_rubric_scoring_dynamic

    # Load rubric
    with open(rubric_path) as f:
        rubric = yaml.safe_load(f)

    # Setup retriever
    retriever, _, _, _ = setup_grading_environment("q01", rubric_path, config_path)

    # Test answer
    student_answer = "An object is a row in a data table. An attribute is a column."

    # Retrieve evidence (as pipeline does)
    evidence_by_criterion = {}
    invalid_scores = []

    for criterion in rubric.get("criteria", []):
        if criterion.get("evidence_required", False):
            query = f"{criterion['description']} {student_answer}"
            evidence = retriever.retrieve(
                query=query,
                top_k_per_index=5,
                final_top_k=3,
                index_subset=None,
            )
            evidence_by_criterion[criterion["criterion_id"]] = evidence

            # Check scores before passing to scoring function
            for ev in evidence:
                for score_key in ["reranker_score", "score"]:
                    score = ev.get(score_key)
                    if score is not None:
                        if not (-1.0 <= score <= 1.0):
                            invalid_scores.append(
                                (
                                    criterion["criterion_id"],
                                    score_key,
                                    score,
                                    ev.get("source_id", "unknown"),
                                )
                            )

    if invalid_scores:
        print("\n[Test] Invalid scores found before scoring:")
        for criterion_id, score_key, score_value, source_id in invalid_scores:
            print(f"  {criterion_id}: {score_key}={score_value:.6f} from {source_id}")

    # Apply scoring (this should handle invalid scores gracefully)
    scores = apply_rubric_scoring_dynamic(
        rubric, student_answer, evidence_by_criterion, debug=True
    )

    # Check that no negative final scores were produced
    negative_scores = [
        (cid, info["score"]) for cid, info in scores.items() if info["score"] < 0
    ]

    if negative_scores:
        print("\n[Test] Negative final scores produced:")
        for criterion_id, score_value in negative_scores:
            print(f"  {criterion_id}: {score_value}")

    # Assertions
    # Cosine similarity scores should be in [-1, 1]
    assert (
        len(cosine_out_of_range) == 0
    ), f"Found {len(cosine_out_of_range)} cosine similarity scores outside [-1, 1]"

    # Cross-encoder scores can be outside [-1, 1], but scoring function should normalize them
    # So we should NOT get negative final scores even if rerank scores are negative
    assert (
        len(negative_scores) == 0
    ), f"Scoring produced {len(negative_scores)} negative final scores. Cross-encoder scores should be normalized."

    print("✓ test_similarity_scores_in_pipeline passed")


if __name__ == "__main__":
    test_similarity_scores_in_valid_range()
    test_similarity_scores_from_retriever_interface()
    test_similarity_scores_in_pipeline()
    print("\n✓ All similarity score validation tests passed")
