#!/usr/bin/env python3
"""Check if embedding model produces same embeddings for same text."""

import random
from pathlib import Path

import numpy as np
from llama_index.core import Settings

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder_in_memory import load_dual_indexes_in_memory


def main() -> None:
    """Check embedding model consistency."""
    persist_dir = Path(__file__).parent / "tmp" / "in_memory_indexes"

    print("Loading indexes...")
    setup_llamaindex_defaults()
    word_index, _ = load_dual_indexes_in_memory(persist_dir)
    print("✓ Indexes loaded\n")

    # Get embedding model
    embed_model = Settings.embed_model
    print(f"Embedding model: {type(embed_model).__name__}")
    if hasattr(embed_model, "model_name"):
        print(f"Model name: {embed_model.model_name}")
    print()

    # Get a random chunk
    vector_store = word_index._storage_context.vector_store
    all_nodes = list(vector_store.nodes.values())
    if not all_nodes:
        print("Error: No nodes found")
        return

    random_node = random.choice(all_nodes)
    random_id = random_node.node_id
    random_text = random_node.text
    stored_embedding = vector_store.embeddings[random_id]

    print(f"Selected chunk ID: {random_id}")
    print(f"Chunk text (first 100 chars): {random_text[:100]}...")
    print(f"Stored embedding shape: {stored_embedding.shape}")
    print(f"Stored embedding norm: {np.linalg.norm(stored_embedding):.6f}\n")

    # Re-embed the same text
    print("Re-embedding the same text...")
    new_embedding = embed_model.get_text_embedding(random_text)
    new_embedding = np.array(new_embedding, dtype=np.float32)

    print(f"New embedding shape: {new_embedding.shape}")
    print(f"New embedding norm: {np.linalg.norm(new_embedding):.6f}\n")

    # Compare embeddings
    stored_norm = stored_embedding / np.linalg.norm(stored_embedding)
    new_norm = new_embedding / np.linalg.norm(new_embedding)

    cosine_sim = float(np.dot(stored_norm, new_norm))
    diff = np.abs(stored_embedding - new_embedding)
    max_diff = float(np.max(diff))
    mean_diff = float(np.mean(diff))

    print("=" * 60)
    print("Embedding Comparison:")
    print("=" * 60)
    print(f"Cosine similarity: {cosine_sim:.10f}")
    print(f"Max difference: {max_diff:.10f}")
    print(f"Mean difference: {mean_diff:.10f}")
    print()

    if cosine_sim > 0.99:
        print("✓✓ Embeddings are nearly identical (cosine similarity > 0.99)")
        print("  The embedding model is producing consistent results.")
    elif cosine_sim > 0.9:
        print("⚠ Embeddings are similar but not identical (cosine similarity > 0.9)")
        print("  There may be slight variations in the embedding model.")
    else:
        print("✗ Embeddings are different (cosine similarity < 0.9)")
        print("  The embedding model may not be deterministic or may have changed.")


if __name__ == "__main__":
    main()
