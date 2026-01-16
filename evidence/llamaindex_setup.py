"""LlamaIndex setup and initialization for evidence retrieval.

This module provides functions to set up LlamaIndex with an in-memory
vector store for RAG-based evidence retrieval.

"""

from pathlib import Path
from typing import Any

from llama_index.core import (
    Document,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import SimpleVectorStore


def create_in_memory_index(
    documents: list[Document], chunk_size: int = 512, chunk_overlap: int = 50
) -> VectorStoreIndex:
    """Create an in-memory vector store index from documents.

    Args:
        documents: List of LlamaIndex Document objects to index.
        chunk_size: Size of text chunks in characters.
        chunk_overlap: Overlap between chunks in characters.

    Returns:
        VectorStoreIndex instance with indexed documents.

    """
    # Create in-memory vector store
    vector_store = SimpleVectorStore()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Configure node parser for chunking
    node_parser = SentenceSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    # Create index with custom node parser
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[node_parser],
        show_progress=True,
    )

    return index


def load_documents_from_directory(directory: Path) -> list[Document]:
    """Load documents from a directory.

    Args:
        directory: Path to directory containing documents.

    Returns:
        List of Document objects.

    """
    reader = SimpleDirectoryReader(
        input_dir=str(directory), recursive=True, required_exts=[".txt", ".md", ".py"]
    )
    documents = reader.load_data()
    return documents


def load_documents_from_texts(texts: list[str]) -> list[Document]:
    """Create Document objects from a list of text strings.

    Args:
        texts: List of text strings to convert to Documents.

    Returns:
        List of Document objects.

    """
    documents = [Document(text=text) for text in texts]
    return documents


def query_index(
    index: VectorStoreIndex, query: str, top_k: int = 5
) -> list[dict[str, Any]]:
    """Query the index and return retrieved chunks with metadata.

    Args:
        index: VectorStoreIndex to query.
        query: Query string.
        top_k: Number of results to retrieve.

    Returns:
        List of dictionaries containing text, score, and metadata.

    """
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)

    results = []
    for node in nodes:
        results.append(
            {
                "text": node.node.text,
                "score": node.score,
                "metadata": node.node.metadata,
                "node_id": node.node.node_id,
            }
        )

    return results


if __name__ == "__main__":
    # Test basic functionality
    from config.llm_config import setup_llamaindex_defaults

    print("Testing LlamaIndex setup...")

    # Configure LlamaIndex
    setup_llamaindex_defaults()
    print("✓ LlamaIndex configured")

    # Create sample documents
    sample_texts = [
        "Mutual information measures the reduction in uncertainty of one variable given another.",
        "The mutual information is always non-negative and symmetric.",
        "Mutual information captures both linear and nonlinear dependencies between variables.",
        "The entropy of a random variable measures the average information content.",
    ]

    print(f"\nCreating index from {len(sample_texts)} sample documents...")
    documents = load_documents_from_texts(sample_texts)
    index = create_in_memory_index(documents, chunk_size=200, chunk_overlap=20)
    print("✓ Index created")

    # Test retrieval
    query = "What does mutual information measure?"
    print(f"\nQuerying: '{query}'")
    results = query_index(index, query, top_k=2)

    for i, result in enumerate(results, 1):
        print(f"\n Result {i}:")
        print(f"  Score: {result['score']:.4f}")
        print(f"  Text: {result['text'][:100]}...")
