"""Grading-specific evidence retrieval wrapper.

This module provides a high-level interface for retrieving evidence
during the grading process, integrating with rubrics and citations.

"""

from typing import Any

from evidence.retriever import EvidenceRetriever
from grader.cite import format_citation, generate_citation


class GradingEvidenceRetriever:
    """Evidence retriever specialized for grading workflow."""

    def __init__(self, retriever: EvidenceRetriever) -> None:
        """Initialize the grading evidence retriever.

        Args:
            retriever: Base EvidenceRetriever instance.

        """
        self.retriever = retriever

    def retrieve_for_rubric(
        self,
        rubric: dict[str, Any],
        student_answer: str,
        top_k_per_criterion: int = 3,
    ) -> dict[str, list[dict[str, Any]]]:
        """Retrieve evidence for all criteria in a rubric.

        Args:
            rubric: Rubric dictionary containing criteria list.
            student_answer: Student's answer text.
            top_k_per_criterion: Number of evidence items per criterion.

        Returns:
            Dictionary mapping criterion_id to list of evidence citations.

        """
        evidence_by_criterion = {}

        for criterion in rubric.get("criteria", []):
            # Only retrieve if evidence is required
            if criterion.get("evidence_required", False):
                evidence = self.retriever.retrieve_for_criterion(
                    criterion, student_answer, top_k=top_k_per_criterion
                )
                evidence_by_criterion[criterion["criterion_id"]] = evidence

        return evidence_by_criterion

    def create_citations(
        self, evidence_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Create formatted citations from evidence list.

        Args:
            evidence_list: List of evidence dictionaries.

        Returns:
            List of citation dictionaries.

        """
        citations = []
        for evidence in evidence_list:
            citation = generate_citation(
                evidence_text=evidence["text"],
                source=evidence["source_id"],
                location=evidence.get("page_number"),
            )
            citations.append(citation)

        return citations

    def format_evidence_with_citations(
        self, evidence_list: list[dict[str, Any]]
    ) -> str:
        """Format evidence with citation markers for grading.

        Args:
            evidence_list: List of evidence dictionaries.

        Returns:
            Formatted string with citations.

        """
        if not evidence_list:
            return "No evidence available."

        lines = []
        for i, evidence in enumerate(evidence_list, 1):
            citation = generate_citation(
                evidence_text=evidence["text"],
                source=evidence["source_id"],
                location=evidence.get("page_number"),
            )
            formatted_citation = format_citation(citation)

            lines.append(f"[Evidence {i}] {formatted_citation}")
            lines.append(f"  {evidence['text']}")
            lines.append("")

        return "\n".join(lines)

    def get_evidence_ids(
        self, evidence_list: list[dict[str, Any]]
    ) -> list[str]:
        """Extract evidence IDs for validation.

        Args:
            evidence_list: List of evidence dictionaries.

        Returns:
            List of evidence source IDs.

        """
        return [evidence["source_id"] for evidence in evidence_list]


if __name__ == "__main__":
    # Test grading evidence retriever
    from config.llm_config import setup_llamaindex_defaults
    from evidence.index_builder import (
        build_index_with_metadata,
        create_documents_with_metadata,
    )

    print("Testing GradingEvidenceRetriever...")

    # Configure LlamaIndex
    setup_llamaindex_defaults()

    # Create sample evidence
    texts = [
        "Mutual information I(X;Y) measures the reduction in uncertainty about X when Y is observed.",
        "The mutual information is symmetric: I(X;Y) = I(Y;X).",
        "Mutual information can detect nonlinear dependencies unlike correlation.",
        "Entropy H(X) is defined as the expected value of -log p(X).",
        "Conditional entropy H(X|Y) measures remaining uncertainty about X after observing Y.",
    ]

    sources = [
        {"source_id": "slide_12", "source_type": "slide", "page_number": 12},
        {"source_id": "slide_13", "source_type": "slide", "page_number": 13},
        {"source_id": "slide_14", "source_type": "slide", "page_number": 14},
        {"source_id": "slide_20", "source_type": "slide", "page_number": 20},
        {"source_id": "slide_21", "source_type": "slide", "page_number": 21},
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)
    print("✓ Grading retriever created")

    # Test rubric-based retrieval
    print("\n[Test 1] Retrieve evidence for rubric:")
    rubric = {
        "criteria": [
            {
                "criterion_id": "c1",
                "description": "Correctly defines mutual information",
                "evidence_required": True,
            },
            {
                "criterion_id": "c2",
                "description": "Explains relationship to entropy",
                "evidence_required": True,
            },
        ]
    }

    student_answer = "Mutual information measures how much information one variable provides about another. It is related to entropy."

    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        rubric, student_answer, top_k_per_criterion=2
    )

    for criterion_id, evidence in evidence_by_criterion.items():
        print(f"\n  Criterion: {criterion_id}")
        print(f"  Evidence items: {len(evidence)}")
        for i, e in enumerate(evidence, 1):
            print(f"    {i}. {e['source_id']} (score: {e['score']:.3f})")

    # Test citation creation
    print("\n[Test 2] Create citations:")
    evidence_list = evidence_by_criterion["c1"]
    citations = grading_retriever.create_citations(evidence_list)
    print(f"Created {len(citations)} citations")
    for citation in citations:
        print(f"  {format_citation(citation)}")

    # Test formatted output
    print("\n[Test 3] Formatted evidence with citations:")
    formatted = grading_retriever.format_evidence_with_citations(evidence_list)
    print(formatted)

    # Test evidence ID extraction
    print("\n[Test 4] Extract evidence IDs:")
    evidence_ids = grading_retriever.get_evidence_ids(evidence_list)
    print(f"Evidence IDs: {evidence_ids}")
