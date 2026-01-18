#!/usr/bin/env python3
"""Check ChromaDB collection metadata to verify cosine similarity is configured.

Usage:
    uv run python -m grading_pipeline.check_index_metadata
    uv run python -m grading_pipeline.check_index_metadata --index-dir path/to/chroma_db
"""

import argparse
from pathlib import Path

import chromadb


def main() -> None:
    """Check collection metadata."""
    parser = argparse.ArgumentParser(
        description="Check ChromaDB collection metadata"
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path(__file__).parent / "tmp" / "chroma_db",
        help="Directory for ChromaDB indexes",
    )

    args = parser.parse_args()

    if not args.index_dir.exists():
        print(f"Error: Index directory not found: {args.index_dir}", flush=True)
        return

    print(f"Checking ChromaDB collections in: {args.index_dir}", flush=True)
    print("=" * 80, flush=True)

    try:
        chroma_client = chromadb.PersistentClient(path=str(args.index_dir))
        collections = chroma_client.list_collections()

        if not collections:
            print("No collections found.", flush=True)
            return

        for collection in collections:
            print(f"\nCollection: {collection.name}", flush=True)
            metadata = collection.metadata or {}
            print(f"  Metadata: {metadata}", flush=True)
            
            similarity_space = metadata.get("hnsw:space", "l2 (default)")
            print(f"  Similarity space: {similarity_space}", flush=True)
            
            if similarity_space == "cosine":
                print("  ✓ Using cosine similarity", flush=True)
            else:
                print(f"  ⚠ Using {similarity_space} (not cosine!)", flush=True)
            
            # Get collection count
            count = collection.count()
            print(f"  Documents in collection: {count}", flush=True)

        print("\n" + "=" * 80, flush=True)
        print("Note: If collections show 'l2' or missing metadata,", flush=True)
        print("      run: uv run python -m grading_pipeline.rebuild_indexes --force", flush=True)

    except Exception as e:
        print(f"Error checking collections: {e}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
