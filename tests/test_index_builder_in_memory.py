#!/usr/bin/env python3
"""Tests for index_builder_in_memory.py functionality.

Tests in-memory vector store with pickle persistence, cosine similarity,
deterministic retrieval, and chunk retrieval verification.

Usage:
    uv run python -m tests.test_index_builder_in_memory
"""

import math
import random
import shutil
from pathlib import Path

import numpy as np

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder_in_memory import (
    InMemoryVectorStore,
    add_documents_to_indexes_in_memory,
    build_or_update_dual_indexes_in_memory,
    build_sentence_index_in_memory,
    build_word_index_in_memory,
    delete_source_from_indexes_in_memory,
    load_dual_indexes_in_memory,
)
from llama_index.core import Document, VectorStoreIndex


def test_in_memory_vector_store_basic() -> None:
    """Test basic InMemoryVectorStore functionality."""
    print("Testing InMemoryVectorStore basic operations...")

    store = InMemoryVectorStore()
    assert len(store.embeddings) == 0
    assert len(store.nodes) == 0
    assert len(store.metadata) == 0
    print("✓ InMemoryVectorStore initialization")

    # Test pickle save/load
    test_dir = Path(__file__).parent / "tmp_in_memory_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    pickle_path = test_dir / "test_store.pkl"

    store.save_to_pickle(pickle_path)
    assert pickle_path.exists()
    print("✓ Pickle save")

    loaded_store = InMemoryVectorStore.load_from_pickle(pickle_path)
    assert len(loaded_store.embeddings) == len(store.embeddings)
    assert len(loaded_store.nodes) == len(store.nodes)
    assert len(loaded_store.metadata) == len(store.metadata)
    print("✓ Pickle load")

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
    print("✓ Basic operations test complete\n")


def test_build_word_index() -> None:
    """Test building word index from documents."""
    print("Testing word index building...")

    setup_llamaindex_defaults()

    # Create test documents
    documents = [
        Document(
            text="Data quality refers to the accuracy, completeness, and reliability of data.",
            metadata={"source_id": "test_1", "source_type": "file"},
        ),
        Document(
            text="Mutual information measures the reduction in uncertainty about one variable when observing another.",
            metadata={"source_id": "test_2", "source_type": "file"},
        ),
    ]

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "word_index"
    test_dir.mkdir(parents=True, exist_ok=True)

    index = build_word_index_in_memory(documents, test_dir, "test_word_index")

    # Verify index was created
    assert index is not None
    print("✓ Word index created")

    # Verify pickle file exists
    pickle_path = test_dir / "test_word_index.pkl"
    assert pickle_path.exists()
    print("✓ Pickle file created")

    # Test retrieval
    retriever = index.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve("What is data quality?")
    assert len(nodes) > 0
    print(f"✓ Retrieval works: {len(nodes)} results")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Word index test complete\n")


def test_build_sentence_index() -> None:
    """Test building sentence index from documents."""
    print("Testing sentence index building...")

    setup_llamaindex_defaults()

    # Create test documents
    documents = [
        Document(
            text="Data quality refers to the accuracy, completeness, and reliability of data. High-quality data is essential for making informed decisions.",
            metadata={"source_id": "test_1", "source_type": "file"},
        ),
    ]

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "sentence_index"
    test_dir.mkdir(parents=True, exist_ok=True)

    index = build_sentence_index_in_memory(
        documents, test_dir, "test_sentence_index"
    )

    # Verify index was created
    assert index is not None
    print("✓ Sentence index created")

    # Verify pickle file exists
    pickle_path = test_dir / "test_sentence_index.pkl"
    assert pickle_path.exists()
    print("✓ Pickle file created")

    # Test retrieval
    retriever = index.as_retriever(similarity_top_k=1)
    nodes = retriever.retrieve("What is data quality?")
    assert len(nodes) > 0
    print(f"✓ Retrieval works: {len(nodes)} results")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Sentence index test complete\n")


