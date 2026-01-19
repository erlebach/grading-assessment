"""Factory for creating and managing multiple indexes.

Orchestrates index creation, loading, and configuration management.
Provides a unified interface for working with multiple indexes while
supporting both config-driven and programmatic index selection.

"""

from pathlib import Path
from typing import Any

import yaml
from llama_index.core import Document, VectorStoreIndex

from grading_pipeline.config.index_schema import IndexesConfig, load_index_config
from grading_pipeline.index_registry import IndexRegistry
from grading_pipeline.manifest import (
    has_index_config_changed,
    load_manifest,
    save_manifest,
    update_index_config,
)


class IndexFactory:
    """Factory for creating and managing multiple indexes.

    Manages index creation, loading, and persistence across multiple index types.
    Supports configuration-driven index selection and runtime filtering.

    Attributes:
        config: Full configuration dictionary.
        persist_dir: Directory for persisting indexes.
        indexes_config: Validated index configurations.
        runtime_config: Runtime configuration for active indexes.
        _loaded_indexes: Cache of loaded indexes.

    """

    def __init__(self, config: dict[str, Any], persist_dir: Path):
        """Initialize the index factory.

        Args:
            config: Configuration dictionary (typically from YAML).
            persist_dir: Directory for persisting indexes.

        """
        self.config = config
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Parse and validate index configuration
        indexes_config = load_index_config(config)
        self.indexes_config = indexes_config.indexes
        self.runtime_config = indexes_config.runtime

        # Cache for loaded indexes
        self._loaded_indexes: dict[str, VectorStoreIndex] = {}

    def build_index(
        self,
        index_id: str,
        documents: list[Document],
        force_rebuild: bool = False,
    ) -> VectorStoreIndex:
        """Build a single index.

        Args:
            index_id: ID of the index to build (must be in indexes_config).
            documents: List of Document objects to index.
            force_rebuild: If True, rebuild even if index exists.

        Returns:
            Built VectorStoreIndex.

        Raises:
            ValueError: If index_id is unknown or disabled.

        """
        if index_id not in self.indexes_config:
            raise ValueError(
                f"Unknown index ID: {index_id}. "
                f"Available: {list(self.indexes_config.keys())}"
            )

        index_config = self.indexes_config[index_id]

        if not index_config.enabled:
            raise ValueError(f"Index {index_id} is disabled in configuration")

        # Get the builder for this index type
        builder = IndexRegistry.get_builder(index_config.type)

        # Convert config object to dict for builder
        config_dict = index_config.model_dump(exclude_none=True)

        # Build the index
        print(f"Building {index_config.type} index: {index_id}")
        index = builder.build(
            documents,
            self.persist_dir,
            index_config.collection_name,
            config_dict,
        )

        # Cache the loaded index
        self._loaded_indexes[index_id] = index

        # Update manifest with new build info
        manifest = load_manifest(self.persist_dir)
        update_index_config(manifest, index_id, config_dict)
        save_manifest(self.persist_dir, manifest)

        return index

    def load_index(self, index_id: str) -> VectorStoreIndex:
        """Load a previously built index.

        Args:
            index_id: ID of the index to load.

        Returns:
            Loaded VectorStoreIndex.

        Raises:
            ValueError: If index_id is unknown.
            FileNotFoundError: If index files not found.

        """
        if index_id not in self.indexes_config:
            raise ValueError(
                f"Unknown index ID: {index_id}. "
                f"Available: {list(self.indexes_config.keys())}"
            )

        # Return cached if already loaded
        if index_id in self._loaded_indexes:
            return self._loaded_indexes[index_id]

        index_config = self.indexes_config[index_id]

        # Get the builder for this index type
        builder = IndexRegistry.get_builder(index_config.type)

        # Convert config object to dict for builder
        config_dict = index_config.model_dump(exclude_none=True)

        # Load the index
        print(f"Loading {index_config.type} index: {index_id}")
        index = builder.load(
            self.persist_dir,
            index_config.collection_name,
            config_dict,
        )

        # Cache the loaded index
        self._loaded_indexes[index_id] = index

        return index

    def build_active_indexes(
        self,
        documents: list[Document],
        force_rebuild: bool = False,
    ) -> dict[str, VectorStoreIndex]:
        """Build all active indexes.

        Builds all indexes listed in runtime.active_indexes.

        Args:
            documents: List of Document objects to index.
            force_rebuild: If True, rebuild all indexes.

        Returns:
            Dictionary mapping index ID to built VectorStoreIndex.

        """
        indexes = {}
        for index_id in self.runtime_config.active_indexes:
            indexes[index_id] = self.build_index(
                index_id, documents, force_rebuild=force_rebuild
            )
        return indexes

    def build_or_update_active_indexes(
        self,
        documents: list[Document],
        force_rebuild: bool = False,
    ) -> dict[str, VectorStoreIndex]:
        """Build or update active indexes based on manifest.

        Checks manifest to determine if indexes need rebuild:
        - Rebuilds if config changed
        - Rebuilds if index files missing
        - Rebuilds if force_rebuild=True
        - Otherwise loads existing index

        Args:
            documents: List of Document objects to index.
            force_rebuild: If True, force rebuild all indexes.

        Returns:
            Dictionary mapping index ID to VectorStoreIndex (built or loaded).

        """
        manifest = load_manifest(self.persist_dir)
        indexes = {}

        for index_id in self.runtime_config.active_indexes:
            index_config = self.indexes_config[index_id]
            config_dict = index_config.model_dump(exclude_none=True)

            # Check if rebuild is needed
            needs_rebuild = (
                force_rebuild
                or has_index_config_changed(index_id, config_dict, manifest)
                or not self._index_files_exist(index_id)
            )

            if needs_rebuild:
                print(f"Rebuilding index: {index_id}")
                indexes[index_id] = self.build_index(
                    index_id, documents, force_rebuild=True
                )
            else:
                print(f"Loading existing index: {index_id}")
                indexes[index_id] = self.load_index(index_id)

        return indexes

    def load_active_indexes(self) -> dict[str, VectorStoreIndex]:
        """Load all active indexes.

        Loads all indexes listed in runtime.active_indexes.

        Returns:
            Dictionary mapping index ID to loaded VectorStoreIndex.

        Raises:
            FileNotFoundError: If any index files not found.

        """
        indexes = {}
        for index_id in self.runtime_config.active_indexes:
            indexes[index_id] = self.load_index(index_id)
        return indexes

    def set_active_indexes(self, index_ids: list[str]) -> None:
        """Override runtime active indexes.

        Useful for selecting a subset of indexes at runtime.

        Args:
            index_ids: List of index IDs to activate.

        Raises:
            ValueError: If any index_id is unknown.

        """
        # Validate all IDs exist
        unknown = set(index_ids) - set(self.indexes_config.keys())
        if unknown:
            raise ValueError(
                f"Unknown index IDs: {unknown}. "
                f"Available: {list(self.indexes_config.keys())}"
            )

        self.runtime_config.active_indexes = index_ids

    def _index_files_exist(self, index_id: str) -> bool:
        """Check if index files exist on disk.

        Args:
            index_id: ID of the index.

        Returns:
            True if index pickle file exists.

        """
        index_config = self.indexes_config[index_id]
        pickle_path = self.persist_dir / f"{index_config.collection_name}.pkl"
        return pickle_path.exists()

    def get_active_index_ids(self) -> list[str]:
        """Get list of active index IDs.

        Returns:
            List of currently active index IDs.

        """
        return self.runtime_config.active_indexes

    def get_index_config(self, index_id: str) -> dict[str, Any]:
        """Get configuration for a specific index.

        Args:
            index_id: ID of the index.

        Returns:
            Configuration dictionary for the index.

        Raises:
            ValueError: If index_id is unknown.

        """
        if index_id not in self.indexes_config:
            raise ValueError(
                f"Unknown index ID: {index_id}. "
                f"Available: {list(self.indexes_config.keys())}"
            )

        return self.indexes_config[index_id].model_dump(exclude_none=True)
