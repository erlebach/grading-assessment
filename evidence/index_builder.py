"""Enhanced index building with metadata for citations.

This module extends the basic LlamaIndex setup to include source metadata
(file paths, line numbers, document IDs) necessary for citation generation.

"""

from pathlib import Path
from typing import Any

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import SimpleVectorStore


def create_documents_with_metadata(
    texts: list[str], sources: list[dict[str, Any]]
) -> list[Document]:
    """Create Document objects with citation metadata.

    Args:
        texts: List of text strings.
        sources: List of metadata dictionaries, one per text. Each should contain:
            - source_id: Unique identifier for the source
            - source_type: Type of source (e.g., "slide", "textbook", "documentation")
            - file_path: Optional file path
            - page_number: Optional page number
            - line_start: Optional starting line number
            - line_end: Optional ending line number

    Returns:
        List of Document objects with metadata.

    """
    if len(texts) != len(sources):
        raise ValueError("Number of texts must match number of source metadata dicts")

    documents = []
    for text, source_meta in zip(texts, sources):
        # Create document with metadata
        doc = Document(text=text, metadata=source_meta)
        documents.append(doc)

    return documents


def load_documents_from_files_with_metadata(
    file_paths: list[Path],
) -> list[Document]:
    """Load documents from files and attach file metadata.

    Args:
        file_paths: List of file paths to load.

    Returns:
        List of Document objects with file metadata.

    """
    documents = []

    for file_path in file_paths:
        with open(file_path, "r") as f:
            content = f.read()

        # Create metadata for citation
        metadata = {
            "source_id": f"file_{file_path.stem}",
            "source_type": "file",
            "file_path": str(file_path),
            "file_name": file_path.name,
        }

        doc = Document(text=content, metadata=metadata)
        documents.append(doc)

    return documents


def build_index_with_metadata(
    documents: list[Document],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> VectorStoreIndex:
    """Build vector index preserving source metadata in chunks.

    Args:
        documents: List of Document objects with metadata.
        chunk_size: Size of text chunks in characters.
        chunk_overlap: Overlap between chunks in characters.

    Returns:
        VectorStoreIndex with metadata preserved in chunks.

    """
    # Create in-memory vector store
    vector_store = SimpleVectorStore()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Configure node parser (metadata will be inherited by chunks)
    node_parser = SentenceSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    # Create index with metadata preservation
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[node_parser],
        show_progress=True,
    )

    return index


def extract_citation_from_node(node: Any) -> dict[str, Any]:
    """Extract citation information from a retrieved node.

    Args:
        node: Retrieved node from LlamaIndex query.

    Returns:
        Dictionary containing citation information.

    """
    metadata = node.node.metadata

    citation = {
        "text": node.node.text,
        "score": node.score,
        "source_id": metadata.get("source_id", "unknown"),
        "source_type": metadata.get("source_type", "unknown"),
    }

    # Add optional metadata fields if present
    if "file_path" in metadata:
        citation["file_path"] = metadata["file_path"]
    if "file_name" in metadata:
        citation["file_name"] = metadata["file_name"]
    if "page_number" in metadata:
        citation["page_number"] = metadata["page_number"]
    if "line_start" in metadata:
        citation["line_start"] = metadata["line_start"]
    if "line_end" in metadata:
        citation["line_end"] = metadata["line_end"]

    return citation


if __name__ == "__main__":
    # Test metadata preservation
    from config.llm_config import setup_llamaindex_defaults

    print("Testing index building with metadata...")

    # Configure LlamaIndex
    setup_llamaindex_defaults()

    # Create sample documents with metadata
    texts = [
        "Mutual information measures the reduction in uncertainty.",
        "Entropy measures the average information content.",
        "Data quality includes accuracy and completeness.",
    ]

    sources = [
        {
            "source_id": "slide_12",
            "source_type": "slide",
            "file_path": "lectures/lecture_03.pdf",
            "page_number": 12,
        },
        {
            "source_id": "slide_14",
            "source_type": "slide",
            "file_path": "lectures/lecture_03.pdf",
            "page_number": 14,
        },
        {
            "source_id": "textbook_ch2",
            "source_type": "textbook",
            "file_path": "textbook/chapter_02.pdf",
            "page_number": 45,
        },
    ]

    print(f"\nCreating {len(texts)} documents with metadata...")
    documents = create_documents_with_metadata(texts, sources)

    for i, doc in enumerate(documents):
        print(f"  Document {i+1}: {doc.metadata['source_id']}")

    print("\nBuilding index...")
    index = build_index_with_metadata(documents, chunk_size=200, chunk_overlap=20)
    print("✓ Index built with metadata preserved")

    # Test retrieval with metadata
    query = "What does mutual information measure?"
    print(f"\nQuerying: '{query}'")

    retriever = index.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve(query)

    print(f"\nRetrieved {len(nodes)} results:")
    for i, node in enumerate(nodes, 1):
        citation = extract_citation_from_node(node)
        print(f"\n  Result {i}:")
        print(f"    Source ID: {citation['source_id']}")
        print(f"    Source Type: {citation['source_type']}")
        print(f"    Score: {citation['score']:.4f}")
        print(f"    Text: {citation['text'][:80]}...")
