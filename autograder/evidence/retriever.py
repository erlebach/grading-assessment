"""Evidence retrieval interface for grading.

This module provides a clean interface for retrieving evidence with
citations from a LlamaIndex vector store.

"""

from typing import Any

from llama_index.core import VectorStoreIndex

from evidence.index_builder import extract_citation_from_node


class EvidenceRetriever:
    """Retriever for evidence with citation support."""

    def __init__(self, index: VectorStoreIndex) -> None:
        """Initialize the evidence retriever.

        Args:
            index: VectorStoreIndex to retrieve from.

        """
        self.index = index

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Retrieve evidence chunks with citations.

        Args:
            query: Query string.
            top_k: Maximum number of results to retrieve.
            similarity_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of dictionaries containing evidence with citation metadata.

        """
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)

        # Extract citations and filter by threshold
        results = []
        for node in nodes:
            citation = extract_citation_from_node(node)
            if citation["score"] >= similarity_threshold:
                results.append(citation)

        return results

    def retrieve_for_criterion(
        self,
        criterion: dict[str, Any],
        student_answer: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve evidence relevant to a specific rubric criterion.

        Args:
            criterion: Rubric criterion dictionary containing:
                - criterion_id: Unique identifier
                - description: Criterion description
            student_answer: Student's answer text.
            top_k: Maximum number of results to retrieve.

        Returns:
            List of evidence citations relevant to the criterion.

        """
        # Construct query from criterion and student answer
        query = f"{criterion['description']} {student_answer}"

        return self.retrieve(query, top_k=top_k)

    def format_evidence_for_grading(
        self, evidence_list: list[dict[str, Any]]
    ) -> str:
        """Format evidence citations for use in grading prompts.

        Args:
            evidence_list: List of evidence citations.

        Returns:
            Formatted string with numbered evidence items.

        """
        if not evidence_list:
            return "No evidence retrieved."

        lines = []
        for i, evidence in enumerate(evidence_list, 1):
            source_id = evidence["source_id"]
            text = evidence["text"]
            score = evidence["score"]

            lines.append(
                f"[{i}] Source: {source_id} (relevance: {score:.3f})\n{text}\n"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    # Test retriever
    from config.llm_config import setup_llamaindex_defaults
    from evidence.index_builder import (
        build_index_with_metadata,
        create_documents_with_metadata,
    )

    print("Testing EvidenceRetriever...")

    # Configure LlamaIndex
    setup_llamaindex_defaults()

    # Create sample evidence
    texts = [
        "Mutual information I(X;Y) measures the reduction in uncertainty "
        "about X when we observe Y.",
        "The mutual information is always non-negative and symmetric.",
        "Mutual information captures both linear and nonlinear dependencies.",
        "Entropy H(X) measures the average information content.",
        "Data quality includes accuracy, completeness, and consistency.",
    ]

    sources = [
        {"source_id": "slide_12", "source_type": "slide"},
        {"source_id": "slide_13", "source_type": "slide"},
        {"source_id": "slide_14", "source_type": "slide"},
        {"source_id": "slide_20", "source_type": "slide"},
        {"source_id": "textbook_ch3", "source_type": "textbook"},
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    # Create retriever
    retriever = EvidenceRetriever(index)
    print("✓ Retriever created")

    # Test basic retrieval
    print("\n[Test 1] Basic retrieval:")
    results = retriever.retrieve("What is mutual information?", top_k=3)
    print(f"Retrieved {len(results)} results")
    for i, result in enumerate(results, 1):
        print(
            f"  {i}. {result['source_id']} (score: {result['score']:.3f})"
        )

    # Test criterion-based retrieval
    print("\n[Test 2] Criterion-based retrieval:")
    criterion = {
        "criterion_id": "c1",
        "description": "Correctly defines mutual information",
    }
    student_answer = "Mutual information tells us how much knowing Y reduces uncertainty about X."

    results = retriever.retrieve_for_criterion(
        criterion, student_answer, top_k=2
    )
    print(f"Retrieved {len(results)} results for criterion")

    # Test formatting
    print("\n[Test 3] Formatted evidence:")
    formatted = retriever.format_evidence_for_grading(results)
    print(formatted)
