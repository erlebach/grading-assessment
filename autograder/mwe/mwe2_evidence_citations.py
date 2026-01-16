"""MWE 2: Evidence Retrieval with Citations.

This script demonstrates:
1. Building an index with source metadata
2. Retrieving evidence for rubric criteria
3. Generating properly formatted citations
4. Integration with the grading workflow

Prerequisites:
- Set environment variables in $HOME/.env (same as MWE 1)
- Completed MWE 1

Usage:
    python -m mwe.mwe2_evidence_citations

"""

from config.llm_config import setup_llamaindex_defaults
from evidence.index_builder import (
    build_index_with_metadata,
    create_documents_with_metadata,
)
from evidence.retriever import EvidenceRetriever
from grader.cite import format_citation
from grader.evidence_retriever import GradingEvidenceRetriever


def main() -> None:
    """Run MWE 2 demonstration."""
    print("=" * 70)
    print("MWE 2: Evidence Retrieval with Citations")
    print("=" * 70)

    # Step 1: Configure LlamaIndex
    print("\n[Step 1] Configuring LlamaIndex...")
    setup_llamaindex_defaults()
    print("✓ Configuration loaded")

    # Step 2: Create evidence corpus with metadata
    print("\n[Step 2] Creating evidence corpus with citation metadata...")

    evidence_texts = [
        # Mutual information - slides 12-14
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
        # Entropy - slides 20-22
        "The entropy H(X) of a random variable measures the average "
        "information content or uncertainty. For a discrete random variable "
        "with probability mass function p(x), entropy is defined as "
        "H(X) = -sum_x p(x) log p(x).",
        "Conditional entropy H(X|Y) measures the average uncertainty "
        "remaining about X after observing Y. It is related to mutual "
        "information by the formula: I(X;Y) = H(X) - H(X|Y).",
        "The joint entropy H(X,Y) measures the uncertainty about the pair "
        "(X,Y). It satisfies H(X,Y) = H(X) + H(Y|X) = H(Y) + H(X|Y).",
        # Data quality - textbook chapter 3
        "Data quality dimensions include accuracy, completeness, consistency, "
        "timeliness, and validity. Accuracy measures how well data represents "
        "the real-world entity or event it describes.",
        "Data completeness refers to the extent to which all required data "
        "is present. Missing data can arise from various sources including "
        "sensor failures, human error, or system limitations.",
    ]

    # Metadata with source IDs for citations
    evidence_sources = [
        {
            "source_id": "slide_12",
            "source_type": "slide",
            "file_path": "lectures/lecture_03_information_theory.pdf",
            "page_number": 12,
        },
        {
            "source_id": "slide_13",
            "source_type": "slide",
            "file_path": "lectures/lecture_03_information_theory.pdf",
            "page_number": 13,
        },
        {
            "source_id": "slide_14",
            "source_type": "slide",
            "file_path": "lectures/lecture_03_information_theory.pdf",
            "page_number": 14,
        },
        {
            "source_id": "slide_20",
            "source_type": "slide",
            "file_path": "lectures/lecture_03_information_theory.pdf",
            "page_number": 20,
        },
        {
            "source_id": "slide_21",
            "source_type": "slide",
            "file_path": "lectures/lecture_03_information_theory.pdf",
            "page_number": 21,
        },
        {
            "source_id": "slide_22",
            "source_type": "slide",
            "file_path": "lectures/lecture_03_information_theory.pdf",
            "page_number": 22,
        },
        {
            "source_id": "textbook_ch3_p45",
            "source_type": "textbook",
            "file_path": "textbook/data_quality.pdf",
            "page_number": 45,
        },
        {
            "source_id": "textbook_ch3_p46",
            "source_type": "textbook",
            "file_path": "textbook/data_quality.pdf",
            "page_number": 46,
        },
    ]

    print(f"✓ Created {len(evidence_texts)} evidence documents with metadata")

    # Step 3: Build index with metadata
    print("\n[Step 3] Building index with metadata preservation...")
    documents = create_documents_with_metadata(evidence_texts, evidence_sources)
    index = build_index_with_metadata(documents, chunk_size=512, chunk_overlap=50)
    print("✓ Index built with citation metadata")

    # Step 4: Create retrievers
    print("\n[Step 4] Creating evidence retrievers...")
    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    print("✓ Retrievers initialized")

    # Step 5: Demonstrate rubric-based retrieval
    print("\n[Step 5] Retrieving evidence for rubric criteria...")

    sample_rubric = {
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
    another variable. It's always positive and works both ways (symmetric).
    It's related to entropy because it shows how much the entropy of X
    decreases when we know Y.
    """

    print(f"\nRubric: {sample_rubric['question_text']}")
    print(f"Student answer: {student_answer.strip()[:100]}...")

    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        sample_rubric, student_answer, top_k_per_criterion=2
    )

    print(f"\n✓ Retrieved evidence for {len(evidence_by_criterion)} criteria")

    # Step 6: Display evidence with citations
    print("\n[Step 6] Evidence with citations:")
    print("=" * 70)

    for criterion in sample_rubric["criteria"]:
        criterion_id = criterion["criterion_id"]
        if criterion_id in evidence_by_criterion:
            evidence_list = evidence_by_criterion[criterion_id]

            print(f"\nCriterion: {criterion['description']}")
            print(f"Points: {criterion['points']}")
            print(f"Evidence items: {len(evidence_list)}")
            print("─" * 70)

            for i, evidence in enumerate(evidence_list, 1):
                print(f"\n  [{i}] Source: {evidence['source_id']}")
                print(f"      Relevance: {evidence['score']:.4f}")
                print(f"      File: {evidence.get('file_path', 'N/A')}")
                if "page_number" in evidence:
                    print(f"      Page: {evidence['page_number']}")
                print(f"      Text: {evidence['text'][:150]}...")

    # Step 7: Create formatted citations
    print("\n" + "=" * 70)
    print("[Step 7] Formatted citations for grading:")
    print("=" * 70)

    # Example: Format evidence for the first criterion
    first_criterion_id = sample_rubric["criteria"][0]["criterion_id"]
    if first_criterion_id in evidence_by_criterion:
        evidence_list = evidence_by_criterion[first_criterion_id]
        citations = grading_retriever.create_citations(evidence_list)

        print(f"\nCriterion: {sample_rubric['criteria'][0]['description']}")
        print("\nCitations:")
        for i, citation in enumerate(citations, 1):
            formatted = format_citation(citation)
            print(f"  [{i}] {formatted}")

        # Show evidence IDs for validation
        evidence_ids = grading_retriever.get_evidence_ids(evidence_list)
        print(f"\nEvidence IDs for validation: {evidence_ids}")

    # Step 8: Summary
    print("\n" + "=" * 70)
    print("MWE 2 Summary")
    print("=" * 70)
    print("✓ Index built with source metadata")
    print("✓ Evidence retrieved for rubric criteria")
    print("✓ Citations generated with source IDs")
    print("✓ Evidence IDs available for validation")
    print("\nNext: MWE 3 will add LMQL constraints for citation enforcement")


if __name__ == "__main__":
    main()
