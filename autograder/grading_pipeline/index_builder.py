"""Grading Pipeline: Extends retrieval_core with PDF support and incremental indexing.

This module imports and reuses all retrieval_core functionality,
adding PDF-specific file loading and incremental indexing capabilities.

Key Functions:
    - _extract_text_from_pdf(): Extract text from PDF files
    - _load_file_source_with_pdf(): Load file sources with PDF support
    - load_sources_from_yaml_with_pdf(): YAML loader with PDF support
    - build_or_update_dual_indexes(): Incremental indexing (NEW)

Imported from retrieval_core (reused as-is):
    - build_word_index(): Word-based index building
    - build_sentence_index(): Sentence-based index building
    - build_dual_indexes(): Build both indexes from config
    - load_dual_indexes(): Load persistent indexes from ChromaDB

"""

from pathlib import Path
from typing import Any

import yaml
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore

try:
    import chromadb
except ImportError:
    raise ImportError("chromadb is required. Install with: pip install chromadb")

try:
    import pypdf
except ImportError:
    raise ImportError(
        "pypdf is required for PDF support. Install with: pip install pypdf"
    )

# Import from retrieval_core - REUSE AS-IS
# Import manifest management
from grading_pipeline.manifest import (
    create_manifest_entry,
    get_source_info,
    has_source_changed,
    load_manifest,
    save_manifest,
)
from retrieval_core.index_builder import (
    _load_url_source,  # URL loading with caching
    build_dual_indexes,  # Build both indexes from config
    build_sentence_index,  # Sentence index building
    build_word_index,  # Word index building
    load_dual_indexes,  # Load persistent indexes
    split_text_by_characters,  # Character-based text splitter function
)


def _get_chunk_size_for_source(source_type: str | None) -> int:
    """Get appropriate chunk size in characters based on source type.

    Args:
        source_type: Type of source document (e.g., "slide", "textbook", "file").

    Returns:
        Chunk size in characters (128 for slides, 512 for others).

    """
    if source_type == "slide":
        return 128  # Smaller chunks for slides
    else:
        return 512  # Standard for other sources


def _extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file using pypdf.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text content from all pages.

    """
    text_content = []

    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)

            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():  # Only add non-empty pages
                        text_content.append(page_text)
                except Exception as e:
                    print(
                        f"Warning: Failed to extract text from page {page_num} "
                        f"of {file_path}: {e}"
                    )

    except Exception as e:
        print(f"Warning: Failed to read PDF {file_path}: {e}")
        return ""

    return "\n\n".join(text_content)


def _load_file_source_with_pdf(
    source: dict[str, Any], metadata: dict[str, Any]
) -> list[Document]:
    """Load file sources with PDF support.

    Extends retrieval_core's _load_file_source() logic:
    - For .pdf files: Use _extract_text_from_pdf()
    - For .txt, .md files: Use same logic as retrieval_core (reimplemented inline)
    - Same metadata structure as retrieval_core

    Args:
        source: Source configuration dictionary with 'path' and 'patterns' keys.
        metadata: Additional metadata to attach to documents.

    Returns:
        List of Document objects with extracted text and metadata.

    """
    documents = []
    source_path = Path(source.get("path", ""))

    if not source_path.exists():
        print(f"Warning: Source path {source_path} does not exist, skipping")
        return documents

    patterns = source.get("patterns", ["*.txt", "*.md"])
    file_paths = []

    # Collect all matching files
    for pattern in patterns:
        file_paths.extend(source_path.glob(f"**/{pattern}"))

    # Process each file
    for file_path in file_paths:
        try:
            # Check if it's a PDF file
            if file_path.suffix.lower() == ".pdf":
                # Extract text from PDF
                content = _extract_text_from_pdf(file_path)
                if not content.strip():
                    print(f"Warning: No text extracted from PDF {file_path}")
                    continue
            else:
                # Read as text file (same as version1)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

            # Create metadata for citation (same structure as version1)
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


def load_sources_from_yaml_with_pdf(config_path: Path) -> list[Document]:
    """Load documents from sources specified in YAML configuration with PDF support.

    Similar structure to retrieval_core's load_sources_from_yaml():
    - For 'file' sources: Use _load_file_source_with_pdf() (handles PDF, TXT, MD)
    - For 'url' sources: Import and use retrieval_core's _load_url_source()

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
            # Load from local files with PDF support
            docs = _load_file_source_with_pdf(source, metadata)
            all_documents.extend(docs)
        elif source_type == "url":
            # Load from URL using retrieval_core's function
            docs = _load_url_source(source, metadata)
            all_documents.extend(docs)
        else:
            print(f"Warning: Unknown source type '{source_type}', skipping")

    return all_documents


