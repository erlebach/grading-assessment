"""Tests for MWE 2: Evidence Retrieval with Citations."""

import pytest

from config.llm_config import setup_llamaindex_defaults
from evidence.index_builder import (
    build_index_with_metadata,
    create_documents_with_metadata,
    extract_citation_from_node,
)
from evidence.retriever import EvidenceRetriever
from grader.evidence_retriever import GradingEvidenceRetriever


def test_create_documents_with_metadata() -> None:
    """Test creating documents with citation metadata."""
    texts = ["Text 1", "Text 2"]
    sources = [
        {"source_id": "src_1", "source_type": "slide", "page_number": 10},
        {"source_id": "src_2", "source_type": "textbook", "page_number": 45},
    ]

    documents = create_documents_with_metadata(texts, sources)

    assert len(documents) == 2
    assert documents[0].text == "Text 1"
    assert documents[0].metadata["source_id"] == "src_1"
    assert documents[0].metadata["page_number"] == 10
    assert documents[1].metadata["source_type"] == "textbook"


def test_metadata_mismatch_raises_error() -> None:
    """Test that mismatched texts and sources raises error."""
    texts = ["Text 1", "Text 2"]
    sources = [{"source_id": "src_1"}]  # Only one source

    with pytest.raises(ValueError):
        create_documents_with_metadata(texts, sources)


def test_index_with_metadata() -> None:
    """Test building index preserves metadata."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = ["Sample text about mutual information"]
    sources = [{"source_id": "slide_12", "source_type": "slide"}]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    assert index is not None

    # Retrieve and check metadata is preserved
    retriever = index.as_retriever(similarity_top_k=1)
    nodes = retriever.retrieve("mutual information")

    assert len(nodes) > 0
    assert "source_id" in nodes[0].node.metadata
    assert nodes[0].node.metadata["source_id"] == "slide_12"


def test_citation_extraction() -> None:
    """Test extracting citation from node."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = ["Information theory concepts"]
    sources = [
        {
            "source_id": "slide_20",
            "source_type": "slide",
            "page_number": 20,
            "file_path": "lectures/lecture.pdf",
        }
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    retriever = index.as_retriever(similarity_top_k=1)
    nodes = retriever.retrieve("information")

    citation = extract_citation_from_node(nodes[0])

    assert citation["source_id"] == "slide_20"
    assert citation["source_type"] == "slide"
    assert citation["page_number"] == 20
    assert citation["file_path"] == "lectures/lecture.pdf"
    assert "text" in citation
    assert "score" in citation


def test_evidence_retriever_basic() -> None:
    """Test basic evidence retrieval."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = ["Mutual information measures dependence", "Entropy measures uncertainty"]
    sources = [
        {"source_id": "slide_1", "source_type": "slide"},
        {"source_id": "slide_2", "source_type": "slide"},
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    retriever = EvidenceRetriever(index)
    results = retriever.retrieve("mutual information", top_k=1)

    assert len(results) > 0
    assert results[0]["source_id"] in ["slide_1", "slide_2"]


def test_evidence_retriever_threshold() -> None:
    """Test similarity threshold filtering."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = ["Information theory", "Data quality"]
    sources = [
        {"source_id": "slide_1", "source_type": "slide"},
        {"source_id": "slide_2", "source_type": "slide"},
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    retriever = EvidenceRetriever(index)

    # High threshold should filter out low-scoring results
    results_low_threshold = retriever.retrieve(
        "information", top_k=10, similarity_threshold=0.0
    )
    results_high_threshold = retriever.retrieve(
        "information", top_k=10, similarity_threshold=0.5
    )

    assert len(results_high_threshold) <= len(results_low_threshold)


def test_grading_retriever_rubric_integration() -> None:
    """Test retrieval for rubric criteria."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = [
        "Mutual information measures statistical dependence",
        "Entropy is the expected value of information",
        "Data quality includes accuracy",
    ]
    sources = [
        {"source_id": "slide_10", "source_type": "slide"},
        {"source_id": "slide_11", "source_type": "slide"},
        {"source_id": "slide_12", "source_type": "slide"},
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)

    rubric = {
        "criteria": [
            {
                "criterion_id": "c1",
                "description": "Defines mutual information",
                "evidence_required": True,
            },
            {
                "criterion_id": "c2",
                "description": "Explains data quality",
                "evidence_required": True,
            },
            {
                "criterion_id": "c3",
                "description": "No evidence needed",
                "evidence_required": False,
            },
        ]
    }

    student_answer = "Mutual information and data quality are important concepts."

    evidence_by_criterion = grading_retriever.retrieve_for_rubric(
        rubric, student_answer, top_k_per_criterion=2
    )

    # Should retrieve for c1 and c2, but not c3
    assert "c1" in evidence_by_criterion
    assert "c2" in evidence_by_criterion
    assert "c3" not in evidence_by_criterion

    # Check evidence was retrieved
    assert len(evidence_by_criterion["c1"]) > 0
    assert len(evidence_by_criterion["c2"]) > 0


def test_citation_creation() -> None:
    """Test creating citations from evidence."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = ["Sample evidence text"]
    sources = [{"source_id": "slide_5", "source_type": "slide", "page_number": 5}]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)

    evidence = base_retriever.retrieve("sample", top_k=1)
    citations = grading_retriever.create_citations(evidence)

    assert len(citations) == len(evidence)
    assert citations[0]["source"] == "slide_5"
    assert citations[0]["location"] == 5


def test_evidence_id_extraction() -> None:
    """Test extracting evidence IDs for validation."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    evidence_list = [
        {"source_id": "slide_1", "text": "Text 1"},
        {"source_id": "slide_2", "text": "Text 2"},
        {"source_id": "slide_3", "text": "Text 3"},
    ]

    texts = [e["text"] for e in evidence_list]
    sources = [
        {"source_id": e["source_id"], "source_type": "slide"} for e in evidence_list
    ]

    documents = create_documents_with_metadata(texts, sources)
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)

    base_retriever = EvidenceRetriever(index)
    grading_retriever = GradingEvidenceRetriever(base_retriever)

    evidence = base_retriever.retrieve("text", top_k=3)
    evidence_ids = grading_retriever.get_evidence_ids(evidence)

    assert len(evidence_ids) > 0
    assert all(eid.startswith("slide_") for eid in evidence_ids)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
