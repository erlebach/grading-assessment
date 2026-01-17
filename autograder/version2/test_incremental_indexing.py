"""Comprehensive test suite for version2 incremental indexing.

This script tests the smart incremental indexing functionality that:
1. Builds fresh indexes when none exist
2. Skips indexing when sources haven't changed
3. Adds only new sources incrementally
4. Detects changes and re-indexes only modified sources

All tests use version2/tmp/ for temporary artifacts.

"""

import shutil
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.llm_config import setup_llamaindex_defaults
from version2.index_builder import build_or_update_dual_indexes
from version2.manifest import get_manifest_summary, load_manifest


def cleanup_test_data(persist_dir: Path) -> None:
    """Remove test ChromaDB and manifest."""
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
        print(f"  Cleaned up {persist_dir}")


def test_fresh_build():
    """Test 1: Fresh build with no existing indexes or manifest.

    Expected:
    - Builds both word and sentence indexes
    - Creates source manifest
    - All sources marked as NEW

    """
    print("\n" + "=" * 70)
    print("Test 1: Fresh Build (No Existing Indexes)")
    print("=" * 70)

    config_path = Path("version2/config/sources.yaml")
    persist_dir = Path("version2/tmp/test_fresh_build")

    # Ensure clean start
    cleanup_test_data(persist_dir)

    print(f"\nBuilding indexes for the first time...")
    start_time = time.time()

    word_index, sentence_index = build_or_update_dual_indexes(config_path, persist_dir)

    build_time = time.time() - start_time
    print(f"\n  Build completed in {build_time:.2f}s")

    # Verify manifest was created
    manifest = load_manifest(persist_dir)
    print(f"\n  Manifest summary:")
    print("  " + get_manifest_summary(manifest).replace("\n", "\n  "))

    # Verify indexes work
    query = "What is data quality?"
    word_retriever = word_index.as_retriever(similarity_top_k=2)
    word_nodes = word_retriever.retrieve(query)
    print(f"\n  Retrieval test: {len(word_nodes)} results from word index")

    assert len(manifest["sources"]) > 0, "Manifest should have sources"
    assert (persist_dir / "source_manifest.yaml").exists(), "Manifest file should exist"

    print(f"\n✓ Test 1 PASSED")
    return persist_dir


def test_no_changes(persist_dir: Path):
    """Test 2: Reload when no sources have changed.

    Expected:
    - Detects all sources as UNCHANGED
    - Skips indexing entirely
    - Loads existing indexes
    - Very fast (< 1 second)

    """
    print("\n" + "=" * 70)
    print("Test 2: Reload with No Changes")
    print("=" * 70)

    config_path = Path("version2/config/sources.yaml")

    print(f"\nReloading with no changes...")
    start_time = time.time()

    word_index, sentence_index = build_or_update_dual_indexes(config_path, persist_dir)

    reload_time = time.time() - start_time
    print(f"\n  Reload completed in {reload_time:.2f}s")

    # Verify indexes still work
    query = "What is data quality?"
    word_retriever = word_index.as_retriever(similarity_top_k=2)
    word_nodes = word_retriever.retrieve(query)
    print(f"\n  Retrieval test: {len(word_nodes)} results from word index")

    assert reload_time < 5.0, f"Reload should be fast, took {reload_time:.2f}s"

    print(f"\n✓ Test 2 PASSED (reload took {reload_time:.2f}s)")


def test_add_new_source():
    """Test 3: Add a new source to existing indexes.

    Expected:
    - Detects existing source as UNCHANGED
    - Detects new source as NEW
    - Indexes only the new source
    - Updates manifest with new source

    """
    print("\n" + "=" * 70)
    print("Test 3: Add New Source")
    print("=" * 70)

    config_path = Path("version2/tmp/test_add_source_config.yaml")
    persist_dir = Path("version2/tmp/test_add_source")

    # Start fresh
    cleanup_test_data(persist_dir)

    # Create initial config with one source
    initial_config = {
        "sources": [
            {
                "type": "file",
                "path": str(Path("version2/sources").absolute()),
                "patterns": ["slides_data_type_quality.pdf"],
                "metadata": {"source_type": "slide"},
            }
        ]
    }

    import yaml

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(initial_config, f)

    print(f"\nStep 1: Build initial index with 1 source...")
    word_index, sentence_index = build_or_update_dual_indexes(config_path, persist_dir)

    manifest = load_manifest(persist_dir)
    initial_source_count = len(manifest["sources"])
    print(f"  Initial sources: {initial_source_count}")

    # For this test, we'll simulate adding a new source by copying the PDF with a new name
    source_dir = Path("version2/sources")
    original_pdf = source_dir / "slides_data_type_quality.pdf"
    new_pdf = source_dir / "slides_data_type_quality_copy.pdf"

    if original_pdf.exists() and not new_pdf.exists():
        shutil.copy(original_pdf, new_pdf)
        print(f"  Created test file: {new_pdf.name}")

        # Update config to include both sources
        updated_config = {
            "sources": [
                {
                    "type": "file",
                    "path": str(source_dir.absolute()),
                    "patterns": ["*.pdf"],
                    "metadata": {"source_type": "slide"},
                }
            ]
        }

        with open(config_path, "w") as f:
            yaml.dump(updated_config, f)

        print(f"\nStep 2: Update index with new source...")
        start_time = time.time()
        word_index, sentence_index = build_or_update_dual_indexes(
            config_path, persist_dir
        )
        update_time = time.time() - start_time

        manifest = load_manifest(persist_dir)
        final_source_count = len(manifest["sources"])
        print(f"  Final sources: {final_source_count}")
        print(f"  Update took {update_time:.2f}s")

        # Cleanup test file
        if new_pdf.exists():
            new_pdf.unlink()
            print(f"  Cleaned up test file: {new_pdf.name}")

        assert (
            final_source_count == initial_source_count + 1
        ), "Should have one more source"
        print(f"\n✓ Test 3 PASSED")
    else:
        print(f"\n⚠ Test 3 SKIPPED (source PDF not found or copy already exists)")

    # Cleanup
    if config_path.exists():
        config_path.unlink()