def delete_source_from_indexes(
    persist_dir: Path,
    source_id: str,
    word_collection_name: str = "word_index",
    sentence_collection_name: str = "sentence_index",
) -> tuple[int, int]:
    """Delete all embeddings for a specific source from both indexes.

    Args:
        persist_dir: Directory containing the persisted ChromaDB.
        source_id: Source ID to delete.
        word_collection_name: Name of word index collection.
        sentence_collection_name: Name of sentence index collection.

    Returns:
        Tuple of (num_deleted_word, num_deleted_sentence).

    """
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))

    # Delete from word index
    try:
        word_collection = chroma_client.get_collection(word_collection_name)
        word_collection.delete(where={"source_id": {"$eq": source_id}})
        num_word = word_collection.count()  # Count remaining after deletion
        print(f"  Deleted embeddings for {source_id} from word index")
    except Exception as e:
        print(f"  Warning: Failed to delete from word index: {e}")
        num_word = 0

    # Delete from sentence index
    try:
        sentence_collection = chroma_client.get_collection(sentence_collection_name)
        sentence_collection.delete(where={"source_id": {"$eq": source_id}})
        num_sentence = sentence_collection.count()  # Count remaining after deletion
        print(f"  Deleted embeddings for {source_id} from sentence index")
    except Exception as e:
        print(f"  Warning: Failed to delete from sentence index: {e}")
        num_sentence = 0

    return (num_word, num_sentence)


def add_documents_to_indexes(
    documents: list[Document],
    persist_dir: Path,
    word_collection_name: str = "word_index",
    sentence_collection_name: str = "sentence_index",
) -> tuple[int, int]:
    """Add new documents to existing indexes incrementally.

    Args:
        documents: List of Document objects to add.
        persist_dir: Directory containing the persisted ChromaDB.
        word_collection_name: Name of word index collection.
        sentence_collection_name: Name of sentence index collection.

    Returns:
        Tuple of (num_chunks_word, num_chunks_sentence) added.

    """
    if not documents:
        return (0, 0)

    chroma_client = chromadb.PersistentClient(path=str(persist_dir))

    # Group documents by source_type for source-aware chunking
    from collections import defaultdict

    docs_by_type = defaultdict(list)
    for doc in documents:
        source_type = doc.metadata.get("source_type", "file")
        docs_by_type[source_type].append(doc)

    # Add to word index with source-type-aware chunking
    # https://cookbook.chromadb.dev/core/configuration/
    word_collection = chroma_client.get_or_create_collection(word_collection_name,
       metadata={
          "hnsw:space": "cosine", 
          "hnsw:search_ef": 1000,  # larger than nb of chunks for deterministic search, much higher recall
          "hnsw:construction_ef": 200,  # better graph quality
          "hnsw:M": 32, # denser graph (more memory)
       })
    word_vector_store = ChromaVectorStore(chroma_collection=word_collection)
    word_storage_context = StorageContext.from_defaults(vector_store=word_vector_store)

    # Process each source type group with appropriate chunk size
    word_index = None
    for idx, (source_type, type_docs) in enumerate(docs_by_type.items()):
        chunk_size = _get_chunk_size_for_source(source_type)

        if len(docs_by_type) > 1:
            print(
                f"  Processing {len(type_docs)} {source_type} document(s) with chunk_size={chunk_size}...",
                flush=True,
            )

        # Manually chunk documents using character-based splitting
        nodes = []
        for doc in type_docs:
            chunks = split_text_by_characters(
                doc.text, chunk_size=chunk_size, chunk_overlap=50
            )
            for chunk in chunks:
                node = TextNode(text=chunk, metadata=doc.metadata.copy())
                nodes.append(node)

        if idx == 0:
            # First group: create index from nodes
            word_index = VectorStoreIndex(
                nodes=nodes,
                storage_context=word_storage_context,
                show_progress=True,
            )
        else:
            # Subsequent groups: insert nodes
            word_index.insert_nodes(nodes)

    # Add to sentence index
    sentence_collection = chroma_client.get_or_create_collection(
        sentence_collection_name
    )
    sentence_vector_store = ChromaVectorStore(chroma_collection=sentence_collection)
    sentence_storage_context = StorageContext.from_defaults(
        vector_store=sentence_vector_store
    )

    # Configure sentence-based chunking
    sentence_parser = SentenceSplitter(chunk_size=10000, chunk_overlap=0, separator=" ")

    print(f"  Building sentence index...", flush=True)

    # Create index and insert documents
    sentence_index = VectorStoreIndex.from_documents(
        documents,
        storage_context=sentence_storage_context,
        transformations=[sentence_parser],
        show_progress=True,
    )

    # Get actual chunk counts from ChromaDB collections
    num_chunks_word = word_collection.count()
    num_chunks_sentence = sentence_collection.count()

    return (num_chunks_word, num_chunks_sentence)


