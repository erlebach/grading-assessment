#!/usr/bin/env python3
"""Test retrieval from real persisted indexes.

This test loads the actual indexes from grading_dynamic_rubrics/tmp/in_memory_indexes/
and verifies that retrieval works correctly. This ensures the fix for loading
indexes with from_vector_store() works with production indexes.

Usage:
    uv run pytest tests/test_real_indexes_retrieval.py -v
"""

from pathlib import Path

import pytest

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_factory import IndexFactory
from retrieval_core.multi_retriever import MultiIndexRetriever
import yaml


def test_load_real_indexes_and_retrieve() -> None:
    """Test loading real persisted indexes and retrieving from them."""
    print("Testing retrieval from real persisted indexes...")
    print("=" * 60)

    setup_llamaindex_defaults()

    # Use the actual production persist directory
    persist_dir = Path(__file__).parent.parent / "grading_dynamic_rubrics" / "tmp" / "in_memory_indexes"
    config_path = Path(__file__).parent.parent / "grading_dynamic_rubrics" / "config" / "sources.yaml"

    # Check that indexes exist
    word_index_pkl = persist_dir / "word_index.pkl"
    sentence_index_pkl = persist_dir / "sentence_index.pkl"

    if not word_index_pkl.exists() or not sentence_index_pkl.exists():
        pytest.skip(f"Real indexes not found at {persist_dir}. Run ./build_index_in_memory.x first.")

    print(f"Loading indexes from: {persist_dir}")
    print(f"Config file: {config_path}")

    # Load configuration
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Create factory and load indexes (same as grading pipeline)
    factory = IndexFactory(config, persist_dir)
    indexes = factory.load_active_indexes()

    print(f"\n✓ Loaded {len(indexes)} indexes: {list(indexes.keys())}")

    # Verify each index has nodes
    from grading_pipeline.index_builder_in_memory import InMemoryVectorStore

    for index_id, index in indexes.items():
        # Get the vector store from the index
        vector_store = index._storage_context.vector_store
        if isinstance(vector_store, InMemoryVectorStore):
            num_nodes = len(vector_store.nodes)
            num_embeddings = len(vector_store.embeddings)
            print(f"  {index_id}: {num_nodes} nodes, {num_embeddings} embeddings")
            assert num_nodes > 0, f"{index_id} has no nodes"
            assert num_embeddings > 0, f"{index_id} has no embeddings"
            assert num_nodes == num_embeddings, f"{index_id} node/embedding count mismatch"

    # Create retriever (same as grading pipeline)
    retriever = MultiIndexRetriever(indexes)
    print(f"\n✓ Retriever created with {len(retriever.indexes)} indexes")

    # Test retrieval with multiple queries
    test_queries = [
        "algorithm",
        "data quality",
        "mutual information",
        "clustering",
    ]

    all_passed = True
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        results = retriever.retrieve(
            query=query,
            top_k_per_index=5,
            final_top_k=3,
            similarity_threshold=0.0,
            index_subset=None,
        )

        print(f"  Retrieved {len(results)} results")
        if results:
            print(f"  ✓ Query successful")
            for i, result in enumerate(results[:3], 1):
                score = result.get("score", "N/A")
                index_id = result.get("index_id", "N/A")
                text_preview = result.get("text", "")[:60].replace("\n", " ")
                print(f"    {i}. Score: {score:.4f}, Index: {index_id}, Text: {text_preview}...")
        else:
            print(f"  ✗ WARNING: No results retrieved!")
            all_passed = False

    assert all_passed, "Some queries returned no results"
    print("\n✓ All queries returned results")


