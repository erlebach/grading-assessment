#!/usr/bin/env python3
"""Debug script to check if self-match works correctly."""

import numpy as np
from pathlib import Path
import random

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder_in_memory import load_dual_indexes_in_memory


def main() -> None:
    """Debug cosine similarity with self-match."""
    persist_dir = Path(__file__).parent / "tmp" / "in_memory_indexes"
    
    print("Loading in-memory indexes...")
    setup_llamaindex_defaults()
    word_index, _ = load_dual_indexes_in_memory(persist_dir)
    print("✓ Indexes loaded\n")
    
    # Get vector store
    vector_store = word_index._storage_context.vector_store
    
    # Pick a random node
    all_node_ids = list(vector_store.nodes.keys())
    random_id = random.choice(all_node_ids)
    random_node = vector_store.nodes[random_id]
    random_embedding = vector_store.embeddings[random_id]
    
    print(f"Selected node ID: {random_id}")
    print(f"Node text: {random_node.text[:100]}...")
    print(f"Embedding shape: {random_embedding.shape}")
    print(f"Embedding norm: {np.linalg.norm(random_embedding):.6f}\n")
    
    # Compute cosine similarity between this embedding and itself
    norm = np.linalg.norm(random_embedding)
    normalized = random_embedding / norm
    self_similarity = float(np.dot(normalized, normalized))
    print(f"Self-similarity (stored embedding vs itself): {self_similarity:.10f}\n")
    
    # Now use the text to create a NEW embedding via retrieval
    print("Creating new embedding via retrieval...")
    retriever = word_index.as_retriever(similarity_top_k=10)
    nodes = retriever.retrieve(random_node.text)
    
    print(f"\nTop-10 retrieval results:")
    print("=" * 80)
    for rank, node in enumerate(nodes, 1):
        is_self = "← SELF MATCH" if node.node_id == random_id else ""
        print(f"{rank}. Score: {node.score:.6f} (ID: {node.node_id[:8]}...) {is_self}")
    print("=" * 80)
    
    # Check if self-match is found
    self_match_found = any(node.node_id == random_id for node in nodes)
    if self_match_found:
        self_rank = next(i for i, node in enumerate(nodes, 1) if node.node_id == random_id)
        self_score = next(node.score for node in nodes if node.node_id == random_id)
        print(f"\n✓ Self-match found at rank {self_rank} with score {self_score:.6f}")
    else:
        print(f"\n⚠ WARNING: Self-match NOT found in top-10!")
        print(f"\nThis suggests the embeddings are not being computed consistently.")


if __name__ == "__main__":
    main()