def build_or_update_dual_indexes(
    config_path: Path,
    persist_dir: Path,
    lazy_load_embeddings: bool = True,
) -> tuple[VectorStoreIndex, VectorStoreIndex]:
    """Build new indexes or incrementally update existing ones.

    This function implements smart incremental indexing:
    - Loads source manifest to see what's already indexed
    - Compares sources from YAML to manifest
    - Only indexes new or changed sources
    - Deletes old embeddings before re-indexing changed sources
    - Updates manifest with latest state
    - Lazy loads embedding model only when needed (huge speedup!)

    Args:
        config_path: Path to the YAML configuration file.
        persist_dir: Directory to persist the Chroma databases.
        lazy_load_embeddings: If True, only load embedding model when needed.
            This provides massive speedup (~6s) when no indexing is needed.

    Returns:
        Tuple of (word_index, sentence_index).

    """
    print(f"Loading sources from {config_path}")
    documents = load_sources_from_yaml_with_pdf(config_path)
    print(f"✓ Loaded {len(documents)} documents from YAML")

    if not documents:
        raise ValueError("No documents loaded from sources")

    # Create persist directory if it doesn't exist
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest to check what's already indexed
    manifest = load_manifest(persist_dir)
    existing_sources = manifest.get("sources", {})

    # Check if indexes exist
    indexes_exist = False
    try:
        chroma_client = chromadb.PersistentClient(path=str(persist_dir))
        collections = [c.name for c in chroma_client.list_collections()]
        indexes_exist = "word_index" in collections and "sentence_index" in collections
    except Exception:
        indexes_exist = False

    # Categorize documents: new, changed, unchanged
    new_docs = []
    changed_docs = []
    unchanged_docs = []

    for doc in documents:
        source_id = doc.metadata.get("source_id", "unknown")
        file_path = Path(doc.metadata.get("file_path", ""))

        if source_id not in existing_sources:
            # New source
            new_docs.append(doc)
            print(f"  NEW: {source_id} ({doc.metadata.get('file_name')})")
        elif has_source_changed(file_path, existing_sources[source_id]):
            # Changed source
            changed_docs.append(doc)
            print(
                f"  CHANGED: {source_id} ({doc.metadata.get('file_name')}) "
                f"- will delete old embeddings and re-index"
            )
        else:
            # Unchanged source
            unchanged_docs.append(doc)
            print(
                f"  UNCHANGED: {source_id} ({doc.metadata.get('file_name')}) - skipping"
            )

    # Determine if we need embedding model
    needs_embedding = not indexes_exist or new_docs or changed_docs

    # Lazy load embedding model only when needed
    if needs_embedding and lazy_load_embeddings:
        print(f"\n[Lazy Loading] Embedding model needed for indexing...")
        from config.llm_config import setup_llamaindex_defaults

        setup_llamaindex_defaults()
        print(f"✓ Embedding model loaded")

    # Decide on indexing strategy
    if not indexes_exist:
        # No indexes exist - do fresh build
        print(f"\nNo existing indexes found - building fresh indexes...")
        print(
            f"Building word-based index (source-aware chunking: 128 chars for slides, 512 chars for others)..."
        )
        # Use add_documents_to_indexes for source-aware chunking (builds both indexes)
        num_word, num_sentence = add_documents_to_indexes(documents, persist_dir)
        print(f"  ✓ Created {num_word} word chunks, {num_sentence} sentence chunks")

        # Load the indexes we just created
        word_index, sentence_index = load_dual_indexes(persist_dir)

        # Create manifest entries for all sources
        sentence_parser = SentenceSplitter(
            chunk_size=10000, chunk_overlap=0, separator=" "
        )
        for doc in documents:
            source_id = doc.metadata.get("source_id")
            source_type = doc.metadata.get("source_type", "file")
            # Estimate chunk counts with source-type-aware chunking
            chunk_size = _get_chunk_size_for_source(source_type)
            chunks = split_text_by_characters(
                doc.text, chunk_size=chunk_size, chunk_overlap=50
            )
            num_chunks_word = len(chunks)
            num_chunks_sentence = len(sentence_parser.get_nodes_from_documents([doc]))

            entry = create_manifest_entry(doc, num_chunks_word, num_chunks_sentence)
            manifest["sources"][source_id] = entry

    elif not new_docs and not changed_docs:
        # All sources unchanged - just load existing
        print(f"\nAll sources unchanged - loading existing indexes...")

        # For loading only, we need minimal embedding setup (but won't use it)
        if lazy_load_embeddings:
            # Set a lightweight placeholder - won't be used for loading
            from llama_index.core import Settings
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            # Directly set without checking (checking triggers initialization)
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

        word_index, sentence_index = load_dual_indexes(persist_dir)

    else:
        # Incremental update needed
        print(f"\nIncremental update: {len(new_docs)} new, {len(changed_docs)} changed")

        # Delete embeddings for changed sources
        for doc in changed_docs:
            source_id = doc.metadata.get("source_id")
            print(f"  Deleting old embeddings for {source_id}...")
            delete_source_from_indexes(persist_dir, source_id)

        # Add new and changed documents
        docs_to_add = new_docs + changed_docs
        if docs_to_add:
            print(f"  Adding {len(docs_to_add)} documents to indexes...")
            num_word, num_sentence = add_documents_to_indexes(docs_to_add, persist_dir)
            print(f"  ✓ Added {num_word} word chunks, {num_sentence} sentence chunks")

            # Update manifest for new and changed sources
            for doc in docs_to_add:
                source_id = doc.metadata.get("source_id")
                source_type = doc.metadata.get("source_type", "file")
                # Estimate chunk counts with source-type-aware chunking
                chunk_size = _get_chunk_size_for_source(source_type)
                chunks = split_text_by_characters(
                    doc.text, chunk_size=chunk_size, chunk_overlap=50
                )
                num_chunks_word = len(chunks)

                sentence_parser = SentenceSplitter(
                    chunk_size=10000, chunk_overlap=0, separator=" "
                )
                num_chunks_sentence = len(
                    sentence_parser.get_nodes_from_documents([doc])
                )

                entry = create_manifest_entry(doc, num_chunks_word, num_chunks_sentence)
                manifest["sources"][source_id] = entry

        # Load the updated indexes
        word_index, sentence_index = load_dual_indexes(persist_dir)

    # Save updated manifest
    save_manifest(persist_dir, manifest)

    print(f"\n✓ Dual indexes ready at {persist_dir}")
    return word_index, sentence_index


