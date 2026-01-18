"""Dual-index builder with Chroma vector store.

This module builds two separate indexes:
1. Word-based: 512 character chunks with 50 character overlap
2. Sentence-based: Pure sentence splitting (no size limit)

Both indexes use Chroma for persistent storage.

"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore

try:
    import chromadb
except ImportError:
    raise ImportError("chromadb is required. Install with: pip install chromadb")


def split_text_by_characters(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into fixed-size character chunks.
    
    Args:
        text: Text to split.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Characters to overlap between chunks.
        
    Returns:
        List of text chunks.
    """
    if not text:
        return []
    
    chunks = []
    text_len = len(text)
    i = 0
    
    while i < text_len:
        end = min(i + chunk_size, text_len)
        chunk_text = text[i:end]
        
        # Try to break at word boundary if not at end
        if end < text_len and ' ' in chunk_text:
            last_space = chunk_text.rfind(' ')
            if last_space > chunk_size // 2:  # Only break if we're past halfway
                end = i + last_space + 1
                chunk_text = text[i:end]
        
        chunks.append(chunk_text)
        
        # Move to next chunk with overlap
        if chunk_overlap > 0 and end < text_len:
            i = end - chunk_overlap
        else:
            i = end
    
    return chunks


def load_sources_from_yaml(config_path: Path) -> list[Document]:
    """Load documents from sources specified in YAML configuration.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        List of Document objects with metadata.

    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    all_documents = []

    for source in sources:
        source_type = source.get("type")
        metadata = source.get("metadata", {})

        if source_type == "file":
            # Load from local files
            docs = _load_file_source(source, metadata)
            all_documents.extend(docs)
        elif source_type == "url":
            # Load from URL
            docs = _load_url_source(source, metadata)
            all_documents.extend(docs)
        else:
            print(f"Warning: Unknown source type '{source_type}', skipping")

    return all_documents


def _load_file_source(
    source: dict[str, Any], metadata: dict[str, Any]
) -> list[Document]:
    """Load documents from file source.

    Args:
        source: Source configuration dictionary.
        metadata: Additional metadata to attach.

    Returns:
        List of Document objects.

    """
    documents = []
    source_path = Path(source.get("path", ""))

    if not source_path.exists():
        print(f"Warning: Source path {source_path} does not exist, skipping")
        return documents

    patterns = source.get("patterns", ["*.txt", "*.md"])
    file_paths = []

    for pattern in patterns:
        file_paths.extend(source_path.glob(f"**/{pattern}"))

    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Create metadata for citation
            doc_metadata = {
                "source_id": f"file_{file_path.stem}",
                "source_type": metadata.get("source_type", "file"),
                "file_path": str(file_path),
                "file_name": file_path.name,
                **metadata,
            }

            doc = Document(text=content, metadata=doc_metadata)
            documents.append(doc)
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")

    return documents


def _load_url_source(
    source: dict[str, Any], metadata: dict[str, Any]
) -> list[Document]:
    """Load documents from URL source.

    Args:
        source: Source configuration dictionary.
        metadata: Additional metadata to attach.

    Returns:
        List of Document objects.

    """
    documents = []
    url = source.get("url", "")
    cache_dir = Path(source.get("cache_dir", tempfile.mkdtemp()))

    if not url:
        print("Warning: URL source missing 'url' field, skipping")
        return documents

    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Generate cache filename from URL
    parsed_url = urlparse(url)
    cache_filename = f"{parsed_url.netloc}_{parsed_url.path.replace('/', '_')}.txt"
    cache_path = cache_dir / cache_filename

    # Check if cached version exists
    if cache_path.exists():
        print(f"Loading cached content from {cache_path}")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Failed to load cached content: {e}")
            return documents
    else:
        # Fetch from URL
        print(f"Fetching content from {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text

            # Cache the content
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Warning: Failed to fetch URL {url}: {e}")
            return documents

    # Create document with metadata
    doc_metadata = {
        "source_id": metadata.get("source_id", f"url_{parsed_url.netloc}"),
        "source_type": metadata.get("source_type", "url"),
        "url": url,
        "cache_path": str(cache_path),
        **metadata,
    }

    doc = Document(text=content, metadata=doc_metadata)
    documents.append(doc)

    return documents


def build_word_index(
    documents: list[Document],
    persist_dir: Path,
    collection_name: str = "word_index",
) -> VectorStoreIndex:
    """Build word-based index with 512 character chunks and 50 character overlap.

    Args:
        documents: List of Document objects.
        persist_dir: Directory to persist the Chroma database.
        collection_name: Name of the Chroma collection.

    Returns:
        VectorStoreIndex with word-based chunking.

    """
    # Create Chroma client and collection
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    chroma_collection = chroma_client.get_or_create_collection(collection_name)

    # Create vector store
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Manually chunk documents using character-based splitting
    all_nodes = []
    for doc in documents:
        text = doc.text
        chunks = split_text_by_characters(text, chunk_size=512, chunk_overlap=50)
        
        for chunk in chunks:
            node = TextNode(
                text=chunk,
                metadata=doc.metadata.copy(),
            )
            all_nodes.append(node)

    # Create index from nodes
    index = VectorStoreIndex(
        nodes=all_nodes,
        storage_context=storage_context,
        show_progress=True,
    )

    return index


def build_sentence_index(
    documents: list[Document],
    persist_dir: Path,
    collection_name: str = "sentence_index",
) -> VectorStoreIndex:
    """Build sentence-based index with pure sentence splitting.

    Args:
        documents: List of Document objects.
        persist_dir: Directory to persist the Chroma database.
        collection_name: Name of the Chroma collection.

    Returns:
        VectorStoreIndex with sentence-based chunking.

    """
    # Create Chroma client and collection
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    chroma_collection = chroma_client.get_or_create_collection(collection_name)

    # Create vector store
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Configure node parser for sentence-based chunking (no size limit)
    # Note: Use a very large chunk_size to effectively get pure sentence splitting
    # SentenceSplitter doesn't support chunk_size=None
    node_parser = SentenceSplitter(
        chunk_size=10000,  # Very large chunk to get full sentences
        chunk_overlap=0,
        separator=" ",  # Split on sentences (default behavior)
    )

    # Create index
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[node_parser],
        show_progress=True,
    )

    return index


def build_dual_indexes(
    config_path: Path,
    persist_dir: Path,
) -> tuple[VectorStoreIndex, VectorStoreIndex]:
    """Build both word-based and sentence-based indexes from YAML config.

    Args:
        config_path: Path to the YAML configuration file.
        persist_dir: Directory to persist the Chroma databases.

    Returns:
        Tuple of (word_index, sentence_index).

    """
    print(f"Loading sources from {config_path}")
    documents = load_sources_from_yaml(config_path)
    print(f"Loaded {len(documents)} documents")

    if not documents:
        raise ValueError("No documents loaded from sources")

    # Create persist directory if it doesn't exist
    persist_dir.mkdir(parents=True, exist_ok=True)

    print("\nBuilding word-based index (512 chars, 50 overlap)...")
    word_index = build_word_index(documents, persist_dir, "word_index")

    print("\nBuilding sentence-based index (pure sentence splitting)...")
    sentence_index = build_sentence_index(documents, persist_dir, "sentence_index")

    print(f"\n✓ Dual indexes built and persisted to {persist_dir}")

    return word_index, sentence_index


def load_dual_indexes(persist_dir: Path) -> tuple[VectorStoreIndex, VectorStoreIndex]:
    """Load existing dual indexes from persistent storage.

    Args:
        persist_dir: Directory containing the persisted Chroma databases.

    Returns:
        Tuple of (word_index, sentence_index).

    """
    # Create Chroma client
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))

    # Load word-based index
    word_collection = chroma_client.get_collection("word_index")
    word_vector_store = ChromaVectorStore(chroma_collection=word_collection)
    word_index = VectorStoreIndex.from_vector_store(word_vector_store)

    # Load sentence-based index
    sentence_collection = chroma_client.get_collection("sentence_index")
    sentence_vector_store = ChromaVectorStore(chroma_collection=sentence_collection)
    sentence_index = VectorStoreIndex.from_vector_store(sentence_vector_store)

    return word_index, sentence_index


if __name__ == "__main__":
    # Test dual index building
    from config.llm_config import setup_llamaindex_defaults

    print("Testing dual index builder...")

    # Setup LlamaIndex
    setup_llamaindex_defaults()

    # Create sample documents
    sample_texts = [
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
    ]

    sample_sources = [
        {"source_id": "slide_12", "source_type": "slide", "page_number": 12},
        {"source_id": "slide_13", "source_type": "slide", "page_number": 13},
        {"source_id": "slide_14", "source_type": "slide", "page_number": 14},
    ]

    from evidence.index_builder import create_documents_with_metadata

    documents = create_documents_with_metadata(sample_texts, sample_sources)

    # Build indexes in retrieval_core/tmp/
    temp_dir = Path(__file__).parent / "tmp" / f"test_index_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nBuilding indexes in {temp_dir}")

    word_index = build_word_index(documents, temp_dir, "test_word_index")
    print("✓ Word-based index built")

    sentence_index = build_sentence_index(documents, temp_dir, "test_sentence_index")
    print("✓ Sentence-based index built")

    # Test retrieval
    query = "What is mutual information?"
    print(f"\nTesting retrieval with query: '{query}'")

    word_retriever = word_index.as_retriever(similarity_top_k=2)
    word_nodes = word_retriever.retrieve(query)
    print(f"Word-based retrieval: {len(word_nodes)} results")

    sentence_retriever = sentence_index.as_retriever(similarity_top_k=2)
    sentence_nodes = sentence_retriever.retrieve(query)
    print(f"Sentence-based retrieval: {len(sentence_nodes)} results")

    print("\n✓ Dual index builder test complete")