def test_pickle_save_load() -> None:
    """Test pickle save and load functionality."""
    print("Testing pickle save/load...")

    setup_llamaindex_defaults()

    # Create and build index
    documents = [
        Document(
            text="Test document for pickle persistence.",
            metadata={"source_id": "pickle_test", "source_type": "file"},
        ),
    ]

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "pickle_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Build index
    index1 = build_word_index_in_memory(documents, test_dir, "test_pickle")
    pickle_path = test_dir / "test_pickle.pkl"

    # Load index
    loaded_store = InMemoryVectorStore.load_from_pickle(pickle_path)
    index2 = VectorStoreIndex.from_vector_store(loaded_store)

    # Verify both indexes work
    retriever1 = index1.as_retriever(similarity_top_k=1)
    retriever2 = index2.as_retriever(similarity_top_k=1)

    nodes1 = retriever1.retrieve("test")
    nodes2 = retriever2.retrieve("test")

    assert len(nodes1) == len(nodes2)
    assert len(nodes1) > 0
    print("✓ Pickle save/load preserves functionality")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Pickle save/load test complete\n")


def test_incremental_indexing() -> None:
    """Test incremental indexing with add_documents_to_indexes_in_memory."""
    print("Testing incremental indexing...")

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "incremental"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Initial documents
    documents1 = [
        Document(
            text="Initial document content for testing incremental indexing.",
            metadata={"source_id": "doc1", "source_type": "file"},
        ),
    ]

    # Build initial index
    build_word_index_in_memory(documents1, test_dir, "word_index")
    build_sentence_index_in_memory(documents1, test_dir, "sentence_index")

    # Add new documents incrementally
    documents2 = [
        Document(
            text="New document content added incrementally.",
            metadata={"source_id": "doc2", "source_type": "file"},
        ),
    ]

    num_word, num_sentence = add_documents_to_indexes_in_memory(
        documents2, test_dir
    )

    assert num_word > 0
    assert num_sentence > 0
    print(f"✓ Added {num_word} word chunks, {num_sentence} sentence chunks")

    # Verify indexes can be loaded
    word_index, sentence_index = load_dual_indexes_in_memory(test_dir)
    assert word_index is not None
    assert sentence_index is not None
    print("✓ Indexes can be loaded after incremental update")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Incremental indexing test complete\n")


def test_delete_source() -> None:
    """Test deletion of sources from indexes."""
    print("Testing source deletion...")

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "delete_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create documents
    documents = [
        Document(
            text="Document to be deleted.",
            metadata={"source_id": "delete_me", "source_type": "file"},
        ),
        Document(
            text="Document to keep.",
            metadata={"source_id": "keep_me", "source_type": "file"},
        ),
    ]

    # Build index
    add_documents_to_indexes_in_memory(documents, test_dir)

    # Load and check counts
    from grading_pipeline.index_builder_in_memory import InMemoryVectorStore

    word_store = InMemoryVectorStore.load_from_pickle(test_dir / "word_index.pkl")
    sentence_store = InMemoryVectorStore.load_from_pickle(
        test_dir / "sentence_index.pkl"
    )

    initial_word_count = len(word_store.nodes)
    initial_sentence_count = len(sentence_store.nodes)

    # Delete source
    num_deleted_word, num_deleted_sentence = delete_source_from_indexes_in_memory(
        test_dir, "delete_me"
    )

    assert num_deleted_word > 0
    assert num_deleted_sentence > 0
    print(f"✓ Deleted {num_deleted_word} word chunks, {num_deleted_sentence} sentence chunks")

    # Reload and verify
    word_store2 = InMemoryVectorStore.load_from_pickle(test_dir / "word_index.pkl")
    sentence_store2 = InMemoryVectorStore.load_from_pickle(
        test_dir / "sentence_index.pkl"
    )

    assert len(word_store2.nodes) < initial_word_count
    assert len(sentence_store2.nodes) < initial_sentence_count
    print("✓ Source deletion verified")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Source deletion test complete\n")


def test_cosine_similarity() -> None:
    """Test cosine similarity retrieval."""
    print("Testing cosine similarity...")

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "cosine_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create documents with distinct content
    documents = [
        Document(
            text="Data quality is important for analytics.",
            metadata={"source_id": "doc1", "source_type": "file"},
        ),
        Document(
            text="Machine learning requires good data.",
            metadata={"source_id": "doc2", "source_type": "file"},
        ),
    ]

    index = build_word_index_in_memory(documents, test_dir, "test_cosine")

    # Query for data quality
    retriever = index.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve("data quality analytics")

    assert len(nodes) > 0
    # First result should be most similar
    assert nodes[0].score >= nodes[-1].score if len(nodes) > 1 else True
    print(f"✓ Cosine similarity works: {len(nodes)} results")
    print(f"  Top score: {nodes[0].score:.6f}")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Cosine similarity test complete\n")


