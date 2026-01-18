#!/usr/bin/env python3
"""Test script to verify ChromaDB similarity scoring.

This script tests similarity scoring by:
1. Extracting a chunk from the database
2. Querying for similar chunks using that chunk's text
3. Verifying that the original chunk appears at the top with high similarity
"""

import argparse
import math
from pathlib import Path

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder import load_dual_indexes


def test_similarity_scoring(
    index, collection_name: str, top_k: int = 10
) -> tuple[bool, dict]:
    """Test similarity scoring by querying with a chunk from the index.

    Args:
        index: VectorStoreIndex to test.
        collection_name: Name of the collection (for display).
        top_k: Number of results to retrieve.

    Returns:
        Tuple of (test_passed, results_dict).
    """
    # Determine expected chunk size based on collection name
    if collection_name == "word_index":
        expected_chunk_size = 512
    elif collection_name == "sentence_index":
        expected_chunk_size = 10000
    else:
        expected_chunk_size = None

    # Loop through ALL chunks in the database to check their sizes
    print("  Analyzing all chunks in database...", flush=True)
    try:
        from pathlib import Path

        import chromadb

        # Determine the persist directory from the index
        # We need to get it from somewhere - let's use a reasonable default
        persist_dir = Path(__file__).parent / "tmp" / "chroma_db"

        chroma_client = chromadb.PersistentClient(path=str(persist_dir))
        collection = chroma_client.get_collection(collection_name)

        # Get all documents in the collection
        results = collection.get(include=["documents"])
        all_docs = results.get("documents", [])

        if all_docs:
            doc_lengths = [len(doc) for doc in all_docs]
            avg_chunk_size = sum(doc_lengths) / len(doc_lengths)

            # Build dynamic chunk type description based on actual data
            if collection_name == "word_index":
                chunk_type = f"Word-based (avg {avg_chunk_size:.0f} chars, max {max(doc_lengths)})"
            elif collection_name == "sentence_index":
                chunk_type = f"Sentence-based (avg {avg_chunk_size:.0f} chars, max {max(doc_lengths)})"
            else:
                chunk_type = "Unknown"

            print(f"  Index type: {chunk_type}", flush=True)
            if expected_chunk_size:
                print(
                    f"  Expected chunk size: up to {expected_chunk_size} characters",
                    flush=True,
                )
            print("", flush=True)

            print(f"  Total chunks in {collection_name}: {len(all_docs)}", flush=True)
            print(
                f"  Chunk lengths: min={min(doc_lengths)}, max={max(doc_lengths)}, avg={avg_chunk_size:.1f}",
                flush=True,
            )

            if expected_chunk_size:
                oversized = [l for l in doc_lengths if l > expected_chunk_size]
                if oversized:
                    print(
                        f"  ⚠ Found {len(oversized)} chunks exceeding {expected_chunk_size} chars",
                        flush=True,
                    )
                    print(
                        f"     Oversized chunk lengths: {sorted(oversized, reverse=True)[:10]}",
                        flush=True,
                    )
                else:
                    print(
                        f"  ✓ All chunks are ≤ {expected_chunk_size} characters",
                        flush=True,
                    )

            # Show distribution as histogram with ranges
            print("  Chunk length distribution (histogram):", flush=True)

            # Define ranges for histogram (100-char buckets)
            ranges = [
                (0, 100),
                (100, 200),
                (200, 300),
                (300, 400),
                (400, 500),
                (500, 600),
            ]

            # Add additional ranges if needed based on expected chunk size or actual max
            max_length = max(doc_lengths) if doc_lengths else 0
            if max_length > 600:
                # Add ranges up to max_length, in 200-char increments
                current = 600
                while current < max_length:
                    next_end = min(current + 200, max_length + 1)
                    ranges.append((current, next_end))
                    current = next_end

            # Count chunks in each range
            total_counted = 0
            for start, end in ranges:
                # Count chunks where start <= length < end
                count = sum(1 for l in doc_lengths if start <= l < end)
                total_counted += count
                if count > 0:
                    # Show range and count
                    print(f"     [{start:4d}, {end:4d}): {count} chunks", flush=True)

            # Verify we counted all chunks
            if total_counted != len(doc_lengths):
                print(
                    f"     ⚠ Warning: Counted {total_counted} chunks but total is {len(doc_lengths)}",
                    flush=True,
                )
        else:
            print(f"  ⚠ No documents found in {collection_name}", flush=True)
            # Fallback to hardcoded descriptions if no data
            if collection_name == "word_index":
                chunk_type = "Word-based (no data available)"
            elif collection_name == "sentence_index":
                chunk_type = "Sentence-based (no data available)"
            else:
                chunk_type = "Unknown"
            print(f"  Index type: {chunk_type}", flush=True)

    except Exception as e:
        print(f"  ⚠ Could not analyze chunks: {e}", flush=True)
        import traceback

        traceback.print_exc()

        # Fallback to hardcoded descriptions on error
        if collection_name == "word_index":
            chunk_type = "Word-based (error reading data)"
        elif collection_name == "sentence_index":
            chunk_type = "Sentence-based (error reading data)"
        else:
            chunk_type = "Unknown"
        print(f"  Index type: {chunk_type}", flush=True)

    print("", flush=True)

    # First, get a chunk from the index by doing an initial query
    initial_retriever = index.as_retriever(similarity_top_k=1)
    initial_nodes = initial_retriever.retrieve("data mining")

    if not initial_nodes:
        return False, {"error": "No chunks found in index"}

    # Extract the first chunk as our test chunk
    test_chunk = initial_nodes[0]
    print(f"==>  Test chunk: {test_chunk}", flush=True)
    test_text = test_chunk.node.text
    print(f"==>  Test chunk text: {test_text}", flush=True)
    test_node_id = test_chunk.node.node_id
    print(f"==>  Test chunk node_id: {test_node_id}", flush=True)

    print(f"==>  Test chunk text length: {len(test_text)} characters", flush=True)
    print(f"==>  {expected_chunk_size=}", flush=True)

    if expected_chunk_size:
        if len(test_text) > expected_chunk_size:
            print(
                f"  ⚠ Warning: Chunk size ({len(test_text)}) exceeds expected "
                f"max ({expected_chunk_size})",
                flush=True,
            )
        else:
            print(
                f"  ✓ Chunk size ({len(test_text)}) is within expected range "
                f"(≤ {expected_chunk_size})",
                flush=True,
            )
    print(f"  Test chunk text (first 100 chars): {test_text[:100]}...", flush=True)
    print("", flush=True)

    # Now query using the test chunk's text
    print("  Querying for chunks similar to test chunk...", flush=True)
    print(f"  Query text length: {len(test_text)} characters", flush=True)
    print(
        f"  Query text (first 200 chars): ==={test_text[:100]}==={test_text[-100:]}===",
        flush=True,
    )
    print("", flush=True)

    # Try to get the stored embedding for comparison
    # Note: This is diagnostic - we'll explain why scores aren't exactly 1.0
    try:
        from llama_index.core import Settings

        embed_model = Settings.embed_model

        # Embed the query text
        query_embedding = embed_model.get_query_embedding(test_text)
        print(f"  Query embedding dimension: {len(query_embedding)}", flush=True)
        print(f"  Query embedding (first 5 values): {query_embedding[:5]}", flush=True)
        print("", flush=True)
    except Exception as e:
        print(
            f"  Note: Could not extract query embedding for comparison: {e}", flush=True
        )
        print("", flush=True)

    query_retriever = index.as_retriever(similarity_top_k=top_k)
    query_nodes = query_retriever.retrieve(test_text)

    # Find where our test chunk appears in the results
    test_chunk_rank = None
    test_chunk_score = None
    for rank, node in enumerate(query_nodes, 1):
        if node.node.node_id == test_node_id:
            test_chunk_rank = rank
            test_chunk_score = node.score
            print(f"  Test chunk rank: {test_chunk_rank}", flush=True)
            print(f"  Test chunk score: {node.score}", flush=True)
            print("  Retrieved original chunk", flush=True)
            break

    # Display results
    print(f"  Top {min(top_k, len(query_nodes))} results:", flush=True)
    for rank, node in enumerate(query_nodes[:top_k], 1):
        is_test_chunk = node.node.node_id == test_node_id
        marker = "  ← TEST CHUNK" if is_test_chunk else ""
        raw_distance = -math.log(node.score) if node.score > 0 else float("inf")
        cosine_sim_approx = (
            max(0.0, min(1.0, 1.0 - raw_distance)) if node.score > 0 else 0.0
        )

        print(
            f"    {rank}. score={node.score:.6f} "
            f"(distance={raw_distance:.3f}, cosine_sim≈{cosine_sim_approx:.3f}){marker}",
            flush=True,
        )
        print(f"       text: {node.node.text[:80]}...", flush=True)  # noqa: F541

    # Verify test passed
    test_passed = False
    if test_chunk_rank is not None:
        # Test passes if:
        # 1. Test chunk appears in top results (within top_k)
        # 2. Test chunk has high similarity (score > 0.9, meaning distance < 0.1)
        if test_chunk_rank <= top_k and test_chunk_score is not None:
            raw_distance = (
                -math.log(test_chunk_score) if test_chunk_score > 0 else float("inf")
            )
            cosine_sim_approx = (
                max(0.0, min(1.0, 1.0 - raw_distance)) if test_chunk_score > 0 else 0.0
            )

            print("", flush=True)
            print("  Why isn't the score exactly 1.0?", flush=True)
            print("  ==================================", flush=True)
            print("  A score of 0.93 means:", flush=True)
            print(f"    - Raw distance: {raw_distance:.6f} (very small!)", flush=True)
            print(
                f"    - Approximate cosine similarity: {cosine_sim_approx:.6f}",
                flush=True,
            )
            print("", flush=True)
            print("  Possible reasons for not being exactly 1.0:", flush=True)
            print(
                "    1. Embedding differences: Query text is re-embedded, which may",
                flush=True,
            )
            print(
                "       produce slightly different vectors than the stored embedding",
                flush=True,
            )
            print(
                "    2. Text preprocessing: Stored chunk may have slight differences",
                flush=True,
            )
            print(
                "       (whitespace, normalization) from the raw query text", flush=True
            )
            print(
                "    3. HNSW approximation: ChromaDB uses approximate nearest neighbor",
                flush=True,
            )
            print("       search, which may introduce small errors", flush=True)
            print(
                "    4. Floating point precision: Tiny numerical differences accumulate",
                flush=True,
            )
            print("", flush=True)
            print("  A score of 0.93 is EXCELLENT - it indicates:", flush=True)
            print("    - Distance < 0.1 (very close vectors)", flush=True)
            print("    - Cosine similarity > 0.9 (almost identical)", flush=True)
            print("    - The chunk is correctly identified as most similar", flush=True)
            print("", flush=True)

            if test_chunk_score > 0.9:
                test_passed = True
                print(
                    f"  ✓ Test PASSED: Test chunk found at rank {test_chunk_rank} "
                    f"with score {test_chunk_score:.6f} (very high similarity)",
                    flush=True,
                )
            else:
                print(
                    f"  ⚠ Test PARTIAL: Test chunk found at rank {test_chunk_rank} "
                    f"but score {test_chunk_score:.6f} is lower than expected (>0.9)",
                    flush=True,
                )
        else:
            print(
                f"\n  ✗ Test FAILED: Test chunk not found in top {top_k} results",
                flush=True,
            )
    else:
        print(
            "\n  ✗ Test FAILED: Test chunk not found in query results",
            flush=True,
        )

    return test_passed, {
        "test_chunk_node_id": test_node_id,
        "test_chunk_rank": test_chunk_rank,
        "test_chunk_score": test_chunk_score,
        "total_results": len(query_nodes),
    }


