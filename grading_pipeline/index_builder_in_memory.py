"""Grading Pipeline: In-memory vector store with pickle persistence.

This module provides an in-memory vector database implementation that mirrors
ChromaDB functionality but uses pickle for persistence. Supports cosine similarity,
deterministic retrieval (exhaustive search), and the same interface as ChromaDB.

Key Components:
    - InMemoryVectorStore: Custom vector store with pickle persistence
    - build_word_index_in_memory(): Build word-based index
    - build_sentence_index_in_memory(): Build sentence-based index
    - build_or_update_dual_indexes_in_memory(): Incremental indexing
    - load_dual_indexes_in_memory(): Load indexes from pickle files

"""

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, NodeWithScore, TextNode
from llama_index.core.vector_stores import (
    MetadataFilters,
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from pydantic import ConfigDict

# Import from existing index_builder for reuse
from grading_pipeline.index_builder import (
    _extract_text_from_pdf,
    _get_chunk_size_for_source,
    _load_file_source_with_pdf,
    get_embedding_model_info,
    load_embedding_metadata,
    load_sources_from_yaml_with_pdf,
    save_embedding_metadata,
    verify_embedding_model,
)
from grading_pipeline.manifest import (
    create_manifest_entry,
    get_source_info,
    has_source_changed,
    load_manifest,
    save_manifest,
)
from retrieval_core.index_builder import (
    _load_url_source,
    split_text_by_characters,
)


def create_text_node_with_embed_text_only(
    text: str, metadata: dict[str, Any]
) -> TextNode:
    """Create TextNode that excludes metadata from embeddings.

    Args:
        text: Chunk text for the node.
        metadata: Metadata dictionary for the node.

    Returns:
        TextNode configured to exclude metadata from embeddings.

    """
    metadata_keys = list(metadata.keys())
    return TextNode(
        text=text,
        metadata=metadata,
        excluded_embed_metadata_keys=metadata_keys,
    )


def load_chunking_config(config_path: Path | None = None) -> dict:
    """Load chunking configuration from YAML file.

    Args:
        config_path: Path to sources.yaml. If None, uses default location.

    Returns:
        Dictionary with word and sentence chunking configs.

    """
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "sources.yaml"

    if not config_path.exists():
        # Return defaults if config doesn't exist
        return {
            "word": {"chunk_size": 512, "chunk_overlap": 50},
            "sentence": {"chunk_size": 10000, "chunk_overlap": 0},
        }

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Extract chunking config, use defaults if not present
    chunking = config.get("chunking", {})
    return {
        "word": chunking.get("word", {"chunk_size": 512, "chunk_overlap": 50}),
        "sentence": chunking.get("sentence", {"chunk_size": 10000, "chunk_overlap": 0}),
    }


def create_sentence_splitter(
    config_path: Path | None = None,
    source_type: str | None = None,
    **overrides: Any,
) -> SentenceSplitter:
    """Create SentenceSplitter with configuration from YAML.

    Args:
        config_path: Path to sources.yaml. If None, uses default location.
        source_type: Type of source ('slide', 'file', etc.). Used to select
                     appropriate secondary_chunking_regex.
        **overrides: Override specific parameters (e.g., chunk_size=200 for testing).

    Returns:
        Configured SentenceSplitter instance.

    """
    chunking_config = load_chunking_config(config_path)
    sentence_config = chunking_config["sentence"].copy()

    # Select secondary_chunking_regex based on source_type
    if source_type == "slide":
        # For slides: split on line breaks (\n) in addition to punctuation
        regex_key = "secondary_chunking_regex_slides"
    else:
        # For regular files: use default punctuation-based regex
        regex_key = "secondary_chunking_regex_default"

    if regex_key in sentence_config:
        sentence_config["secondary_chunking_regex"] = sentence_config[regex_key]

    # Remove the config-specific keys (not valid SentenceSplitter params)
    sentence_config.pop("secondary_chunking_regex_default", None)
    sentence_config.pop("secondary_chunking_regex_slides", None)

    # Apply any overrides
    sentence_config.update(overrides)

    return SentenceSplitter(**sentence_config)


class InMemoryVectorStore(BasePydanticVectorStore):
    """In-memory vector store with cosine similarity and pickle persistence.

    Stores embeddings, nodes, and metadata in memory. Supports deterministic
    retrieval using exhaustive cosine similarity search. Can be saved/loaded
    from pickle files.

    Attributes:
        embeddings: Dict mapping node_id to embedding vector (numpy array).
        nodes: Dict mapping node_id to TextNode objects.
        metadata: Dict mapping node_id to metadata dictionaries.
        stores_text: Whether the store stores text (always True).

    """

    model_config = ConfigDict(extra="allow")

    stores_text: bool = True
    is_embedding_query: bool = True

    def __init__(self, **kwargs: Any) -> None:
        """Initialize empty in-memory vector store."""
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic validation for runtime data
        object.__setattr__(self, "embeddings", {})
        object.__setattr__(self, "nodes", {})
        object.__setattr__(self, "metadata", {})

    def add(
        self,
        nodes: list[BaseNode],
        **add_kwargs: Any,
    ) -> list[str]:
        """Add nodes with their embeddings to the store.

        Args:
            nodes: List of BaseNode objects with embeddings.
            **add_kwargs: Additional keyword arguments (unused).

        Returns:
            List of node IDs that were added.

        """
        node_ids = []
        for node in nodes:
            node_id = node.node_id

            # Extract embedding from node
            if node.embedding is None:
                raise ValueError(f"Node {node_id} has no embedding")

            # Store as numpy array for efficient computation
            self.embeddings[node_id] = np.array(node.embedding, dtype=np.float32)
            self.nodes[node_id] = node
            self.metadata[node_id] = node.metadata or {}

            node_ids.append(node_id)

        return node_ids

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """Delete nodes by reference document ID.

        Args:
            ref_doc_id: Reference document ID to delete.
            **delete_kwargs: Additional keyword arguments (unused).

        """
        # Find all nodes with matching ref_doc_id
        nodes_to_delete = []
        for node_id, node in self.nodes.items():
            if hasattr(node, "ref_doc_id") and node.ref_doc_id == ref_doc_id:
                nodes_to_delete.append(node_id)

        # Delete found nodes
        for node_id in nodes_to_delete:
            self.embeddings.pop(node_id, None)
            self.nodes.pop(node_id, None)
            self.metadata.pop(node_id, None)

    def delete_by_node_ids(self, node_ids: list[str]) -> None:
        """Delete nodes by their node IDs.

        Args:
            node_ids: List of node IDs to delete.

        """
        for node_id in node_ids:
            self.embeddings.pop(node_id, None)
            self.nodes.pop(node_id, None)
            self.metadata.pop(node_id, None)

    def query(
        self,
        query: VectorStoreQuery,
        **kwargs: Any,
    ) -> VectorStoreQueryResult:
        """Query the vector store using cosine similarity.

        Performs exhaustive search (computes similarity to all vectors) for
        deterministic results. Returns top-k most similar nodes.

        Args:
            query: VectorStoreQuery object with query embedding and parameters.
            **kwargs: Additional keyword arguments (unused).

        Returns:
            VectorStoreQueryResult with matching nodes, similarities, and IDs.

        """
        if query.query_embedding is None:
            # No embedding provided - return empty result
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])

        query_embedding = np.array(query.query_embedding, dtype=np.float32)

        # Normalize query embedding for cosine similarity
        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0:
            # Zero vector - return empty result
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])

        query_embedding = query_embedding / query_norm

        # Compute cosine similarity to all stored embeddings
        similarities: list[tuple[str, float]] = []
        for node_id, stored_embedding in self.embeddings.items():
            # Normalize stored embedding
            stored_norm = np.linalg.norm(stored_embedding)
            if stored_norm == 0:
                continue

            normalized_stored = stored_embedding / stored_norm

            # Cosine similarity: dot product of normalized vectors
            similarity = float(np.dot(query_embedding, normalized_stored))
            # Store similarity directly (like SimpleVectorStore does)
            similarities.append((node_id, similarity))

        # Apply metadata filters if provided
        if query.filters is not None:
            filtered_similarities = []
            for node_id, similarity in similarities:
                node_metadata = self.metadata.get(node_id, {})
                if self._matches_filters(node_metadata, query.filters):
                    filtered_similarities.append((node_id, similarity))
            similarities = filtered_similarities

        # Apply node_ids filter if provided (only if not empty)
        if query.node_ids is not None and len(query.node_ids) > 0:
            node_ids_set = set(query.node_ids)
            similarities = [
                (node_id, sim)
                for node_id, sim in similarities
                if node_id in node_ids_set
            ]

        # Sort by similarity (descending = most similar first), then by node_id for stability
        similarities.sort(key=lambda x: (-x[1], x[0]))

        # Get top-k results
        top_k = query.similarity_top_k
        top_similarities = similarities[:top_k]

        # Build result
        # Return nodes directly since we store them (stores_text=True)
        result_nodes: list[BaseNode] = []
        result_similarities: list[float] = []
        result_ids: list[str] = []

        for node_id, similarity in top_similarities:
            node = self.nodes[node_id]
            result_nodes.append(node)
            # Return similarity directly (like SimpleVectorStore)
            result_similarities.append(similarity)
            result_ids.append(node_id)

        return VectorStoreQueryResult(
            nodes=result_nodes, similarities=result_similarities, ids=result_ids
        )

    def _matches_filters(
        self, metadata: dict[str, Any], filters: MetadataFilters
    ) -> bool:
        """Check if metadata matches the provided filters.

        Args:
            metadata: Node metadata dictionary.
            filters: MetadataFilters object.

        Returns:
            True if metadata matches filters, False otherwise.

        """
        # Simple implementation: check if all filter conditions are met
        # This is a basic implementation - can be extended for more complex filters
        for filter_item in filters.filters:
            key = filter_item.key
            value = filter_item.value

            if key not in metadata:
                return False

            # Support equality check
            if metadata[key] != value:
                return False

        return True

    def persist(self, persist_path: str, **kwargs: Any) -> None:
        """Persist the vector store to disk using pickle.

        Args:
            persist_path: Path to save the pickle file.
            **kwargs: Additional keyword arguments (unused).

        """
        self.save_to_pickle(Path(persist_path))

    def save_to_pickle(self, path: Path) -> None:
        """Save the vector store to a pickle file.

        Args:
            path: Path to the pickle file.

        """
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "embeddings": self.embeddings,
            "nodes": self.nodes,
            "metadata": self.metadata,
        }

        with open(path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load_from_pickle(cls, path: Path) -> "InMemoryVectorStore":
        """Load a vector store from a pickle file.

        Args:
            path: Path to the pickle file.

        Returns:
            Loaded InMemoryVectorStore instance.

        """
        with open(path, "rb") as f:
            data = pickle.load(f)

        store = cls()
        # Use object.__setattr__ to bypass Pydantic validation for runtime data
        object.__setattr__(store, "embeddings", data["embeddings"])
        object.__setattr__(store, "nodes", data["nodes"])
        object.__setattr__(store, "metadata", data["metadata"])

        return store

    def get_nodes(
        self,
        node_ids: list[str] | None = None,
        filters: MetadataFilters | None = None,
    ) -> list[BaseNode]:
        """Get nodes by IDs or filters.

        Args:
            node_ids: List of node IDs to retrieve.
            filters: Metadata filters to apply.

        Returns:
            List of matching nodes.

        """
        if node_ids is not None:
            return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
        elif filters is not None:
            result = []
            for node_id, node in self.nodes.items():
                node_metadata = self.metadata.get(node_id, {})
                if self._matches_filters(node_metadata, filters):
                    result.append(node)
            return result
        else:
            return list(self.nodes.values())

    @property
    def client(self) -> None:
        """Return the underlying client (None for in-memory store).

        Returns:
            None (no underlying client).

        """
        return None


def build_word_index_in_memory(
    documents: list[Document],
    persist_dir: Path,
    collection_name: str = "word_index",
) -> VectorStoreIndex:
    """Build word-based index with character chunking using in-memory store.

    Args:
        documents: List of Document objects.
        persist_dir: Directory to persist the pickle file.
        collection_name: Name for the index (used in pickle filename).

    Returns:
        VectorStoreIndex with word-based chunking.

    """
    # Create in-memory vector store
    vector_store = InMemoryVectorStore()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Manually chunk documents using character-based splitting
    all_nodes = []
    for doc in documents:
        text = doc.text
        source_type = doc.metadata.get("source_type", "file")
        chunk_size = _get_chunk_size_for_source(source_type)

        chunks = split_text_by_characters(text, chunk_size=chunk_size, chunk_overlap=50)

        for chunk in chunks:
            node = create_text_node_with_embed_text_only(
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

    # Get the store from the index's storage context (it has been populated with nodes and embeddings)
    actual_store = index._storage_context.vector_store
    if not isinstance(actual_store, InMemoryVectorStore):
        raise ValueError(f"Expected InMemoryVectorStore, got {type(actual_store)}")

    # Save to pickle after embeddings are generated
    pickle_path = persist_dir / f"{collection_name}.pkl"
    actual_store.save_to_pickle(pickle_path)

    # Save embedding model metadata
    embedding_metadata = get_embedding_model_info()
    save_embedding_metadata(persist_dir, embedding_metadata)
    print(
        f"  ✓ Saved embedding model metadata: {embedding_metadata.get('embedding_type')} "
        f"({embedding_metadata.get('embedding_model')})"
    )

    return index


def build_sentence_index_in_memory(
    documents: list[Document],
    persist_dir: Path,
    collection_name: str = "sentence_index",
) -> VectorStoreIndex:
    """Build sentence-based index with SentenceSplitter (token-based chunking).

    Uses LlamaIndex's SentenceSplitter which splits by sentences and uses
    token-based chunk_size measurement. Automatically selects appropriate
    secondary_chunking_regex based on source_type (slides vs regular files).

    Args:
        documents: List of Document objects.
        persist_dir: Directory to persist the pickle file.
        collection_name: Name for the index (used in pickle filename).

    Returns:
        VectorStoreIndex with sentence-based chunking.

    """
    # Create in-memory vector store
    vector_store = InMemoryVectorStore()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Detect source_type from first document (assumes all docs are same type)
    source_type = None
    if documents:
        source_type = documents[0].metadata.get("source_type")

    # Configure node parser for sentence-based chunking (token-based)
    node_parser = create_sentence_splitter(source_type=source_type)

    print(f"  Building sentence index (token-based SentenceSplitter)...")
    if source_type == "slide":
        print(f"    Using slide-optimized regex (splits on \\n line breaks)")

    # Create index with sentence splitting
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[node_parser],
        show_progress=True,
    )

    # Get the store from the index's storage context (it has been populated with nodes and embeddings)
    actual_store = index._storage_context.vector_store
    if not isinstance(actual_store, InMemoryVectorStore):
        raise ValueError(f"Expected InMemoryVectorStore, got {type(actual_store)}")

    # Save to pickle after embeddings are generated
    pickle_path = persist_dir / f"{collection_name}.pkl"
    actual_store.save_to_pickle(pickle_path)

    # Save embedding model metadata
    embedding_metadata = get_embedding_model_info()
    save_embedding_metadata(persist_dir, embedding_metadata)
    print(
        f"  ✓ Saved embedding model metadata: {embedding_metadata.get('embedding_type')} "
        f"({embedding_metadata.get('embedding_model')})"
    )

    return index


def add_documents_to_indexes_in_memory(
    documents: list[Document],
    persist_dir: Path,
    word_collection_name: str = "word_index",
    sentence_collection_name: str = "sentence_index",
) -> tuple[int, int]:
    """Add new documents to existing indexes incrementally.

    Args:
        documents: List of Document objects to add.
        persist_dir: Directory containing the pickle files.
        word_collection_name: Name of word index.
        sentence_collection_name: Name of sentence index.

    Returns:
        Tuple of (num_chunks_word, num_chunks_sentence) added.

    """
    if not documents:
        return (0, 0)

    # Group documents by source_type for source-aware chunking
    from collections import defaultdict

    docs_by_type = defaultdict(list)
    for doc in documents:
        source_type = doc.metadata.get("source_type", "file")
        docs_by_type[source_type].append(doc)

    # Load or create word index
    word_pickle_path = persist_dir / f"{word_collection_name}.pkl"
    if word_pickle_path.exists():
        word_vector_store = InMemoryVectorStore.load_from_pickle(word_pickle_path)
    else:
        word_vector_store = InMemoryVectorStore()

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
                node = create_text_node_with_embed_text_only(
                    text=chunk,
                    metadata=doc.metadata.copy(),
                )
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

    # Save word index
    word_vector_store.save_to_pickle(word_pickle_path)

    # Save embedding model metadata
    embedding_metadata = get_embedding_model_info()
    save_embedding_metadata(persist_dir, embedding_metadata)
    print(
        f"  ✓ Saved embedding model metadata: {embedding_metadata.get('embedding_type')} "
        f"({embedding_metadata.get('embedding_model')})"
    )

    # Load or create sentence index
    sentence_pickle_path = persist_dir / f"{sentence_collection_name}.pkl"
    if sentence_pickle_path.exists():
        sentence_vector_store = InMemoryVectorStore.load_from_pickle(
            sentence_pickle_path
        )
    else:
        sentence_vector_store = InMemoryVectorStore()

    sentence_storage_context = StorageContext.from_defaults(
        vector_store=sentence_vector_store
    )

    # Configure sentence-based chunking (token-based)
    # Detect source_type from first document
    source_type = None
    if documents:
        source_type = documents[0].metadata.get("source_type")

    sentence_parser = create_sentence_splitter(source_type=source_type)

    print(
        f"  Building sentence index (token-based SentenceSplitter)...",
        flush=True,
    )
    if source_type == "slide":
        print(
            f"    Using slide-optimized regex (splits on \\n line breaks)", flush=True
        )

    # Create sentence nodes with SentenceSplitter
    sentence_nodes = sentence_parser.get_nodes_from_documents(documents)

    # Create or update sentence index
    if sentence_pickle_path.exists():
        # Load existing index and insert new nodes
        sentence_index = VectorStoreIndex.from_vector_store(sentence_vector_store)
        sentence_index.insert_nodes(sentence_nodes)
    else:
        # Create new index from nodes
        sentence_index = VectorStoreIndex(
            nodes=sentence_nodes,
            storage_context=sentence_storage_context,
            show_progress=True,
        )

    # Save sentence index
    sentence_vector_store.save_to_pickle(sentence_pickle_path)

    # Save embedding model metadata (update if already exists)
    embedding_metadata = get_embedding_model_info()
    save_embedding_metadata(persist_dir, embedding_metadata)
    print(
        f"  ✓ Saved embedding model metadata: {embedding_metadata.get('embedding_type')} "
        f"({embedding_metadata.get('embedding_model')})"
    )

    # Get actual chunk counts
    num_chunks_word = len(word_vector_store.nodes)
    num_chunks_sentence = len(sentence_vector_store.nodes)

    return (num_chunks_word, num_chunks_sentence)


def delete_source_from_indexes_in_memory(
    persist_dir: Path,
    source_id: str,
    word_collection_name: str = "word_index",
    sentence_collection_name: str = "sentence_index",
) -> tuple[int, int]:
    """Delete all embeddings for a specific source from both indexes.

    Args:
        persist_dir: Directory containing the pickle files.
        source_id: Source ID to delete.
        word_collection_name: Name of word index.
        sentence_collection_name: Name of sentence index.

    Returns:
        Tuple of (num_deleted_word, num_deleted_sentence).

    """
    num_deleted_word = 0
    num_deleted_sentence = 0

    # Delete from word index
    word_pickle_path = persist_dir / f"{word_collection_name}.pkl"
    if word_pickle_path.exists():
        word_vector_store = InMemoryVectorStore.load_from_pickle(word_pickle_path)

        # Find nodes with matching source_id
        nodes_to_delete = []
        for node_id, node in word_vector_store.nodes.items():
            node_metadata = word_vector_store.metadata.get(node_id, {})
            if node_metadata.get("source_id") == source_id:
                nodes_to_delete.append(node_id)

        word_vector_store.delete_by_node_ids(nodes_to_delete)
        num_deleted_word = len(nodes_to_delete)

        # Save updated index
        word_vector_store.save_to_pickle(word_pickle_path)
        print(
            f"  Deleted {num_deleted_word} embeddings for {source_id} from word index"
        )

    # Delete from sentence index
    sentence_pickle_path = persist_dir / f"{sentence_collection_name}.pkl"
    if sentence_pickle_path.exists():
        sentence_vector_store = InMemoryVectorStore.load_from_pickle(
            sentence_pickle_path
        )

        # Find nodes with matching source_id
        nodes_to_delete = []
        for node_id, node in sentence_vector_store.nodes.items():
            node_metadata = sentence_vector_store.metadata.get(node_id, {})
            if node_metadata.get("source_id") == source_id:
                nodes_to_delete.append(node_id)

        sentence_vector_store.delete_by_node_ids(nodes_to_delete)
        num_deleted_sentence = len(nodes_to_delete)

        # Save updated index
        sentence_vector_store.save_to_pickle(sentence_pickle_path)
        print(
            f"  Deleted {num_deleted_sentence} embeddings for {source_id} from sentence index"
        )

    return (num_deleted_word, num_deleted_sentence)


def load_dual_indexes_in_memory(
    persist_dir: Path,
    word_collection_name: str = "word_index",
    sentence_collection_name: str = "sentence_index",
) -> tuple[VectorStoreIndex, VectorStoreIndex]:
    """Load existing dual indexes from pickle files.

    Args:
        persist_dir: Directory containing the pickle files.
        word_collection_name: Name of word index.
        sentence_collection_name: Name of sentence index.

    Returns:
        Tuple of (word_index, sentence_index).

    Raises:
        ValueError: If embedding model doesn't match the one used to build the index.

    """
    # Verify embedding model matches
    stored_metadata = load_embedding_metadata(persist_dir)
    if stored_metadata:
        print(
            f"  Using embedding model: {stored_metadata.get('embedding_type')} "
            f"({stored_metadata.get('embedding_model')})"
        )
    verify_embedding_model(persist_dir)

    # Load word-based index
    word_pickle_path = persist_dir / f"{word_collection_name}.pkl"
    if not word_pickle_path.exists():
        raise FileNotFoundError(f"Word index not found: {word_pickle_path}")

    word_vector_store = InMemoryVectorStore.load_from_pickle(word_pickle_path)
    word_index = VectorStoreIndex.from_vector_store(word_vector_store)

    # Load sentence-based index
    sentence_pickle_path = persist_dir / f"{sentence_collection_name}.pkl"
    if not sentence_pickle_path.exists():
        raise FileNotFoundError(f"Sentence index not found: {sentence_pickle_path}")

    sentence_vector_store = InMemoryVectorStore.load_from_pickle(sentence_pickle_path)
    sentence_index = VectorStoreIndex.from_vector_store(sentence_vector_store)

    return word_index, sentence_index


def build_or_update_dual_indexes_in_memory(
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
    - Lazy loads embedding model only when needed

    Args:
        config_path: Path to the YAML configuration file.
        persist_dir: Directory to persist the pickle files.
        lazy_load_embeddings: If True, only load embedding model when needed.

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
    word_pickle_path = persist_dir / "word_index.pkl"
    sentence_pickle_path = persist_dir / "sentence_index.pkl"
    indexes_exist = word_pickle_path.exists() and sentence_pickle_path.exists()

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
        # Use add_documents_to_indexes_in_memory for source-aware chunking
        num_word, num_sentence = add_documents_to_indexes_in_memory(
            documents, persist_dir
        )
        print(f"  ✓ Created {num_word} word chunks, {num_sentence} sentence chunks")

        # Load the indexes we just created
        word_index, sentence_index = load_dual_indexes_in_memory(persist_dir)

        # Create manifest entries for all sources
        sentence_parser = create_sentence_splitter()
        for doc in documents:
            source_id = doc.metadata.get("source_id")
            source_type = doc.metadata.get("source_type", "file")

            # Estimate chunk counts with source-type-aware chunking
            # Load word chunking config
            chunking_config = load_chunking_config()
            word_config = chunking_config["word"]
            chunk_size = _get_chunk_size_for_source(source_type)
            chunk_overlap = word_config["chunk_overlap"]

            chunks = split_text_by_characters(
                doc.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            num_chunks_word = len(chunks)

            # Get sentence chunks with SentenceSplitter (token-based)
            sentence_config = chunking_config["sentence"]
            sentence_parser = create_sentence_splitter(source_type=source_type)
            sent_nodes = sentence_parser.get_nodes_from_documents([doc])
            num_chunks_sentence = len(sent_nodes)

            # COMMENTED OUT: Character-based chunking (was used for testing)
            # sent_chunks = split_text_by_characters(
            #     doc.text,
            #     chunk_size=sentence_config["chunk_size"],
            #     chunk_overlap=sentence_config["chunk_overlap"],
            # )
            # num_chunks_sentence = len(sent_chunks)

            print("-" * 100)
            print(
                f"==> Number of sentence chunks: {num_chunks_sentence} "
                f"(token-based: {sentence_config['chunk_size']} tokens, "
                f"{sentence_config['chunk_overlap']} overlap)"
            )
            for i, node in enumerate(sent_nodes[: min(5, num_chunks_sentence)]):
                print("-" * 80)
                print(
                    f"  Chunk {i+1}: {len(node.text)} chars (~{len(node.text)/4:.0f} tokens)"
                )
                print(f"  Chunk {i+1} text: ==={node.text}===")
            if num_chunks_sentence > 5:
                print(f"  ... and {num_chunks_sentence - 5} more chunks")

            entry = create_manifest_entry(doc, num_chunks_word, num_chunks_sentence)
            manifest["sources"][source_id] = entry

    elif not new_docs and not changed_docs:
        # All sources unchanged - just load existing
        print(f"\nAll sources unchanged - loading existing indexes...")

        # For loading only, we need minimal embedding setup (but won't use it)
        if lazy_load_embeddings:
            # Align embedding model with stored metadata for verification
            from llama_index.core import Settings

            from config.llm_config import configure_embedding

            stored_metadata = load_embedding_metadata(persist_dir) or {}
            embedding_type = stored_metadata.get("embedding_type", "")
            embedding_model = stored_metadata.get("embedding_model")

            if embedding_type == "OpenAIEmbedding":
                Settings.embed_model = configure_embedding(
                    provider="openai", model=embedding_model
                )
            else:
                Settings.embed_model = configure_embedding(
                    provider="sentence-transformer", model=embedding_model
                )

            # Log the resolved embedding model for tracing
            resolved_model = (
                embedding_model if embedding_model else "default for provider"
            )
            print(
                f"  Configured embedding model: {embedding_type} "
                f"({resolved_model})",
                flush=True,
            )

        word_index, sentence_index = load_dual_indexes_in_memory(persist_dir)

    else:
        # Incremental update needed
        print(f"\nIncremental update: {len(new_docs)} new, {len(changed_docs)} changed")

        # Delete embeddings for changed sources
        for doc in changed_docs:
            source_id = doc.metadata.get("source_id")
            print(f"  Deleting old embeddings for {source_id}...")
            delete_source_from_indexes_in_memory(persist_dir, source_id)

        # Add new and changed documents
        docs_to_add = new_docs + changed_docs
        if docs_to_add:
            print(f"  Adding {len(docs_to_add)} documents to indexes...")
            num_word, num_sentence = add_documents_to_indexes_in_memory(
                docs_to_add, persist_dir
            )
            print(f"  ✓ Added {num_word} word chunks, {num_sentence} sentence chunks")

            # Update manifest for new and changed sources
            for doc in docs_to_add:
                source_id = doc.metadata.get("source_id")
                source_type = doc.metadata.get("source_type", "file")

                # Estimate chunk counts with source-type-aware chunking
                # Load word chunking config
                chunking_config = load_chunking_config()
                word_config = chunking_config["word"]
                chunk_size = _get_chunk_size_for_source(source_type)
                chunk_overlap = word_config["chunk_overlap"]

                chunks = split_text_by_characters(
                    doc.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
                num_chunks_word = len(chunks)

                # Get sentence chunks with SentenceSplitter (token-based)
                sentence_config = chunking_config["sentence"]
                sentence_parser = create_sentence_splitter(source_type=source_type)
                sent_nodes = sentence_parser.get_nodes_from_documents([doc])
                num_chunks_sentence = len(sent_nodes)

                # COMMENTED OUT: Character-based chunking (was used for testing)
                # sent_chunks = split_text_by_characters(
                #     doc.text,
                #     chunk_size=sentence_config["chunk_size"],
                #     chunk_overlap=sentence_config["chunk_overlap"],
                # )
                # num_chunks_sentence = len(sent_chunks)

                print("-" * 100)
                print(
                    f"==> Number of sentence chunks: {num_chunks_sentence} "
                    f"(token-based: {sentence_config['chunk_size']} tokens, "
                    f"{sentence_config['chunk_overlap']} overlap)"
                )
                for i, node in enumerate(sent_nodes[: min(5, num_chunks_sentence)]):
                    print("-" * 80)
                    print(
                        f"  Chunk {i+1}: {len(node.text)} chars (~{len(node.text)/4:.0f} tokens)"
                    )
                    print(f"  Chunk {i+1} text: ==={node.text}===")
                if num_chunks_sentence > 5:
                    print(f"  ... and {num_chunks_sentence - 5} more chunks")

                entry = create_manifest_entry(doc, num_chunks_word, num_chunks_sentence)
                manifest["sources"][source_id] = entry

        # Load the updated indexes
        word_index, sentence_index = load_dual_indexes_in_memory(persist_dir)

    # Save updated manifest
    save_manifest(persist_dir, manifest)

    print(f"\n✓ Dual indexes ready at {persist_dir}")
    return word_index, sentence_index


def build_multi_indexes_in_memory(
    config_path: Path | None = None,
    persist_dir: Path | None = None,
    index_subset: list[str] | None = None,
    force_rebuild: bool = False,
) -> dict[str, VectorStoreIndex]:
    """Build multiple indexes using the new multi-index system.

    Uses IndexFactory to build indexes defined in the configuration file.
    Supports subset selection and config-driven index definitions.

    Args:
        config_path: Path to YAML config file. If None, uses default location.
        persist_dir: Directory to persist indexes. If None, uses default location.
        index_subset: List of index IDs to build. If None, builds all active indexes.
        force_rebuild: If True, rebuild all indexes even if they exist.

    Returns:
        Dictionary mapping index ID to built VectorStoreIndex.

    """
    from grading_pipeline.config.index_schema import load_index_config
    from grading_pipeline.index_factory import IndexFactory

    # Use default paths if not provided
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "sources.yaml"
    if persist_dir is None:
        persist_dir = Path(__file__).parent / "persist"

    # Load and validate configuration
    print(f"Loading multi-index configuration from {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Load sources from configuration
    print(f"Loading sources from {config_path}")
    documents = load_sources_from_yaml_with_pdf(config_path)
    print(f"✓ Loaded {len(documents)} documents")

    if not documents:
        raise ValueError("No documents loaded from sources")

    # Create factory
    factory = IndexFactory(config, persist_dir)

    # Override active indexes if subset provided
    if index_subset:
        factory.set_active_indexes(index_subset)
        print(f"Using index subset: {index_subset}")

    # Build or update indexes
    print(f"\nBuilding indexes: {factory.get_active_index_ids()}")
    indexes = factory.build_or_update_active_indexes(
        documents, force_rebuild=force_rebuild
    )

    print(f"\n✓ Multi-indexes ready at {persist_dir}")
    return indexes


def load_multi_indexes_in_memory(
    config_path: Path | None = None,
    persist_dir: Path | None = None,
    index_subset: list[str] | None = None,
) -> dict[str, VectorStoreIndex]:
    """Load multiple indexes using the multi-index system.

    Args:
        config_path: Path to YAML config file. If None, uses default location.
        persist_dir: Directory containing persisted indexes. If None, uses default.
        index_subset: List of index IDs to load. If None, loads all active indexes.

    Returns:
        Dictionary mapping index ID to loaded VectorStoreIndex.

    """
    from grading_pipeline.index_factory import IndexFactory

    # Use default paths if not provided
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "sources.yaml"
    if persist_dir is None:
        persist_dir = Path(__file__).parent / "persist"

    # Load configuration
    print(f"Loading configuration from {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Create factory
    factory = IndexFactory(config, persist_dir)

    # Override active indexes if subset provided
    if index_subset:
        factory.set_active_indexes(index_subset)
        print(f"Loading index subset: {index_subset}")

    # Load indexes
    print(f"\nLoading indexes: {factory.get_active_index_ids()}")
    indexes = factory.load_active_indexes()

    print(f"\n✓ Indexes loaded from {persist_dir}")
    return indexes


if __name__ == "__main__":
    """CLI support for building indexes."""
    import argparse

    parser = argparse.ArgumentParser(description="Build multi-index grading pipeline")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to sources.yaml config file",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="Directory to persist indexes",
    )
    parser.add_argument(
        "--indexes",
        type=str,
        help="Comma-separated index IDs to build (e.g., 'word_index,sentence_index'). "
        "Use 'all' to build all enabled indexes.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild all indexes even if they exist",
    )

    args = parser.parse_args()

    # Set up embedding model before building
    print("[Setup] Initializing embedding model...")
    from config.llm_config import setup_llamaindex_defaults

    setup_llamaindex_defaults()
    print("✓ Embedding model loaded\n")

    # Build indexes
    index_subset = None
    if args.indexes:
        if args.indexes.lower() == "all":
            # Load config to get all enabled indexes
            if args.config is None:
                args.config = Path(__file__).parent / "config" / "sources.yaml"
            with open(args.config, "r") as f:
                config = yaml.safe_load(f)
            index_subset = [
                idx
                for idx, cfg in config.get("indexes", {}).items()
                if cfg.get("enabled", True)
            ]
            print(f"Building all enabled indexes: {index_subset}")
        else:
            index_subset = args.indexes.split(",")
            print(f"Building specified indexes: {index_subset}")

    try:
        indexes = build_multi_indexes_in_memory(
            config_path=args.config,
            persist_dir=args.persist_dir,
            index_subset=index_subset,
            force_rebuild=args.force_rebuild,
        )

        print(f"\n✓ Successfully built {len(indexes)} indexes")
        for idx_id in indexes.keys():
            print(f"  - {idx_id}")

    except Exception as e:
        print(f"\n✗ Error building indexes: {e}")
        raise


# Re-export for convenience
__all__ = [
    "InMemoryVectorStore",
    "load_chunking_config",
    "create_sentence_splitter",
    "build_word_index_in_memory",
    "build_sentence_index_in_memory",
    "build_or_update_dual_indexes_in_memory",
    "add_documents_to_indexes_in_memory",
    "delete_source_from_indexes_in_memory",
    "load_dual_indexes_in_memory",
    "load_sources_from_yaml_with_pdf",
    # New multi-index support
    "build_multi_indexes_in_memory",
    "load_multi_indexes_in_memory",
]