def test_deterministic_retrieval() -> None:
    """Test that same query returns same results (deterministic)."""
    print("Testing deterministic retrieval...")

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "deterministic_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    documents = [
        Document(
            text="Deterministic test document with unique content.",
            metadata={"source_id": "det_test", "source_type": "file"},
        ),
    ]

    index = build_word_index_in_memory(documents, test_dir, "test_deterministic")

    query = "deterministic test"
    retriever = index.as_retriever(similarity_top_k=5)

    # Run query multiple times
    results1 = retriever.retrieve(query)
    results2 = retriever.retrieve(query)
    results3 = retriever.retrieve(query)

    # Verify same results each time
    assert len(results1) == len(results2) == len(results3)
    for i in range(len(results1)):
        assert results1[i].node.node_id == results2[i].node.node_id
        assert results2[i].node.node_id == results3[i].node.node_id
        assert abs(results1[i].score - results2[i].score) < 1e-6
        assert abs(results2[i].score - results3[i].score) < 1e-6

    print("✓ Deterministic retrieval verified (3 runs, identical results)")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Deterministic retrieval test complete\n")


def test_chunk_retrieval_verification() -> None:
    """Test chunk retrieval verification: extract chunk, query, verify it's returned."""
    print("Testing chunk retrieval verification...")
    print("=" * 60)

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "chunk_retrieval_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create documents with substantial content
    documents = [
        Document(
            text=(
                "Data quality refers to the accuracy, completeness, and reliability of data. "
                "High-quality data is essential for making informed decisions in business and research. "
                "Poor data quality can lead to incorrect conclusions and wasted resources."
            ),
            metadata={"source_id": "chunk_test_1", "source_type": "file"},
        ),
        Document(
            text=(
                "Mutual information measures the reduction in uncertainty about one variable "
                "when observing another variable. It quantifies the amount of information obtained "
                "about one random variable through observing the other random variable."
            ),
            metadata={"source_id": "chunk_test_2", "source_type": "file"},
        ),
    ]

    # Build index
    index = build_word_index_in_memory(documents, test_dir, "test_chunk_retrieval")

    # Get all nodes from the index by loading the store
    from grading_pipeline.index_builder_in_memory import InMemoryVectorStore

    word_store = InMemoryVectorStore.load_from_pickle(
        test_dir / "test_chunk_retrieval.pkl"
    )
    all_node_ids = list(word_store.nodes.keys())

    if not all_node_ids:
        print("⚠ No nodes found in index, skipping test")
        shutil.rmtree(test_dir.parent, ignore_errors=True)
        return

    # Select a random chunk
    random_node_id = random.choice(all_node_ids)
    random_node = word_store.nodes[random_node_id]
    random_chunk_text = random_node.text

    print(f"Selected chunk node_id: {random_node_id}")
    print(f"Chunk text (first 100 chars): {random_chunk_text[:100]}...")
    print()

    # Query using the chunk's text
    print(f"Querying with chunk text (length: {len(random_chunk_text)} chars)...")
    retriever = index.as_retriever(similarity_top_k=10)
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
        print(
            f"  {rank}. score={node.score:.6f} node_id={node.node.node_id[:8]}...{marker}"
        )

    # Verify test passed
    test_passed = False
    if test_chunk_rank is not None:
        print(f"\n✓ Test chunk found at rank {test_chunk_rank} with score {test_chunk_score:.6f}")

        # For in-memory store with same embedding model, we expect very high similarity
        # The score should be close to 1.0 (since we're querying with the exact same text)
        if test_chunk_rank == 1 and test_chunk_score > 0.99:
            test_passed = True
            print(
                f"✓✓ Test PASSED: Chunk at rank 1 with score {test_chunk_score:.6f} "
                f"(excellent - very high similarity)"
            )
        elif test_chunk_rank <= 3 and test_chunk_score > 0.9:
            test_passed = True
            print(
                f"✓ Test PASSED: Chunk at rank {test_chunk_rank} with score {test_chunk_score:.6f} "
                f"(good - high similarity)"
            )
        else:
            print(
                f"⚠ Test PARTIAL: Chunk at rank {test_chunk_rank} with score {test_chunk_score:.6f} "
                f"(lower than expected)"
            )
    else:
        print(f"\n✗ Test FAILED: Test chunk not found in top 10 results")

    # Additional verification: check that embedding model is consistent
    from llama_index.core import Settings

    embed_model = Settings.embed_model
    assert embed_model is not None, "Embedding model should be set"
    print(f"✓ Embedding model consistency verified: {type(embed_model).__name__}")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)

    assert test_passed, "Chunk retrieval verification failed"
    print("✓ Chunk retrieval verification test complete\n")