def test_real_indexes_direct_retrieval() -> None:
    """Test direct retrieval from each index individually."""
    print("\nTesting direct retrieval from each index...")
    print("=" * 60)

    setup_llamaindex_defaults()

    persist_dir = Path(__file__).parent.parent / "grading_dynamic_rubrics" / "tmp" / "in_memory_indexes"
    config_path = Path(__file__).parent.parent / "grading_dynamic_rubrics" / "config" / "sources.yaml"

    # Check that indexes exist
    word_index_pkl = persist_dir / "word_index.pkl"
    sentence_index_pkl = persist_dir / "sentence_index.pkl"

    if not word_index_pkl.exists() or not sentence_index_pkl.exists():
        pytest.skip(f"Real indexes not found at {persist_dir}. Run ./build_index_in_memory.x first.")

    # Load configuration
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Create factory and load indexes
    factory = IndexFactory(config, persist_dir)
    indexes = factory.load_active_indexes()

    # Test each index directly
    query = "algorithm data quality"
    print(f"Query: \"{query}\"\n")

    for index_id, index in indexes.items():
        print(f"Testing {index_id}...")
        retriever = index.as_retriever(similarity_top_k=3)
        nodes = retriever.retrieve(query)

        print(f"  Retrieved {len(nodes)} nodes")
        assert len(nodes) > 0, f"{index_id} returned no results"

        if nodes:
            first_node = nodes[0]
            score = first_node.score if hasattr(first_node, "score") else "N/A"
            text_preview = first_node.text[:60].replace("\n", " ") if hasattr(first_node, "text") else "N/A"
            print(f"  ✓ Top result: score={score}, text={text_preview}...")

    print("\n✓ Direct retrieval from all indexes works")


def test_real_indexes_chunk_retrieval() -> None:
    """Test chunk retrieval verification with real indexes (like test_chunk_retrieval_verification)."""
    print("\nTesting chunk retrieval verification with real indexes...")
    print("=" * 60)

    setup_llamaindex_defaults()

    persist_dir = Path(__file__).parent.parent / "grading_dynamic_rubrics" / "tmp" / "in_memory_indexes"
    config_path = Path(__file__).parent.parent / "grading_dynamic_rubrics" / "config" / "sources.yaml"

    # Check that indexes exist
    word_index_pkl = persist_dir / "word_index.pkl"

    if not word_index_pkl.exists():
        pytest.skip(f"Real indexes not found at {persist_dir}. Run ./build_index_in_memory.x first.")

    # Load the word index directly
    from grading_pipeline.index_builder_in_memory import InMemoryVectorStore
    from llama_index.core import VectorStoreIndex

    word_store = InMemoryVectorStore.load_from_pickle(word_index_pkl)
    word_index = VectorStoreIndex.from_vector_store(word_store)

    # Get all node IDs
    all_node_ids = list(word_store.nodes.keys())
    if not all_node_ids:
        pytest.skip("No nodes found in word_index")

    print(f"Word index has {len(all_node_ids)} nodes")

    # Select a random chunk
    import random
    random_node_id = random.choice(all_node_ids)
    random_node = word_store.nodes[random_node_id]
    random_chunk_text = random_node.text

    print(f"\nSelected chunk node_id: {random_node_id[:16]}...")
    print(f"Chunk text (first 100 chars): {random_chunk_text[:100]}...")

    # Query using the chunk's text
    print(f"\nQuerying with chunk text (length: {len(random_chunk_text)} chars)...")
    retriever = word_index.as_retriever(similarity_top_k=10)
    query_nodes = retriever.retrieve(random_chunk_text)

    # Find where our test chunk appears in the results
    test_chunk_rank = None
    test_chunk_score = None
    for rank, node in enumerate(query_nodes, 1):
        if node.node.node_id == random_node_id:
            test_chunk_rank = rank
            test_chunk_score = node.score
            break

    # Display results
    print(f"\nTop {min(10, len(query_nodes))} results:")
    for rank, node in enumerate(query_nodes[:10], 1):
        is_test_chunk = node.node.node_id == random_node_id
        marker = "  ← TEST CHUNK" if is_test_chunk else ""
        print(f"  {rank}. score={node.score:.6f} node_id={node.node.node_id[:16]}...{marker}")

    # Verify test passed
    assert test_chunk_rank is not None, "Test chunk not found in results"
    assert test_chunk_rank <= 3, f"Test chunk found at rank {test_chunk_rank}, expected rank 1-3"
    assert test_chunk_score > 0.9, f"Test chunk score {test_chunk_score} too low, expected > 0.9"

    print(f"\n✓ Test PASSED: Chunk at rank {test_chunk_rank} with score {test_chunk_score:.6f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
