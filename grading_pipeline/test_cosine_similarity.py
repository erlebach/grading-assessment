#!/usr/bin/env python3
"""Simple test to retrieve a random chunk and show top-5 similarity scores.

This script:
1. Chooses a random chunk from the word index (sentence indexing with hard limit)
2. Performs top-5 retrieval using that chunk
3. Prints the 5 similarity scores

Supports both ChromaDB and in-memory database backends.
"""

import argparse
import random
from pathlib import Path

import chromadb
import numpy as np
import yaml
from llama_index.core import Settings

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder import load_dual_indexes
from grading_pipeline.index_builder_in_memory import load_dual_indexes_in_memory


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity between a and b.

    """
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b)
    return float(np.dot(a_norm, b_norm))


def print_embedding_side_by_side(
    stored_embedding: np.ndarray,
    new_embedding: np.ndarray,
    max_items: int = 20,
) -> None:
    """Print stored vs new embeddings and cosine similarity.

    Args:
        stored_embedding: Stored embedding vector from the index.
        new_embedding: Newly computed embedding vector from the same text.
        max_items: Number of leading entries to print.

    """
    limit = min(max_items, len(stored_embedding), len(new_embedding))
    print("Embedding entries (stored vs new, first values):")
    print(f"{'idx':>5} | {'stored':>12} | {'new':>12} | {'diff':>12}")
    print("-" * 50)
    for idx in range(limit):
        stored_val = float(stored_embedding[idx])
        new_val = float(new_embedding[idx])
        diff_val = stored_val - new_val
        print(
            f"{idx:5d} | {stored_val:12.5g} | {new_val:12.5g} | {diff_val:12.5g}"
        )

    cosine_sim = _cosine_similarity(stored_embedding, new_embedding)
    print("-" * 50)
    print(f"Cosine similarity (stored vs new): {cosine_sim:.6f}")


def load_debug_config(config_path: Path) -> bool:
    """Load debug flag from YAML config.

    Args:
        config_path: Path to sources.yaml.

    Returns:
        True if embedding diagnostics are enabled, False otherwise.

    """
    if not config_path.exists():
        return False

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    debug_config = config.get("debug", {})
    return bool(debug_config.get("embedding_diagnostics", False))


def run_embedding_diagnostics(
    stored_embedding: np.ndarray,
    random_chunk: str,
    embed_model: object,
) -> None:
    """Run embedding diagnostics for stored vs computed embeddings.

    Args:
        stored_embedding: Embedding stored in the in-memory index.
        random_chunk: Text used for re-embedding.
        embed_model: Embedding model used for re-embedding.

    """
    new_embedding = np.array(
        embed_model.get_text_embedding(random_chunk), dtype=np.float32
    )
    second_embedding = np.array(
        embed_model.get_text_embedding(random_chunk), dtype=np.float32
    )
    query_embedding = np.array(
        embed_model.get_query_embedding(random_chunk), dtype=np.float32
    )

    cosine_sim = _cosine_similarity(stored_embedding, new_embedding)
    repeat_sim = _cosine_similarity(new_embedding, second_embedding)
    query_sim = _cosine_similarity(new_embedding, query_embedding)

    print(f"Embedding consistency check:")
    print(f"  Stored embedding norm: {np.linalg.norm(stored_embedding):.6f}")
    print(f"  New embedding norm: {np.linalg.norm(new_embedding):.6f}")
    print(f"  Query embedding norm: {np.linalg.norm(query_embedding):.6f}")
    print(f"  Stored vs new cosine similarity: {cosine_sim:.6f}")
    print(f"  New vs new cosine similarity: {repeat_sim:.6f}")
    print(f"  Text vs query cosine similarity: {query_sim:.6f}")
    print(f"  Chunk text repr: {random_chunk!r}")
    if cosine_sim < 0.9:
        print(
            f"  ⚠ WARNING: Embeddings differ! This explains low retrieval scores."
        )
    print()
    print_embedding_side_by_side(stored_embedding, new_embedding)
    print()


def get_random_chunk_chromadb(persist_dir: Path) -> tuple[str, str]:
    """Get a random chunk from ChromaDB.

    Args:
        persist_dir: Directory containing ChromaDB.

    Returns:
        Tuple of (chunk_id, chunk_text).

    """
    print("Selecting random chunk from word_index (ChromaDB)...")
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    collection = chroma_client.get_collection("word_index")

    # Get all document IDs
    results = collection.get(include=["documents"])
    all_docs = results.get("documents", [])
    all_ids = results.get("ids", [])

    if not all_docs:
        raise ValueError("No documents found in word_index")

    # Select random chunk
    random_idx = random.randint(0, len(all_docs) - 1)
    random_chunk = all_docs[random_idx]
    random_id = all_ids[random_idx]

    return random_id, random_chunk


def get_random_chunk_in_memory(word_index) -> tuple[str, str]:
    """Get a random chunk from in-memory database.

    Args:
        word_index: VectorStoreIndex with in-memory vector store.

    Returns:
        Tuple of (chunk_id, chunk_text).

    """
    print("Selecting random chunk from word_index (in-memory)...")
    vector_store = word_index._storage_context.vector_store

    # Get all nodes
    all_nodes = list(vector_store.nodes.values())
    if not all_nodes:
        raise ValueError("No documents found in word_index")

    # Select random node
    random_node = random.choice(all_nodes)
    random_id = random_node.node_id
    random_chunk = random_node.text

    return random_id, random_chunk


def main() -> None:
    """Test cosine similarity with random chunk retrieval."""
    parser = argparse.ArgumentParser(
        description="Test cosine similarity using ChromaDB or in-memory database",
        epilog="""