def test_metadata_excluded_from_embeddings() -> None:
    """Test that metadata does not affect embeddings.

    This verifies that embeddings are computed from text only, even when
    metadata fields are present.

    """
    print("Testing metadata exclusion from embeddings...")

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "metadata_embed_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    documents = [
        Document(
            text="Metadata should not affect text embeddings.",
            metadata={
                "source_id": "meta_test_1",
                "source_type": "file",
                "lecture": "Unit 7",
                "page": 42,
                "tags": ["grading", "rag"],
            },
        )
    ]

    index = build_word_index_in_memory(documents, test_dir, "test_metadata_embed")

    # Load stored embedding
    word_store = InMemoryVectorStore.load_from_pickle(
        test_dir / "test_metadata_embed.pkl"
    )
    node_ids = list(word_store.nodes.keys())
    assert len(node_ids) == 1
    node_id = node_ids[0]
    stored_embedding = word_store.embeddings[node_id]
    chunk_text = word_store.nodes[node_id].text

    # Re-embed text only
    from llama_index.core import Settings

    embed_model = Settings.embed_model
    assert embed_model is not None, "Embedding model should be set"

    new_embedding = np.array(
        embed_model.get_text_embedding(chunk_text), dtype=np.float32
    )

    stored_norm = stored_embedding / np.linalg.norm(stored_embedding)
    new_norm = new_embedding / np.linalg.norm(new_embedding)
    cosine_sim = float(np.dot(stored_norm, new_norm))

    print(f"  Cosine similarity (stored vs new): {cosine_sim:.6f}")
    assert cosine_sim > 0.99
    print("✓ Metadata excluded from embeddings")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Metadata exclusion test complete\n")


def test_compatibility_with_existing_interface() -> None:
    """Test that in-memory indexes work with existing retrieval interface."""
    print("Testing compatibility with existing interface...")

    setup_llamaindex_defaults()

    test_dir = Path(__file__).parent / "tmp_in_memory_test" / "compatibility_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    documents = [
        Document(
            text="Compatibility test document.",
            metadata={"source_id": "compat_test", "source_type": "file"},
        ),
    ]

    index = build_word_index_in_memory(documents, test_dir, "test_compat")

    # Test that as_retriever works (existing interface)
    retriever = index.as_retriever(similarity_top_k=5)
    nodes = retriever.retrieve("test")

    assert len(nodes) > 0
    assert all(hasattr(node, "node") for node in nodes)
    assert all(hasattr(node, "score") for node in nodes)
    print("✓ Compatible with existing retrieval interface")

    # Cleanup
    shutil.rmtree(test_dir.parent, ignore_errors=True)
    print("✓ Compatibility test complete\n")


def main() -> None:
    """Run all tests."""
    print("=" * 80)
    print("In-Memory Vector Store Test Suite")
    print("=" * 80)
    print()

    try:
        test_in_memory_vector_store_basic()
        test_build_word_index()
        test_build_sentence_index()
        test_pickle_save_load()
        test_incremental_indexing()
        test_delete_source()
        test_cosine_similarity()
        test_deterministic_retrieval()
        test_chunk_retrieval_verification()
        test_metadata_excluded_from_embeddings()
        test_compatibility_with_existing_interface()

        print("=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
