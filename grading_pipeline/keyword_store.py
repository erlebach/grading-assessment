"""Keyword storage per chunk.

Stores keywords extracted from chunks in a separate file to avoid
metadata size issues. Maps chunk_id -> list of keywords.

"""

import json
from pathlib import Path
from typing import Any


def load_keyword_store(keyword_store_path: Path) -> dict[str, list[str]]:
    """Load keyword store from file.

    Args:
        keyword_store_path: Path to keyword store JSON file.

    Returns:
        Dictionary mapping chunk_id to list of keywords.

    """
    if not keyword_store_path.exists():
        return {}

    with open(keyword_store_path, "r") as f:
        return json.load(f)


def save_keyword_store(
    keyword_store: dict[str, list[str]], keyword_store_path: Path
) -> None:
    """Save keyword store to file.

    Args:
        keyword_store: Dictionary mapping chunk_id to list of keywords.
        keyword_store_path: Path to keyword store JSON file.

    """
    keyword_store_path.parent.mkdir(parents=True, exist_ok=True)

    with open(keyword_store_path, "w") as f:
        json.dump(keyword_store, f, indent=2)


def add_chunk_keywords(
    chunk_id: str,
    keywords: list[str],
    keyword_store_path: Path,
) -> None:
    """Add keywords for a chunk to the store.

    Args:
        chunk_id: Unique identifier for the chunk.
        keywords: List of keywords extracted from the chunk.
        keyword_store_path: Path to keyword store JSON file.

    """
    store = load_keyword_store(keyword_store_path)
    store[chunk_id] = keywords
    save_keyword_store(store, keyword_store_path)


def get_chunk_keywords(
    chunk_id: str, keyword_store_path: Path
) -> list[str]:
    """Get keywords for a chunk from the store.

    Args:
        chunk_id: Unique identifier for the chunk.
        keyword_store_path: Path to keyword store JSON file.

    Returns:
        List of keywords for the chunk, or empty list if not found.

    """
    store = load_keyword_store(keyword_store_path)
    return store.get(chunk_id, [])
