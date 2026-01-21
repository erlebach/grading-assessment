"""Registry for index builders with extensible architecture.

This module defines the IndexBuilder protocol and provides concrete implementations
for different index types (character, sentence, paragraph). New index types can be
registered by implementing the IndexBuilder protocol.

"""

from pathlib import Path
from typing import Any, Protocol

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from grading_pipeline.index_builder_in_memory import InMemoryVectorStore
from retrieval_core.index_builder import split_text_by_characters


class IndexBuilder(Protocol):
    """Protocol defining the interface for index builders.

    Any class implementing this protocol can be registered with IndexRegistry
    and used to build indexes of that type.

    """

    def build(
        self,
        documents: list[Document],
        persist_dir: Path,
        collection_name: str,
        config: dict[str, Any],
    ) -> VectorStoreIndex:
        """Build an index from documents.

        Args:
            documents: List of LlamaIndex Document objects.
            persist_dir: Directory to persist the index.
            collection_name: Name of the collection for this index.
            config: Configuration dict for this index type.

        Returns:
            Built VectorStoreIndex instance.

        """
        ...

    def load(
        self, persist_dir: Path, collection_name: str, config: dict[str, Any]
    ) -> VectorStoreIndex:
        """Load a previously built index from persistence.

        Args:
            persist_dir: Directory containing persisted index.
            collection_name: Name of the collection.
            config: Configuration dict for this index type.

        Returns:
            Loaded VectorStoreIndex instance.

        """
        ...


class CharacterIndexBuilder:
    """Builder for character-based chunking indexes.

    Uses character-level splitting with configurable chunk size and overlap.
    Suitable for shorter, more granular chunks.

    """

    def build(
        self,
        documents: list[Document],
        persist_dir: Path,
        collection_name: str,
        config: dict[str, Any],
    ) -> VectorStoreIndex:
        """Build character-based index."""
        chunk_size = config.get("chunk_size", 512)
        chunk_overlap = config.get("chunk_overlap", 50)

        # Create in-memory vector store
        vector_store = InMemoryVectorStore()

        # Chunk documents by characters
        nodes = []
        for doc in documents:
            # Get per-source-type chunk size override if available
            source_type = doc.metadata.get("source_type", "default")
            source_overrides = config.get("source_type_overrides", {})
            actual_chunk_size = source_overrides.get(source_type, chunk_size)

            # Split by characters
            chunks = split_text_by_characters(
                doc.text, actual_chunk_size, chunk_overlap
            )
            for chunk in chunks:
                node = TextNode(
                    text=chunk,
                    metadata=doc.metadata,
                    excluded_embed_metadata_keys=list(doc.metadata.keys()),
                )
                nodes.append(node)

        # Validate that we have nodes before building
        if not nodes:
            raise RuntimeError(
                f"Cannot build {collection_name}: no nodes created from documents.\n"
                f"  This indicates documents were empty or chunking produced no chunks.\n"
                f"  Documents provided: {len(documents)}\n"
                f"  This prevents downstream execution."
            )

        # Build index from nodes using StorageContext (required for proper store population)
        from llama_index.core import StorageContext

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            show_progress=True,
        )

        # Get the actual store from the index's storage context (it may be different)
        actual_store = index._storage_context.vector_store
        if not isinstance(actual_store, InMemoryVectorStore):
            raise RuntimeError(
                f"Cannot persist {collection_name}: expected InMemoryVectorStore, "
                f"got {type(actual_store).__name__}"
            )

        # Validate store has content before persisting
        if len(actual_store.nodes) == 0:
            raise RuntimeError(
                f"Cannot persist {collection_name}: vector store is empty after building.\n"
                f"  This indicates a critical error in the build process.\n"
                f"  Nodes created: {len(nodes)}, but store has {len(actual_store.nodes)} nodes.\n"
                f"  This prevents downstream execution."
            )

        # Persist vector store
        persist_dir.mkdir(parents=True, exist_ok=True)
        pickle_path = persist_dir / f"{collection_name}.pkl"
        actual_store.save_to_pickle(pickle_path)

        return index

    def load(
        self, persist_dir: Path, collection_name: str, config: dict[str, Any]
    ) -> VectorStoreIndex:
        """Load character-based index from pickle."""
        pickle_path = persist_dir / f"{collection_name}.pkl"

        if not pickle_path.exists():
            raise FileNotFoundError(f"Index not found at {pickle_path}")

        # Load vector store from pickle
        vector_store = InMemoryVectorStore.load_from_pickle(pickle_path)

        # Create index from loaded vector store (use from_vector_store for proper connection)
        index = VectorStoreIndex.from_vector_store(vector_store)

        return index


