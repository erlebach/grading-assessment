"""Source manifest management for incremental indexing.

This module manages the source_manifest.yaml file that tracks which sources
have been indexed, their file properties (size, mtime), and indexing metadata.

Key Functions:
    - load_manifest(): Load existing manifest from persist directory
    - save_manifest(): Save manifest to persist directory
    - get_source_info(): Extract file metadata (size, mtime, etc.)
    - has_source_changed(): Check if source file changed
    - create_manifest_entry(): Create new manifest entry for a source

"""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from llama_index.core import Document

MANIFEST_FILENAME = "source_manifest.yaml"
MANIFEST_VERSION = "1.0"


def load_manifest(persist_dir: Path) -> dict[str, Any]:
    """Load source manifest from persist directory.

    Args:
        persist_dir: Directory containing the persisted ChromaDB and manifest.

    Returns:
        Manifest dictionary with version, last_updated, and sources.
        Returns empty manifest if file doesn't exist.

    """
    manifest_path = persist_dir / MANIFEST_FILENAME

    if not manifest_path.exists():
        # Return empty manifest structure
        return {
            "version": MANIFEST_VERSION,
            "last_updated": datetime.now().isoformat(),
            "sources": {},
        }

    try:
        with open(manifest_path, "r") as f:
            manifest = yaml.safe_load(f)

        # Ensure sources dict exists
        if "sources" not in manifest:
            manifest["sources"] = {}

        return manifest
    except Exception as e:
        print(f"Warning: Failed to load manifest from {manifest_path}: {e}")
        return {
            "version": MANIFEST_VERSION,
            "last_updated": datetime.now().isoformat(),
            "sources": {},
        }


def save_manifest(persist_dir: Path, manifest: dict[str, Any]) -> None:
    """Save source manifest to persist directory.

    Args:
        persist_dir: Directory containing the persisted ChromaDB.
        manifest: Manifest dictionary to save.

    """
    # Ensure persist directory exists
    persist_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = persist_dir / MANIFEST_FILENAME

    # Update last_updated timestamp
    manifest["last_updated"] = datetime.now().isoformat()

    try:
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
        print(f"✓ Manifest saved to {manifest_path}")
    except Exception as e:
        print(f"Warning: Failed to save manifest to {manifest_path}: {e}")


def get_source_info(file_path: Path) -> dict[str, Any]:
    """Extract file metadata for change detection.

    Args:
        file_path: Path to the source file.

    Returns:
        Dictionary with file_size and file_mtime.

    """
    stat = file_path.stat()
    return {
        "file_size": stat.st_size,
        "file_mtime": stat.st_mtime,
    }


def has_source_changed(file_path: Path, manifest_entry: dict[str, Any]) -> bool:
    """Check if source file has changed since last indexing.

    Compares current file size and modification time against manifest entry.

    Args:
        file_path: Path to the source file.
        manifest_entry: Manifest entry for this source.

    Returns:
        True if file has changed, False otherwise.

    """
    if not file_path.exists():
        print(f"Warning: Source file {file_path} no longer exists")
        return True  # Consider it changed (needs handling)

    current_info = get_source_info(file_path)

    # Check if size or mtime changed
    size_changed = current_info["file_size"] != manifest_entry.get("file_size", 0)
    mtime_changed = current_info["file_mtime"] != manifest_entry.get("file_mtime", 0.0)

    return size_changed or mtime_changed


def create_manifest_entry(
    doc: Document,
    num_chunks_word: int,
    num_chunks_sentence: int,
) -> dict[str, Any]:
    """Create a manifest entry for a newly indexed source.

    Args:
        doc: Document object with metadata.
        num_chunks_word: Number of chunks in word-based index.
        num_chunks_sentence: Number of chunks in sentence-based index.

    Returns:
        Manifest entry dictionary.

    """
    file_path = Path(doc.metadata.get("file_path", ""))

    # Get current file info
    if file_path.exists():
        file_info = get_source_info(file_path)
    else:
        # Fallback if file doesn't exist
        file_info = {"file_size": 0, "file_mtime": 0.0}

    return {
        "source_id": doc.metadata.get("source_id", "unknown"),
        "file_path": str(file_path),
        "file_name": doc.metadata.get("file_name", "unknown"),
        "file_size": file_info["file_size"],
        "file_mtime": file_info["file_mtime"],
        "source_type": doc.metadata.get("source_type", "unknown"),
        "indexed_at": datetime.now().isoformat(),
        "num_chunks_word": num_chunks_word,
        "num_chunks_sentence": num_chunks_sentence,
    }


def get_manifest_summary(manifest: dict[str, Any]) -> str:
    """Get a human-readable summary of the manifest.

    Args:
        manifest: Manifest dictionary.

    Returns:
        Formatted string summary.

    """
    sources = manifest.get("sources", {})
    last_updated = manifest.get("last_updated", "unknown")

    lines = [
        f"Manifest version: {manifest.get('version', 'unknown')}",
        f"Last updated: {last_updated}",
        f"Total sources: {len(sources)}",
    ]

    if sources:
        lines.append("\nSources:")
        for source_id, entry in sources.items():
            file_name = entry.get("file_name", "unknown")
            indexed_at = entry.get("indexed_at", "unknown")
            num_chunks = entry.get("num_chunks_word", 0) + entry.get(
                "num_chunks_sentence", 0
            )
            lines.append(f"  - {file_name} ({source_id})")
            lines.append(f"    Indexed: {indexed_at}, Chunks: {num_chunks}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test manifest functions
    import tempfile

    print("Testing manifest module...")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        persist_dir = Path(temp_dir)

        # Test 1: Load non-existent manifest
        print("\n[Test 1] Load non-existent manifest")
        manifest = load_manifest(persist_dir)
        assert manifest["version"] == MANIFEST_VERSION
        assert manifest["sources"] == {}
        print("✓ Returns empty manifest")

        # Test 2: Create and save manifest entry
        print("\n[Test 2] Create and save manifest")

        # Create a test document
        test_doc = Document(
            text="Test content",
            metadata={
                "source_id": "test_file",
                "file_path": __file__,  # Use this file as test
                "file_name": "manifest.py",
                "source_type": "test",
            },
        )

        entry = create_manifest_entry(test_doc, num_chunks_word=5, num_chunks_sentence=2)
        manifest["sources"]["test_file"] = entry
        save_manifest(persist_dir, manifest)

        assert (persist_dir / MANIFEST_FILENAME).exists()
        print("✓ Manifest saved successfully")

        # Test 3: Load saved manifest
        print("\n[Test 3] Load saved manifest")
        loaded_manifest = load_manifest(persist_dir)
        assert "test_file" in loaded_manifest["sources"]
        assert loaded_manifest["sources"]["test_file"]["num_chunks_word"] == 5
        print("✓ Manifest loaded correctly")

        # Test 4: Check source change detection
        print("\n[Test 4] Change detection")
        this_file = Path(__file__)
        entry = loaded_manifest["sources"]["test_file"]

        # Should not have changed
        changed = has_source_changed(this_file, entry)
        print(f"  Has changed (should be False): {changed}")

        # Modify entry to simulate old file
        entry["file_size"] = 123  # Wrong size
        changed = has_source_changed(this_file, entry)
        assert changed
        print("✓ Detects size change")

        # Test 5: Manifest summary
        print("\n[Test 5] Manifest summary")
        summary = get_manifest_summary(loaded_manifest)
        print(summary)
        print("✓ Summary generated")

    print("\n✓ All manifest tests passed")