Examples:
  %(prog)s                              # Use ChromaDB (default)
  %(prog)s --db chromadb                # Explicitly use ChromaDB
  %(prog)s --db in-memory               # Use in-memory database
  %(prog)s --db chromadb --persist-dir /custom/path  # Custom ChromaDB directory
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        choices=["chromadb", "in-memory"],
        default="chromadb",
        metavar="DATABASE",
        help="Database backend to use. Choices: chromadb, in-memory (default: chromadb)",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Directory containing the indexes. Defaults to tmp/chroma_db for chromadb, tmp/in_memory_indexes for in-memory",
    )
    args = parser.parse_args()

    # Set default persist directory based on database type
    if args.persist_dir is None:
        if args.db == "chromadb":
            persist_dir = Path(__file__).parent / "tmp" / "chroma_db"
        else:
            persist_dir = Path(__file__).parent / "tmp" / "in_memory_indexes"
    else:
        persist_dir = args.persist_dir

    print(f"Using {args.db} database at {persist_dir}\n")

    # Load indexes
    print("Loading indexes...")
    setup_llamaindex_defaults()

    if args.db == "chromadb":
        word_index, _ = load_dual_indexes(persist_dir)
    else:
        word_index, _ = load_dual_indexes_in_memory(persist_dir)

    print("✓ Indexes loaded\n")

    # Check embedding model consistency
    embed_model = Settings.embed_model
    print(f"Current embedding model: {type(embed_model).__name__}")
    if hasattr(embed_model, "model_name"):
        print(f"Model name: {embed_model.model_name}")
    print()

    # Get a random chunk
    try:
        if args.db == "chromadb":
            random_id, random_chunk = get_random_chunk_chromadb(persist_dir)
        else:
            random_id, random_chunk = get_random_chunk_in_memory(word_index)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print(f"Selected chunk ID: {random_id}")
    print(f"Chunk length: {len(random_chunk)} characters")
    print(f"Chunk text (first 100 chars): {random_chunk[:100]}...\n")

    # For in-memory, check if re-embedding produces same result
    if args.db == "in-memory":
        config_path = Path(__file__).parent / "config" / "sources.yaml"
        if load_debug_config(config_path):
            vector_store = word_index._storage_context.vector_store
            stored_embedding = vector_store.embeddings[random_id]
            run_embedding_diagnostics(
                stored_embedding=stored_embedding,
                random_chunk=random_chunk,
                embed_model=embed_model,
            )

    # Perform top-5 retrieval
    print("Performing top-5 retrieval...")
    retriever = word_index.as_retriever(similarity_top_k=5)
    nodes = retriever.retrieve(random_chunk)

    # Print the 5 scores
    print(f"\nTop-5 Similarity Scores ({args.db}):")
    print("=" * 60)
    for rank, node in enumerate(nodes, 1):
        is_self = "← SELF MATCH" if node.node_id == random_id else ""
        print(f"{rank}. Score: {node.score:.6f} (ID: {node.node_id[:8]}...) {is_self}")
    print("=" * 60)

    # Check if self-match is in top 5
    self_match_found = any(node.node_id == random_id for node in nodes)
    if self_match_found:
        self_rank = next(
            i for i, node in enumerate(nodes, 1) if node.node_id == random_id
        )
        self_score = next(node.score for node in nodes if node.node_id == random_id)
        print(f"\n✓ Self-match found at rank {self_rank} with score {self_score:.6f}")
    else:
        print(f"\n⚠ Warning: Self-match NOT found in top-5 results!")


if __name__ == "__main__":
    main()
