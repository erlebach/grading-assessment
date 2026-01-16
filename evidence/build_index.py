"""Build the RAG evidence index from configured sources."""

import pickle
from pathlib import Path
from typing import Any

import yaml
from llama_index.core import VectorStoreIndex

from config.llm_config import setup_llamaindex_defaults
from evidence.index_builder import (
    build_index_with_metadata,
    load_documents_from_files_with_metadata,
)


def load_index_config(config_path: Path) -> dict[str, Any]:
    """Load index configuration from YAML file.

    Args:
        config_path: Path to the index configuration YAML file.

    Returns:
        Dictionary containing index configuration.

    """
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def build_index(config_path: Path, output_path: Path) -> VectorStoreIndex:
    """Build the evidence index from configured sources.

    Args:
        config_path: Path to the index configuration YAML file.
        output_path: Path where the built index should be saved.

    Returns:
        Built VectorStoreIndex.

    """
    config = load_index_config(config_path)

    # Setup LlamaIndex with default configuration
    setup_llamaindex_defaults()

    # Get configuration
    index_config = config.get("index_config", {})
    chunking_config = index_config.get("chunking", {})
    sources_config = index_config.get("sources", [])

    chunk_size = chunking_config.get("chunk_size", 512)
    chunk_overlap = chunking_config.get("chunk_overlap", 50)

    print(f"Building index from {config_path}")
    print(f"Chunk size: {chunk_size}, overlap: {chunk_overlap}")

    # Load documents from sources
    all_documents = []

    for source in sources_config:
        source_type = source.get("type")

        if source_type == "file":
            # Load files from directory
            source_path = Path(source.get("path", ""))
            if source_path.exists():
                patterns = source.get("patterns", ["*.txt", "*.md", "*.py"])
                file_paths = []

                for pattern in patterns:
                    file_paths.extend(source_path.glob(f"**/{pattern}"))

                if file_paths:
                    print(f"Loading {len(file_paths)} files from {source_path}")
                    documents = load_documents_from_files_with_metadata(file_paths)
                    all_documents.extend(documents)
            else:
                print(f"Warning: Source path {source_path} does not exist")

        elif source_type == "documentation":
            # For documentation URLs, we would need to fetch and process
            # For now, just log that it's not implemented
            print(f"Warning: Documentation sources not yet implemented")

    if not all_documents:
        print("Warning: No documents found. Creating empty index.")

    print(f"Total documents loaded: {len(all_documents)}")

    # Build index with metadata
    print("Building vector index...")
    index = build_index_with_metadata(
        all_documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    # Save index
    output_path.mkdir(parents=True, exist_ok=True)
    index_file = output_path / "vector_index.pkl"

    print(f"Saving index to {index_file}")
    with open(index_file, "wb") as f:
        pickle.dump(index, f)

    print("✓ Index built and saved successfully")

    return index


def load_saved_index(index_path: Path) -> VectorStoreIndex | None:
    """Load a previously saved index.

    Args:
        index_path: Path to the saved index file.

    Returns:
        Loaded VectorStoreIndex or None if not found.

    """
    index_file = index_path / "vector_index.pkl"

    if not index_file.exists():
        return None

    with open(index_file, "rb") as f:
        index = pickle.load(f)

    return index


if __name__ == "__main__":
    config_path = Path(__file__).parent / "index_config.yaml"
    output_path = Path(__file__).parent / "index"
    build_index(config_path, output_path)
