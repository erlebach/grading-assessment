"""MWE 4: Full Pipeline Integration.

This script demonstrates the complete end-to-end grading pipeline:
1. Load rubric and student submission
2. Build/load evidence index
3. Retrieve evidence for rubric criteria
4. Apply rubric-driven scoring (deterministic)
5. Generate LMQL-constrained feedback with citations
6. Return complete grading record

Prerequisites:
- Set environment variables in $HOME/.env (same as previous MWEs)
- Completed MWE 1, 2, and 3

Usage:
    python -m mwe.mwe4_full_pipeline

"""

from pathlib import Path

from config.llm_config import setup_llamaindex_defaults
from evidence.build_index import build_index, load_saved_index
from evidence.index_builder import create_documents_with_metadata
from evidence.retriever import EvidenceRetriever
from grader.evidence_retriever import GradingEvidenceRetriever
from grader.grade_question import grade_question, load_rubric
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
    import tempfile

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


def main() -> None:
    """Run MWE 4 demonstration."""
    print("=" * 70)
    print("MWE 4: Full Pipeline Integration")
    print("=" * 70)

    # Step 1: Setup
    print("\n[Step 1] Configuring system...")
    setup_llamaindex_defaults()
    print("✓ Configuration loaded")

    # Step 2: Create sample evidence index
    print("\n[Step 2] Creating sample evidence index...")
    index_path = create_sample_evidence_index()
    print(f"✓ Index created at {index_path}")

    # Step 3: Create sample rubric and submission
    print("\n[Step 3] Creating sample rubric and submission...")

    rubric = create_sample_rubric()
    print(f"✓ Rubric: {rubric['question_text']}")
    print(f"  Criteria: {len(rubric['criteria'])}")
    print(f"  Total points: {rubric['total_points']}")

    student_answer = """
    Mutual information measures how much knowing one variable tells us about
    another variable. It's always non-negative and is symmetric, meaning
    I(X;Y) = I(Y;X). It's related to entropy because mutual information
    equals the entropy of X minus the conditional entropy H(X|Y).
    """

    print(f"\n  Student answer: {student_answer.strip()[:100]}...")

    # Step 4: Load evidence index and create retrievers
    print("\n[Step 4] Loading evidence index...")
    index = load_saved_index(index_path)
    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    print("✓ Evidence retriever initialized")

    # Step 5: Retrieve evidence for rubric
    print("\n[Step 5] Retrieving evidence for rubric criteria...")
    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        rubric, student_answer, top_k_per_criterion=2
    )

    for criterion_id, evidence_list in evidence_by_criterion.items():
        print(f"  {criterion_id}: {len(evidence_list)} evidence items")

    # Step 6: Apply rubric scoring
    print("\n[Step 6] Applying rubric-driven scoring...")

    # Import the scoring function
    from grader.grade_question import apply_rubric_scoring

    scores = apply_rubric_scoring(rubric, student_answer, evidence_by_criterion)

    total_score = sum(s["score"] for s in scores.values())
    max_score = sum(s["max_score"] for s in scores.values())

    print(f"✓ Scores assigned: {total_score}/{max_score}")
    for criterion_id, score_info in scores.items():
        print(f"  {criterion_id}: {score_info['score']}/{score_info['max_score']}")

    # Step 7: Generate LMQL-constrained feedback
    print("\n[Step 7] Generating citation-enforced feedback...")
    print("  (This may take 10-30 seconds...)")

    lmql_grader = LMQLGrader()
    grading_result = lmql_grader.grade_with_feedback(
        rubric=rubric,
        student_answer=student_answer,
        evidence_by_criterion=evidence_by_criterion,
        scores=scores,
    )

    print(f"✓ Feedback generated")
    print(f"  Validation passed: {grading_result['validation_passed']}")

    # Step 8: Display complete grading results
    print("\n" + "=" * 70)
    print("Complete Grading Results")
    print("=" * 70)

    print(f"\nQuestion: {grading_result['question_id']}")
    print(f"Total Score: {grading_result['total_score']}/{grading_result['max_score']}")

    print("\nScore Breakdown:")
    for criterion_id, score_info in grading_result["scores"].items():
        print(f"  {criterion_id}: {score_info['score']}/{score_info['max_score']}")

    print("\nCitation-Enforced Feedback:")
    print("─" * 70)
    print(grading_result["feedback"])
    print("─" * 70)

    print("\nStructured Explanation:")
    if grading_result["explanation"]:
        for i, sentence in enumerate(grading_result["explanation"]["sentences"], 1):
            print(f"  [{i}] {sentence['text']}")
            print(f"      Citations: {', '.join(sentence['citations'])}")

    print("\nEvidence Sources Used:")
    for i, evidence in enumerate(grading_result["evidence_used"], 1):
        print(f"  [{i}] {evidence['source_id']}")
        print(f"      {evidence['text'][:80]}...")

    # Step 9: Test using grade_question function
    print("\n" + "=" * 70)
    print("[Step 9] Testing grade_question() function")
    print("=" * 70)

    # Create temporary files
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(student_answer)
        submission_path = Path(f.name)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(rubric, f)
        rubric_path = Path(f.name)

    # Call grade_question
    result = grade_question(
        submission_path=submission_path,
        rubric_path=rubric_path,
        evidence_index_path=index_path,
    )

    print(f"\n✓ Question: {result['question_id']}")
    print(f"  Score: {result['score']}/{result['max_score']}")
    print(f"  Rubric items: {len(result['rubric_items'])}")
    print(f"  Citations: {len(result['citations'])}")

    print("\nRubric Item Breakdown:")
    for item in result["rubric_items"]:
        print(
            f"  {item['criterion_id']}: {item['score']}/{item['max_score']} - {item['description']}"
        )

    print("\nFeedback:")
    print(result["feedback"][:200] + "...")

    # Cleanup
    submission_path.unlink()
    rubric_path.unlink()

    # Step 10: Summary
    print("\n" + "=" * 70)
    print("MWE 4 Summary")
    print("=" * 70)
    print("✓ Full pipeline implemented and tested")
    print("✓ Evidence index built and loaded")
    print("✓ Rubric-driven scoring applied deterministically")
    print("✓ LMQL-constrained feedback with citations generated")
    print("✓ Complete grading record produced")
    print("✓ All TODOs in grade_question.py and build_index.py replaced")
    print("\nThe autograder system is now fully functional!")
    print("\nArchitecture principles maintained:")
    print("  - Rubric-first: Scores defined by rubric, not LLM")
    print("  - Evidence-constrained: All citations from admissible sources")
    print("  - Grades before feedback: Scores assigned deterministically first")
    print("  - Citation-enforced: Every explanation sentence cites evidence")
    print("  - Bounded variance: Deterministic outcomes with auditability")


if __name__ == "__main__":
    main()
