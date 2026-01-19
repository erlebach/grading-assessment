#!/usr/bin/env python3
"""Tests for index_builder.py functionality.

Tests incremental indexing with lazy embedding loading.

Usage:
    uv run python -m tests.test_index_builder
"""

from pathlib import Path

from grading_pipeline.index_builder import build_or_update_dual_indexes


def test_incremental_indexing() -> None:
    """Test incremental indexing functionality with lazy loading."""
    print("Testing grading_pipeline incremental indexing with lazy embedding loading...")

    # NOTE: We do NOT call setup_llamaindex_defaults() here!
    # It will be called lazily inside build_or_update_dual_indexes()
    # ONLY when embedding is actually needed (new/changed sources).

    # Test YAML loading and incremental indexing
    config_path = Path(__file__).parent.parent / "grading_pipeline" / "config" / "sources.yaml"

    # Use test directory
    persist_dir = Path(__file__).parent / "tmp_chroma_indexes" / "index_builder_test"

    if config_path.exists():
        print(f"\nBuilding or updating indexes from {config_path}")
        word_index, sentence_index = build_or_update_dual_indexes(
            config_path, persist_dir
        )
        print("✓ Indexes ready")

        # For retrieval, we need embeddings loaded
        # Check if we need to load them for retrieval
        try:
            from llama_index.core import Settings

            if Settings.embed_model is None:
                print("\n[Loading embeddings for retrieval test...]")
                from config.llm_config import setup_llamaindex_defaults

                setup_llamaindex_defaults()
        except Exception:
            pass

        # Test retrieval
        query = "What is data quality?"
        print(f"\nTesting retrieval with query: '{query}'")

        word_retriever = word_index.as_retriever(similarity_top_k=2)
        word_nodes = word_retriever.retrieve(query)
        print(f"  Word-based retrieval: {len(word_nodes)} results")

        sentence_retriever = sentence_index.as_retriever(similarity_top_k=2)
        sentence_nodes = sentence_retriever.retrieve(query)
        print(f"  Sentence-based retrieval: {len(sentence_nodes)} results")
    else:
        print(f"Config file not found: {config_path}")
        print("Create grading_pipeline/config/sources.yaml to test")

    print("\n✓ Grading pipeline incremental indexing test complete")


if __name__ == "__main__":
    test_incremental_indexing()
