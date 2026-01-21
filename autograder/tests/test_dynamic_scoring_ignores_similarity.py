"""Tests that dynamic grading scoring ignores similarity/reranker numeric scores.

Per intended design: retrieval+reranking selects spans; numeric scores should not
influence rubric scoring. This test ensures scoring is invariant to evidence score
fields.

"""

from grading_dynamic_rubrics.pipeline import apply_rubric_scoring_dynamic


def test_dynamic_scoring_invariant_to_evidence_scores() -> None:
    """Changing evidence numeric scores should not change rubric scores.

    This verifies we do not accidentally use `score` or `reranker_score` for grading.

    """
    rubric = {
        "question_id": "qXX",
        "total_points": 10,
        "semantic_top_k": 3,
        "semantic_decay": "linear",
        "scoring_weights": {
            "c1": {"keyword": 0.5, "semantic": 0.5},
        },
        "criteria": [
            {"criterion_id": "c1", "description": "object attribute record field", "points": 10},
        ],
    }

    student_answer = "An object is a record; an attribute is a field."

    # Same number of spans, but wildly different numeric scores.
    evidence_a = {
        "c1": [
            {"source_id": "s1", "text": "t1", "score": 0.9, "reranker_score": -7.8},
            {"source_id": "s2", "text": "t2", "score": -0.5, "reranker_score": 12.3},
            {"source_id": "s3", "text": "t3", "score": 1.0, "reranker_score": 0.0},
        ]
    }
    evidence_b = {
        "c1": [
            {"source_id": "s1", "text": "t1", "score": -1.0, "reranker_score": -100.0},
            {"source_id": "s2", "text": "t2", "score": 0.0, "reranker_score": 100.0},
            {"source_id": "s3", "text": "t3", "score": 0.2, "reranker_score": -0.1},
        ]
    }

    scores_a = apply_rubric_scoring_dynamic(rubric, student_answer, evidence_a)
    scores_b = apply_rubric_scoring_dynamic(rubric, student_answer, evidence_b)

    assert scores_a["c1"]["keyword_score"] == scores_b["c1"]["keyword_score"]
    assert scores_a["c1"]["semantic_score"] == scores_b["c1"]["semantic_score"]
    assert scores_a["c1"]["combined_score"] == scores_b["c1"]["combined_score"]
    assert scores_a["c1"]["score"] == scores_b["c1"]["score"]

    print("✓ test_dynamic_scoring_invariant_to_evidence_scores passed")


if __name__ == "__main__":
    test_dynamic_scoring_invariant_to_evidence_scores()
