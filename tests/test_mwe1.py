"""Tests for MWE 1: Basic LlamaIndex RAG Setup."""

import pytest

from config.llm_config import (
    configure_embedding,
    configure_llm,
    load_env_config,
    setup_llamaindex_defaults,
)
from evidence.llamaindex_setup import (
    create_in_memory_index,
    load_documents_from_texts,
    query_index,
)


def test_env_config_loads() -> None:
    """Test that environment configuration loads correctly."""
    config = load_env_config()

    assert "openai_api_key" in config
    assert "embedding_provider" in config
    assert "embedding_model" in config
    assert "lmql_backend" in config


def test_llm_configuration() -> None:
    """Test LLM configuration for different providers."""
    # Test OpenAI configuration
    llm = configure_llm("openai")
    assert llm is not None
    assert llm.model == "gpt-4o-mini"

    # Test with custom model
    llm_custom = configure_llm("openai", model="gpt-4")
    assert llm_custom.model == "gpt-4"


def test_embedding_configuration() -> None:
    """Test embedding model configuration."""
    # Test default SentenceTransformer configuration
    embed_model = configure_embedding("sentence-transformer")
    assert embed_model is not None

    # Test that model name is set correctly
    assert hasattr(embed_model, "model_name")
    assert (
        "sentence-transformers" in embed_model.model_name
        or "BAAI" in embed_model.model_name
    )


def test_document_creation() -> None:
    """Test creating documents from text strings."""
    texts = ["Sample text 1", "Sample text 2", "Sample text 3"]
    documents = load_documents_from_texts(texts)

    assert len(documents) == len(texts)
    for doc, text in zip(documents, texts):
        assert doc.text == text


def test_index_creation() -> None:
    """Test creating an in-memory vector index."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = [
        "Mutual information measures statistical dependence.",
        "Entropy measures uncertainty in a random variable.",
        "Data quality includes accuracy and completeness.",
    ]

    documents = load_documents_from_texts(texts)
    index = create_in_memory_index(documents, chunk_size=200, chunk_overlap=20)

    assert index is not None


def test_query_retrieval() -> None:
    """Test querying the index and retrieving results."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = [
        "Mutual information I(X;Y) measures the reduction in uncertainty.",
        "The mutual information is always non-negative and symmetric.",
        "Entropy H(X) measures the average information content.",
    ]

    documents = load_documents_from_texts(texts)
    index = create_in_memory_index(documents, chunk_size=200, chunk_overlap=20)

    # Query about mutual information
    results = query_index(index, "What is mutual information?", top_k=2)

    assert len(results) <= 2
    assert all("text" in result for result in results)
    assert all("score" in result for result in results)
    assert all("metadata" in result for result in results)

    # Check that scores are reasonable (should be positive)
    assert all(result["score"] > 0 for result in results)


def test_retrieval_relevance() -> None:
    """Test that retrieval returns relevant results."""
    # Configure LlamaIndex with SentenceTransformer embeddings
    setup_llamaindex_defaults()

    texts = [
        "Mutual information measures statistical dependence between variables.",
        "Entropy is a measure of uncertainty in probability theory.",
        "Python is a programming language used for data science.",
    ]

    documents = load_documents_from_texts(texts)
    index = create_in_memory_index(documents, chunk_size=200, chunk_overlap=20)

    # Query about information theory
    results = query_index(index, "information theory entropy", top_k=2)

    # The top result should be about entropy (index 1) or mutual information (index 0)
    # Both are more relevant than Python (index 2)
    top_result_text = results[0]["text"].lower()
    assert (
        "entropy" in top_result_text
        or "mutual information" in top_result_text
        or "uncertainty" in top_result_text
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