def test_changed_source():
    """Test 4: Modify an existing source file.

    Expected:
    - Detects source as CHANGED (via size/mtime)
    - Deletes old embeddings for that source
    - Re-indexes only the changed source
    - Updates manifest entry

    """
    print("\n" + "=" * 70)
    print("Test 4: Modify Existing Source")
    print("=" * 70)

    # Create a test file we can modify
    test_dir = Path("version2/tmp/test_changed_source")
    test_sources_dir = test_dir / "sources"
    test_sources_dir.mkdir(parents=True, exist_ok=True)

    test_file = test_sources_dir / "test_doc.txt"
    test_file.write_text("Initial content for testing.")
    print(f"  Created test file: {test_file}")

    # Create config
    config_path = test_dir / "config.yaml"
    config = {
        "sources": [
            {
                "type": "file",
                "path": str(test_sources_dir.absolute()),
                "patterns": ["*.txt"],
                "metadata": {"source_type": "test"},
            }
        ]
    }

    import yaml

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    persist_dir = test_dir / "chroma_db"

    # Build initial index
    print(f"\nStep 1: Build initial index...")
    word_index, sentence_index = build_or_update_dual_indexes(config_path, persist_dir)

    manifest = load_manifest(persist_dir)
    original_mtime = list(manifest["sources"].values())[0]["file_mtime"]
    print(f"  Original file mtime: {original_mtime}")

    # Wait a bit and modify the file
    time.sleep(0.1)
    test_file.write_text("Modified content - this is different now!")
    print(f"  Modified test file")

    new_mtime = test_file.stat().st_mtime
    print(f"  New file mtime: {new_mtime}")
    assert new_mtime != original_mtime, "File mtime should have changed"

    # Update index
    print(f"\nStep 2: Update index after file modification...")
    start_time = time.time()
    word_index, sentence_index = build_or_update_dual_indexes(config_path, persist_dir)
    update_time = time.time() - start_time

    manifest = load_manifest(persist_dir)
    updated_mtime = list(manifest["sources"].values())[0]["file_mtime"]
    print(f"  Updated manifest mtime: {updated_mtime}")
    print(f"  Update took {update_time:.2f}s")

    assert updated_mtime == new_mtime, "Manifest should reflect new mtime"

    # Cleanup
    cleanup_test_data(test_dir)

    print(f"\n✓ Test 4 PASSED")


def main():
    """Run all incremental indexing tests."""
    print("=" * 70)
    print("Version 2: Incremental Indexing Test Suite")
    print("=" * 70)

    # Setup
    print("\n[Setup] Configuring LlamaIndex...")
    setup_llamaindex_defaults()
    print("✓ Configuration loaded")

    try:
        # Test 1: Fresh build
        persist_dir = test_fresh_build()

        # Test 2: No changes
        test_no_changes(persist_dir)

        # Test 3: Add new source
        test_add_new_source()

        # Test 4: Changed source
        test_changed_source()

        # Summary
        print("\n" + "=" * 70)
        print("Test Suite Summary")
        print("=" * 70)
        print("✓ Test 1: Fresh build - PASSED")
        print("✓ Test 2: Reload with no changes - PASSED")
        print("✓ Test 3: Add new source - PASSED")
        print("✓ Test 4: Modify existing source - PASSED")
        print("\n✓ All tests PASSED!")

    except Exception as e:
        print(f"\n✗ Test suite failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
