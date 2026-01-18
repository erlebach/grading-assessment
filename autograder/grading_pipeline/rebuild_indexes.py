#!/usr/bin/env python3
"""Rebuild ChromaDB indexes with cosine similarity.

This script deletes existing indexes and rebuilds them from scratch
with cosine similarity (instead of L2 distance).

Usage:
    uv run python -m grading_pipeline.rebuild_indexes
    # Or with custom paths:
    uv run python -m grading_pipeline.rebuild_indexes --sources-config path/to/sources.yaml --index-dir path/to/chroma_db
"""

import argparse
import shutil
from pathlib import Path

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder import build_or_update_dual_indexes


def main() -> None:
    """Rebuild indexes with cosine similarity."""
    parser = argparse.ArgumentParser(
        description="Rebuild ChromaDB indexes with cosine similarity"
    )
    parser.add_argument(
        "--sources-config",
        type=Path,
        default=Path(__file__).parent / "config" / "sources.yaml",
        help="Path to sources configuration YAML file",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path(__file__).parent / "tmp" / "chroma_db",
        help="Directory for ChromaDB indexes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if indexes exist (deletes existing indexes)",
    )

    args = parser.parse_args()

    # Validate paths
    if not args.sources_config.exists():
        print(f"Error: Sources config not found: {args.sources_config}", flush=True)
        return

    print("=" * 80, flush=True)
    print("Rebuilding ChromaDB Indexes with Cosine Similarity", flush=True)
    print("=" * 80, flush=True)
    print(f"Sources config: {args.sources_config}", flush=True)
    print(f"Index directory: {args.index_dir}", flush=True)
    print("", flush=True)

    # Setup LlamaIndex defaults (loads embedding model)
    print("[Setup] Configuring LlamaIndex...", flush=True)
    setup_llamaindex_defaults()
    print("✓ LlamaIndex configured", flush=True)
    print("", flush=True)

    # Delete existing indexes if they exist
    if args.index_dir.exists() and args.force:
        print(f"[Cleanup] Deleting existing indexes in {args.index_dir}...", flush=True)
        try:
            shutil.rmtree(args.index_dir)
            print("✓ Existing indexes deleted", flush=True)
        except Exception as e:
            print(f"⚠ Warning: Could not delete {args.index_dir}: {e}", flush=True)
            print("  Continuing anyway...", flush=True)
        print("", flush=True)
    elif args.index_dir.exists():
        # Check if collections exist and warn
        try:
            import chromadb

            chroma_client = chromadb.PersistentClient(path=str(args.index_dir))
            collections = [c.name for c in chroma_client.list_collections()]
            if collections:
                print(
                    f"⚠ Warning: Indexes already exist in {args.index_dir}",
                    flush=True,
                )
                print(
                    f"  Collections found: {', '.join(collections)}",
                    flush=True,
                )
                print(
                    "  Use --force to delete and rebuild, or indexes will be updated incrementally.",
                    flush=True,
                )
                print("", flush=True)
        except Exception:
            pass

    # Build or update indexes
    print("[Indexing] Building indexes...", flush=True)
    try:
        word_index, sentence_index = build_or_update_dual_indexes(
            config_path=args.sources_config,
            persist_dir=args.index_dir,
            lazy_load_embeddings=False,  # Already loaded above
        )
        print("", flush=True)
        print("=" * 80, flush=True)
        print("✓ Indexes rebuilt successfully!", flush=True)
        print(f"  Word index: {args.index_dir}/word_index", flush=True)
        print(f"  Sentence index: {args.index_dir}/sentence_index", flush=True)
        print("=" * 80, flush=True)
    except Exception as e:
        print(f"", flush=True)
        print("=" * 80, flush=True)
        print(f"✗ Error rebuilding indexes: {type(e).__name__}: {e}", flush=True)
        print("=" * 80, flush=True)
        raise


if __name__ == "__main__":
    main()
