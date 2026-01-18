#!/usr/bin/env python3
"""Investigate why re-embedded text has cosine similarity ~0.74 with stored embedding."""

import random
from pathlib import Path

import numpy as np
from llama_index.core import Settings

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder_in_memory import load_dual_indexes_in_memory


def main() -> None:
    """Investigate embedding differences."""
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
    print(f"Chunk text length: {len(random_text)} characters")
    print(f"Chunk text (first 200 chars): {random_text[:200]}")
    print(f"Chunk text (last 200 chars): {random_text[-200:]}")
    print()
    print(f"Stored embedding shape: {stored_embedding.shape}")
    print(f"Stored embedding dtype: {stored_embedding.dtype}")
    print(f"Stored embedding norm: {np.linalg.norm(stored_embedding):.10f}")
    print(f"Stored embedding min: {np.min(stored_embedding):.6f}")
    print(f"Stored embedding max: {np.max(stored_embedding):.6f}")
    print(f"Stored embedding mean: {np.mean(stored_embedding):.6f}")
    print(f"Stored embedding std: {np.std(stored_embedding):.6f}")
    print()

    # Re-embed the same text multiple times to check consistency
    print("Re-embedding the same text (multiple times to check consistency)...")
    embeddings = []
    for i in range(3):
        new_embedding = embed_model.get_text_embedding(random_text)
        new_embedding = np.array(new_embedding, dtype=np.float32)
        embeddings.append(new_embedding)
        print(f"  Run {i+1}: shape={new_embedding.shape}, norm={np.linalg.norm(new_embedding):.10f}")

    # Check consistency between re-embeddings
    if len(embeddings) > 1:
        norm1 = embeddings[0] / np.linalg.norm(embeddings[0])
        norm2 = embeddings[1] / np.linalg.norm(embeddings[1])
        consistency = float(np.dot(norm1, norm2))
        print(f"  Consistency between runs 1 and 2: {consistency:.10f}")
        if consistency < 0.99:
            print("  ⚠ WARNING: Embeddings are NOT consistent between runs!")

    new_embedding = embeddings[0]
    print()

    # Compare stored vs new embedding
    stored_norm = stored_embedding / np.linalg.norm(stored_embedding)
    new_norm = new_embedding / np.linalg.norm(new_embedding)

    cosine_sim = float(np.dot(stored_norm, new_norm))
    diff = np.abs(stored_embedding - new_embedding)
    max_diff = float(np.max(diff))
    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff))

    # Element-wise comparison
    abs_diff = np.abs(stored_embedding - new_embedding)
    num_different = np.sum(abs_diff > 1e-6)
    max_abs_diff = float(np.max(abs_diff))

    print("=" * 80)
    print("Embedding Comparison (Stored vs Re-embedded):")
    print("=" * 80)
    print(f"Cosine similarity (normalized): {cosine_sim:.10f}")
    print(f"Max absolute difference: {max_abs_diff:.10f}")
    print(f"Mean absolute difference: {mean_diff:.10f}")
    print(f"Std absolute difference: {std_diff:.10f}")
    print(f"Number of dimensions with diff > 1e-6: {num_different} / {len(stored_embedding)}")
    print()

    # Check if stored embedding is already normalized
    stored_raw_norm = np.linalg.norm(stored_embedding)
    new_raw_norm = np.linalg.norm(new_embedding)
    print(f"Raw norms: stored={stored_raw_norm:.10f}, new={new_raw_norm:.10f}")
    if abs(stored_raw_norm - 1.0) < 1e-6:
        print("  → Stored embedding is already normalized (norm ≈ 1.0)")
    if abs(new_raw_norm - 1.0) < 1e-6:
        print("  → New embedding is already normalized (norm ≈ 1.0)")

    # Check if the issue is normalization
    if abs(stored_raw_norm - 1.0) < 1e-6 and abs(new_raw_norm - 1.0) < 1e-6:
        # Both are normalized, compare directly
        direct_sim = float(np.dot(stored_embedding, new_embedding))
        print(f"Direct dot product (both normalized): {direct_sim:.10f}")
        print(f"  → This should equal cosine similarity: {cosine_sim:.10f}")
        if abs(direct_sim - cosine_sim) > 1e-6:
            print("  ⚠ WARNING: Mismatch between direct dot product and cosine similarity!")

    print()
    print("=" * 80)
    print("Analysis:")
    print("=" * 80)
    if cosine_sim > 0.99:
        print("✓ Embeddings are nearly identical")
    elif cosine_sim > 0.9:
        print("⚠ Embeddings are similar but not identical")
        print("  Possible causes:")
        print("  - Model non-determinism (unlikely for HuggingFace models)")
        print("  - Text preprocessing differences")
        print("  - Batch vs individual embedding processing")
    else:
        print("✗ Embeddings are significantly different")
        print("  This explains why retrieval scores are ~0.74")
        print("  Possible causes:")
        print("  - Different text preprocessing during indexing vs querying")
        print("  - Model was called differently (batch vs single)")
        print("  - Embedding model configuration changed")


if __name__ == "__main__":
    main()