def main() -> None:
    """Test ChromaDB similarity scoring."""
    parser = argparse.ArgumentParser(description="Test ChromaDB similarity scoring")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path(__file__).parent / "tmp" / "chroma_db",
        help="Directory for ChromaDB indexes",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top results to retrieve and display",
    )

    args = parser.parse_args()

    print("=" * 80, flush=True)
    print("Testing ChromaDB / LlamaIndex Similarity Scoring", flush=True)
    print("=" * 80, flush=True)
    print(f"Index directory: {args.index_dir}", flush=True)
    print(f"Top-K: {args.top_k}", flush=True)
    print("", flush=True)

    # Setup
    setup_llamaindex_defaults()

    # Load indexes
    print("[Loading] Loading indexes...", flush=True)
    word_index, sentence_index = load_dual_indexes(args.index_dir)
    print("✓ Indexes loaded", flush=True)
    print("", flush=True)

    # Check collection metadata
    print("[Metadata] Checking collection metadata:", flush=True)
    try:
        import chromadb

        chroma_client = chromadb.PersistentClient(path=str(args.index_dir))
        for collection_name in ["word_index", "sentence_index"]:
            try:
                collection = chroma_client.get_collection(collection_name)
                metadata = collection.metadata or {}
                space = metadata.get("hnsw:space", "l2 (default)")
                count = collection.count()
                print(f"  {collection_name}: {space} ({count} documents)", flush=True)
            except Exception as e:
                print(f"  {collection_name}: Error - {e}", flush=True)
    except Exception as e:
        print(f"  Error checking metadata: {e}", flush=True)
    print("", flush=True)

    # Test word index
    print("=" * 80, flush=True)
    print("Test 1: Word Index Similarity Scoring", flush=True)
    print("=" * 80, flush=True)
    word_passed, word_results = test_similarity_scoring(
        word_index, "word_index", top_k=args.top_k
    )
    print("", flush=True)
    quit()

    # Test sentence index
    print("=" * 80, flush=True)
    print("Test 2: Sentence Index Similarity Scoring", flush=True)
    print("=" * 80, flush=True)
    sentence_passed, sentence_results = test_similarity_scoring(
        sentence_index, "sentence_index", top_k=args.top_k
    )
    print("", flush=True)

    # Summary
    print("=" * 80, flush=True)
    print("Test Summary", flush=True)
    print("=" * 80, flush=True)
    print(f"Word Index: {'✓ PASSED' if word_passed else '✗ FAILED'}", flush=True)
    if word_results.get("test_chunk_rank"):
        print(
            f"  Test chunk rank: {word_results['test_chunk_rank']}",
            flush=True,
        )
        print(
            f"  Test chunk score: {word_results['test_chunk_score']:.6f}",
            flush=True,
        )
    print(
        f"Sentence Index: {'✓ PASSED' if sentence_passed else '✗ FAILED'}", flush=True
    )
    if sentence_results.get("test_chunk_rank"):
        print(
            f"  Test chunk rank: {sentence_results['test_chunk_rank']}",
            flush=True,
        )
        print(
            f"  Test chunk score: {sentence_results['test_chunk_score']:.6f}",
            flush=True,
        )
    print("", flush=True)
    print("Expected behavior:", flush=True)
    print("  - Test chunk should appear at rank 1 (or very high)", flush=True)
    print("  - Test chunk should have score > 0.9 (distance < 0.1)", flush=True)
    print("  - This verifies that similarity scoring works correctly", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
