#!/usr/bin/env python3
"""CLI tool to build or rebuild grading pipeline indexes using in-memory storage.

This script provides command-line control over index building with options
to force rebuilds, specify configurations, and control embedding loading.
Uses pickle files for persistence instead of ChromaDB.

Usage:
    # Normal incremental build (skips unchanged sources)
    uv run python -m grading_pipeline.build_index_in_memory

    # Force complete rebuild (deletes and rebuilds all indexes)
    uv run python -m grading_pipeline.build_index_in_memory --force

    # Rebuild only word index
    uv run python -m grading_pipeline.build_index_in_memory --force-word

    # Rebuild only sentence index
    uv run python -m grading_pipeline.build_index_in_memory --force-sentence

    # Specify custom config and output directory
    uv run python -m grading_pipeline.build_index_in_memory \\
        --config config/sources.yaml \\
        --output tmp/in_memory_indexes

    # Build without lazy loading (always load embeddings upfront)
    uv run python -m grading_pipeline.build_index_in_memory --no-lazy
"""

import argparse
import shutil
from pathlib import Path

from config.llm_config import setup_llamaindex_defaults
from grading_pipeline.index_builder_in_memory import (
    build_or_update_dual_indexes_in_memory,
)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build or rebuild grading pipeline indexes (in-memory)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to sources.yaml config file (default: grading_pipeline/config/sources.yaml)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for pickle files (default: grading_pipeline/tmp/in_memory_indexes)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force complete rebuild (deletes all existing indexes)",
    )

    parser.add_argument(
        "--force-word",
        action="store_true",
        help="Force rebuild of word index only (keeps sentence index)",
    )

    parser.add_argument(
        "--force-sentence",
        action="store_true",
        help="Force rebuild of sentence index only (keeps word index)",
    )

    parser.add_argument(
        "--no-lazy",
        action="store_true",
        help="Disable lazy loading (load embeddings upfront)",
    )

    args = parser.parse_args()

    # Set default paths
    if args.config is None:
        args.config = Path(__file__).parent / "config" / "sources.yaml"

    if args.output is None:
        args.output = Path(__file__).parent / "tmp" / "in_memory_indexes"

    # Validate config exists
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}")
        print("Create a sources.yaml file with your document sources.")
        return

    print("=" * 80)
    print("Grading Pipeline Index Builder (In-Memory)")
    print("=" * 80)
    print(f"Config: {args.config}")
    print(f"Output: {args.output}")
    print(f"Mode: {'Force rebuild' if args.force else 'Incremental update'}")
    print("=" * 80)
    print()

    # Handle force rebuild options
    if args.force or args.force_word or args.force_sentence:
        print("[Force Rebuild] Deleting existing indexes...")
        try:
            if args.output.exists():
                if args.force:
                    # Complete wipe - delete entire directory
                    shutil.rmtree(args.output)
                    print(f"  ✓ Deleted entire index directory")
                    args.output.mkdir(parents=True, exist_ok=True)
                else:
                    # Partial deletion - just specific pickle files
                    word_pickle = args.output / "word_index.pkl"
                    sentence_pickle = args.output / "sentence_index.pkl"

                    if args.force_word:
                        if word_pickle.exists():
                            word_pickle.unlink()
                            print("  ✓ Deleted word_index.pkl")
                        else:
                            print("  Note: word_index.pkl not found")

                    if args.force_sentence:
                        if sentence_pickle.exists():
                            sentence_pickle.unlink()
                            print("  ✓ Deleted sentence_index.pkl")
                        else:
                            print("  Note: sentence_index.pkl not found")

        except Exception as e:
            print(f"  ⚠ Warning: Could not delete indexes: {e}")
        print()

    # Setup LlamaIndex defaults (LLM and embedding model)
    print("[Setup] Configuring LLM and embedding model...")
    setup_llamaindex_defaults()
    print("✓ Configuration loaded")
    print()

    # Build or update indexes
    try:
        print("[Building] Creating or updating indexes...")
        print()

        word_index, sentence_index = build_or_update_dual_indexes_in_memory(
            config_path=args.config,
            persist_dir=args.output,
            lazy_load_embeddings=not args.no_lazy,
        )

        print()
        print("=" * 80)
        print("✓ Index build complete!")
        print("=" * 80)
        print(f"Indexes saved to: {args.output}")
        print("  - word_index.pkl")
        print("  - sentence_index.pkl")
        print()
        print("Next steps:")
        print(
            "  1. Test retrieval: uv run python -m tests.test_index_builder_in_memory"
        )
        print("  2. Run grading: uv run python -m grading_pipeline.cli --question q01")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ Error building indexes: {type(e).__name__}: {e}")
        print("=" * 80)
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