class SentenceIndexBuilder:
    """Builder for sentence-based chunking indexes.

    Uses sentence splitting with token-based measurement and configurable overlap.
    Suitable for semantic chunks at the sentence level.

    """

    def build(
        self,
        documents: list[Document],
        persist_dir: Path,
        collection_name: str,
        config: dict[str, Any],
    ) -> VectorStoreIndex:
        """Build sentence-based index."""
        chunk_size = config.get("chunk_size", 256)  # in tokens
        chunk_overlap = config.get("chunk_overlap", 50)

        # Create in-memory vector store
        vector_store = InMemoryVectorStore()

        # Create sentence splitter
        splitter_config = {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }

        # Add secondary chunking regex if provided
        if "secondary_chunking_regex_default" in config:
            splitter_config["secondary_chunking_regex"] = config[
                "secondary_chunking_regex_default"
            ]

        splitter = SentenceSplitter(**splitter_config)

        # Validate documents before building
        if not documents:
            raise RuntimeError(
                f"Cannot build {collection_name}: no documents provided.\n"
                f"  This prevents downstream execution."
            )

        # Build index from documents with sentence splitter
        from llama_index.core import StorageContext

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(
            documents,
            transformations=[splitter],
            storage_context=storage_context,
            show_progress=True,
        )

        # Get the actual store from the index's storage context
        actual_store = index._storage_context.vector_store
        if not isinstance(actual_store, InMemoryVectorStore):
            raise RuntimeError(
                f"Cannot persist {collection_name}: expected InMemoryVectorStore, "
                f"got {type(actual_store).__name__}"
            )

        # Validate store has content before persisting
        if len(actual_store.nodes) == 0:
            raise RuntimeError(
                f"Cannot persist {collection_name}: vector store is empty after building.\n"
                f"  This indicates documents were empty or chunking produced no chunks.\n"
                f"  Documents provided: {len(documents)}, but store has {len(actual_store.nodes)} nodes.\n"
                f"  This prevents downstream execution."
            )

        # Persist vector store
        persist_dir.mkdir(parents=True, exist_ok=True)
        pickle_path = persist_dir / f"{collection_name}.pkl"
        actual_store.save_to_pickle(pickle_path)

        return index

    def load(
        self, persist_dir: Path, collection_name: str, config: dict[str, Any]
    ) -> VectorStoreIndex:
        """Load sentence-based index from pickle."""
        pickle_path = persist_dir / f"{collection_name}.pkl"

        if not pickle_path.exists():
            raise FileNotFoundError(f"Index not found at {pickle_path}")

        # Load vector store from pickle
        vector_store = InMemoryVectorStore.load_from_pickle(pickle_path)

        # Create index from loaded vector store (use from_vector_store for proper connection)
        index = VectorStoreIndex.from_vector_store(vector_store)

        return index


class ParagraphIndexBuilder:
    """Builder for paragraph-based chunking indexes.

    Uses paragraph-level splitting for coarser, more coherent chunks.
    Suitable for longer context windows and cohesive semantic units.

    """

    def build(
        self,
        documents: list[Document],
        persist_dir: Path,
        collection_name: str,
        config: dict[str, Any],
    ) -> VectorStoreIndex:
        """Build paragraph-based index."""
        chunk_size = config.get("chunk_size", 1024)  # in tokens
        chunk_overlap = config.get("chunk_overlap", 100)
        paragraph_separator = config.get("paragraph_separator", "\n\n")

        # Create in-memory vector store
        vector_store = InMemoryVectorStore()

        # Create sentence splitter configured for paragraphs
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=paragraph_separator,
        )

        # Validate documents before building
        if not documents:
            raise RuntimeError(
                f"Cannot build {collection_name}: no documents provided.\n"
                f"  This prevents downstream execution."
            )

        # Build index from documents with paragraph splitter
        from llama_index.core import StorageContext

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(
            documents,
            transformations=[splitter],
            storage_context=storage_context,
            show_progress=True,
        )

        # Get the actual store from the index's storage context
        actual_store = index._storage_context.vector_store
        if not isinstance(actual_store, InMemoryVectorStore):
            raise RuntimeError(
                f"Cannot persist {collection_name}: expected InMemoryVectorStore, "
                f"got {type(actual_store).__name__}"
            )

        # Validate store has content before persisting
        if len(actual_store.nodes) == 0:
            raise RuntimeError(
                f"Cannot persist {collection_name}: vector store is empty after building.\n"
                f"  This indicates documents were empty or chunking produced no chunks.\n"
                f"  Documents provided: {len(documents)}, but store has {len(actual_store.nodes)} nodes.\n"
                f"  This prevents downstream execution."
            )

        # Persist vector store
        persist_dir.mkdir(parents=True, exist_ok=True)
        pickle_path = persist_dir / f"{collection_name}.pkl"
        actual_store.save_to_pickle(pickle_path)

        return index

    def load(
        self, persist_dir: Path, collection_name: str, config: dict[str, Any]
    ) -> VectorStoreIndex:
        """Load paragraph-based index from pickle."""
        pickle_path = persist_dir / f"{collection_name}.pkl"

        if not pickle_path.exists():
            raise FileNotFoundError(f"Index not found at {pickle_path}")

        # Load vector store from pickle
        vector_store = InMemoryVectorStore.load_from_pickle(pickle_path)

        # Create index from loaded vector store (use from_vector_store for proper connection)
        index = VectorStoreIndex.from_vector_store(vector_store)

        return index


class IndexRegistry:
    """Registry for mapping index types to their builders.

    Maintains a global registry of index type -> builder mappings.
    Allows runtime registration of new index types.

    """

    _builders: dict[str, IndexBuilder] = {}

    @classmethod
    def register(cls, index_type: str, builder: IndexBuilder) -> None:
        """Register a builder for an index type.

        Args:
            index_type: String identifier for the index type (e.g., 'character').
            builder: IndexBuilder implementation for this type.

        """
        cls._builders[index_type] = builder

    @classmethod
    def get_builder(cls, index_type: str) -> IndexBuilder:
        """Get the builder for an index type.

        Args:
            index_type: String identifier for the index type.

        Returns:
            IndexBuilder instance for this type.

        Raises:
            ValueError: If the index type is not registered.

        """
        if index_type not in cls._builders:
            raise ValueError(
                f"Unknown index type: {index_type}. Registered types: {list(cls._builders.keys())}"
            )
        return cls._builders[index_type]

    @classmethod
    def list_types(cls) -> list[str]:
        """Get list of all registered index types.

        Returns:
            List of registered type identifiers.

        """
        return list(cls._builders.keys())


# Register default builders
IndexRegistry.register("character", CharacterIndexBuilder())
IndexRegistry.register("sentence", SentenceIndexBuilder())
IndexRegistry.register("paragraph", ParagraphIndexBuilder())
