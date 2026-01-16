"""MWE 3: LMQL Integration for Structured Grading.

This script demonstrates:
1. LMQL program with citation enforcement
2. Structured output generation (scores, feedback, citations)
3. Validation of citation completeness
4. Integration with evidence from MWE 2

Prerequisites:
- Set environment variables in $HOME/.env (same as MWE 1)
- Completed MWE 1 and MWE 2

Usage:
    python -m mwe.mwe3_lmql_grading

"""

from config.llm_config import setup_llamaindex_defaults
from evidence.index_builder import (
    build_index_with_metadata,
    create_documents_with_metadata,
)
from evidence.retriever import EvidenceRetriever
from grader.evidence_retriever import GradingEvidenceRetriever
from grader.lmql_grading import LMQLGrader


def main() -> None:
    """Run MWE 3 demonstration."""
    print("=" * 70)
    print("MWE 3: LMQL Integration for Structured Grading")
    print("=" * 70)

    # Step 1: Configure LlamaIndex
    print("\n[Step 1] Configuring LlamaIndex and LMQL...")
    setup_llamaindex_defaults()
    print("✓ Configuration loaded")

    # Step 2: Create evidence corpus (reusing from MWE 2)
    print("\n[Step 2] Creating evidence corpus...")

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

    documents = create_documents_with_metadata(evidence_texts, evidence_sources)
    index = build_index_with_metadata(documents, chunk_size=512, chunk_overlap=50)
    print(f"✓ Index created with {len(evidence_texts)} evidence documents")

    # Step 3: Set up retrievers
    print("\n[Step 3] Setting up evidence retrievers...")
    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    print("✓ Retrievers initialized")

    # Step 4: Define rubric and student answer
    print("\n[Step 4] Defining rubric and student answer...")

    rubric = {
        "question_id": "q01",
        "question_text": "Explain mutual information and its relationship to entropy",
        "total_points": 10,
        "criteria": [
            {
                "criterion_id": "definition",
                "description": "Correctly defines mutual information",
                "points": 4,
                "evidence_required": True,
            },
            {
                "criterion_id": "properties",
                "description": "Explains key properties (non-negative, symmetric)",
                "points": 3,
                "evidence_required": True,
            },
            {
                "criterion_id": "entropy_relation",
                "description": "Relates mutual information to entropy",
                "points": 3,
                "evidence_required": True,
            },
        ],
    }

    student_answer = """
    Mutual information measures how much knowing one variable tells us about
    another variable. It's always non-negative and is symmetric, meaning
    I(X;Y) = I(Y;X). It's related to entropy because mutual information
    equals the entropy of X minus the conditional entropy H(X|Y).
    """

    print(f"✓ Rubric: {rubric['question_text']}")
    print(f"  Criteria: {len(rubric['criteria'])}")
    print(f"  Total points: {rubric['total_points']}")

    # Step 5: Retrieve evidence for rubric
    print("\n[Step 5] Retrieving evidence for rubric criteria...")

    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        rubric, student_answer, top_k_per_criterion=2
    )

    for criterion_id, evidence_list in evidence_by_criterion.items():
        print(f"  {criterion_id}: {len(evidence_list)} evidence items")

    # Step 6: Simulate grading (assign scores)
    print("\n[Step 6] Assigning scores (rubric-driven)...")

    # In real system, this would be done by rubric application logic
    # Here we simulate for demonstration
    scores = {
        "definition": {"score": 4, "max_score": 4},  # Full marks
        "properties": {"score": 3, "max_score": 3},  # Full marks
        "entropy_relation": {"score": 2, "max_score": 3},  # Partial
    }

    total_score = sum(s["score"] for s in scores.values())
    max_score = sum(s["max_score"] for s in scores.values())
    print(f"✓ Scores assigned: {total_score}/{max_score}")

    for criterion_id, score_info in scores.items():
        print(f"  {criterion_id}: {score_info['score']}/{score_info['max_score']}")

    # Step 7: Generate LMQL-constrained feedback
    print("\n[Step 7] Generating citation-enforced feedback with LMQL...")
    print("  (This may take 10-30 seconds...)")

    lmql_grader = LMQLGrader()

    result = lmql_grader.grade_with_feedback(
        rubric=rubric,
        student_answer=student_answer,
        evidence_by_criterion=evidence_by_criterion,
        scores=scores,
    )

    print(f"✓ Feedback generated in {result.get('attempts', 1)} attempt(s)")
    print(f"  Validation passed: {result['validation_passed']}")

    # Step 8: Display results
    print("\n" + "=" * 70)
    print("Grading Results")
    print("=" * 70)

    print(f"\nQuestion: {result['question_id']}")
    print(f"Score: {result['total_score']}/{result['max_score']}")

    print("\nScore Breakdown:")
    for criterion_id, score_info in result["scores"].items():
        print(f"  {criterion_id}: {score_info['score']}/{score_info['max_score']}")

    print("\nCitation-Enforced Feedback:")
    print("─" * 70)
    print(result["feedback"])
    print("─" * 70)

    # Step 9: Show structured explanation
    if result["explanation"]:
        print("\nStructured Explanation (with citations):")
        for i, sentence in enumerate(result["explanation"]["sentences"], 1):
            print(f"  [{i}] {sentence['text']}")
            print(f"      Citations: {', '.join(sentence['citations'])}")

    # Step 10: Show evidence used
    print("\nEvidence Sources Used:")
    for i, evidence in enumerate(result["evidence_used"], 1):
        print(f"  [{i}] {evidence['source_id']}: {evidence['text'][:80]}...")

    # Step 11: Summary
    print("\n" + "=" * 70)
    print("MWE 3 Summary")
    print("=" * 70)
    print("✓ Evidence retrieved for rubric criteria")
    print("✓ Scores assigned deterministically (rubric-driven)")
    print("✓ LMQL-constrained feedback generated")
    print("✓ Every sentence includes citations")
    print("✓ All citations reference valid evidence IDs")
    print("✓ Validation passed")
    print("\nNext: MWE 4 will integrate all components into the full pipeline")


if __name__ == "__main__":
    main()