# Re-export retrieval_core functions for convenience
__all__ = [
    "load_sources_from_yaml_with_pdf",  # NEW: PDF-aware YAML loader
    "build_or_update_dual_indexes",  # NEW: Incremental indexing
    "build_word_index",  # From retrieval_core
    "build_sentence_index",  # From retrieval_core
    "build_dual_indexes",  # From retrieval_core
    "load_dual_indexes",  # From retrieval_core
]


if __name__ == "__main__":
    # Test incremental indexing functionality with lazy loading
    print(
        "Testing grading_pipeline incremental indexing with lazy embedding loading..."
    )

    # NOTE: We do NOT call setup_llamaindex_defaults() here!
    # It will be called lazily inside build_or_update_dual_indexes()
    # ONLY when embedding is actually needed (new/changed sources).

    # Test YAML loading and incremental indexing
    config_path = Path(__file__).parent / "config" / "sources.yaml"

    # Use test directory if running from test script, otherwise use production tmp
    # Check if we're in a test environment by looking for tests/ directory
    tests_dir = Path(__file__).parent.parent / "tests"
    if tests_dir.exists():
        # Running from test - use test directory
        persist_dir = tests_dir / "tmp_chroma_indexes" / "index_builder_test"
    else:
        # Production use - use production tmp
        persist_dir = Path(__file__).parent / "tmp" / "chroma_db"

    if config_path.exists():
        print(f"\nBuilding or updating indexes from {config_path}")
        word_index, sentence_index = build_or_update_dual_indexes(
            config_path, persist_dir
        )
        print(f"✓ Indexes ready")

        # For retrieval, we need embeddings loaded
        # Check if we need to load them for retrieval
        try:
            from llama_index.core import Settings

            if Settings.embed_model is None:
                print("\n[Loading embeddings for retrieval test...]")
                from config.llm_config import setup_llamaindex_defaults

                setup_llamaindex_defaults()
        except Exception:
            pass

        # Test retrieval
        query = "What is data quality?"
        print(f"\nTesting retrieval with query: '{query}'")

        word_retriever = word_index.as_retriever(similarity_top_k=2)
        word_nodes = word_retriever.retrieve(query)
        print(f"  Word-based retrieval: {len(word_nodes)} results")

        sentence_retriever = sentence_index.as_retriever(similarity_top_k=2)
        sentence_nodes = sentence_retriever.retrieve(query)
        print(f"  Sentence-based retrieval: {len(sentence_nodes)} results")
    else:
        print(f"Config file not found: {config_path}")
        print("Create grading_pipeline/config/sources.yaml to test")

    print("\n✓ Grading pipeline incremental indexing test complete")
