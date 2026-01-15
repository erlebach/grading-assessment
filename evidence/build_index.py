"""Build the RAG evidence index from configured sources."""

from pathlib import Path
from typing import Any

import yaml


def load_index_config(config_path: Path) -> dict[str, Any]:
    """Load index configuration from YAML file.

    Args:
        config_path: Path to the index configuration YAML file.

    Returns:
        Dictionary containing index configuration.

    """
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def build_index(config_path: Path, output_path: Path) -> None:
    """Build the evidence index from configured sources.

    Args:
        config_path: Path to the index configuration YAML file.
        output_path: Path where the built index should be saved.

    """
    config = load_index_config(config_path)

    # TODO: Implement index building logic
    # - Load sources from configuration
    # - Chunk documents according to chunking strategy
    # - Generate embeddings
    # - Build index (vector store, BM25, etc.)
    # - Save index to output_path

    print(f"Building index from {config_path}")
    print(f"Index will be saved to {output_path}")
    print("Index building not yet implemented")


if __name__ == "__main__":
    config_path = Path(__file__).parent / "index_config.yaml"
    output_path = Path(__file__).parent / "index"
    build_index(config_path, output_path)
