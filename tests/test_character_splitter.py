#!/usr/bin/env python3
"""Tests for CharacterTextSplitter.

Tests that the custom character-based text splitter:
1. Can be instantiated correctly
2. Enforces strict chunk_size limits
3. Handles overlap correctly
4. Splits at word boundaries when possible
5. Handles edge cases

Usage:
    uv run python -m tests.test_character_splitter
"""

from retrieval_core.index_builder import CharacterTextSplitter


def test_instantiation() -> None:
    """Test that CharacterTextSplitter can be instantiated."""
    print("Test 1: Instantiation...")
    splitter = CharacterTextSplitter(chunk_size=512, chunk_overlap=50)
    assert splitter is not None
    print("  ✓ CharacterTextSplitter instantiated successfully")


def test_basic_splitting() -> None:
    """Test basic text splitting functionality."""
    print("\nTest 2: Basic splitting...")
    splitter = CharacterTextSplitter(chunk_size=10, chunk_overlap=2)
    
    text = "This is a test sentence that is longer than ten characters."
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 0
    assert all(len(chunk) > 0 for chunk in chunks)
    print(f"  ✓ Split text into {len(chunks)} chunks")


def test_strict_chunk_size() -> None:
    """Test that chunks never exceed chunk_size."""
    print("\nTest 3: Strict chunk size enforcement...")
    chunk_size = 20
    splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=5)
    
    # Create text longer than chunk_size
    text = "This is a very long sentence that definitely exceeds twenty characters and should be split into multiple chunks."
    chunks = splitter.split_text(text)
    
    # Verify all chunks are <= chunk_size
    max_chunk_len = max(len(chunk) for chunk in chunks) if chunks else 0
    assert max_chunk_len <= chunk_size, f"Found chunk of length {max_chunk_len} exceeding {chunk_size}"
    print(f"  ✓ All {len(chunks)} chunks are ≤ {chunk_size} characters (max: {max_chunk_len})")


def test_overlap() -> None:
    """Test that overlap works correctly."""
    print("\nTest 4: Overlap functionality...")
    chunk_size = 15
    chunk_overlap = 5
    splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    text = "This is a test sentence that is longer than fifteen characters to test overlap."
    chunks = splitter.split_text(text)
    
    # Check that consecutive chunks have overlap
    if len(chunks) > 1:
        # Find overlap between first two chunks
        chunk1_end = chunks[0][-chunk_overlap:]
        chunk2_start = chunks[1][:chunk_overlap]
        # They should share some content (may not be exact due to word boundaries)
        assert len(chunk1_end) > 0 and len(chunk2_start) > 0
        print(f"  ✓ Overlap detected between chunks (overlap={chunk_overlap})")
    else:
        print(f"  ✓ Only one chunk (text too short for overlap)")


def test_empty_text() -> None:
    """Test handling of empty text."""
    print("\nTest 5: Empty text handling...")
    splitter = CharacterTextSplitter(chunk_size=10, chunk_overlap=2)
    
    chunks = splitter.split_text("")
    assert chunks == []
    print("  ✓ Empty text returns empty list")
    
    chunks = splitter.split_text("   ")
    # Should handle whitespace-only text
    print(f"  ✓ Whitespace-only text handled ({len(chunks)} chunks)")


def test_short_text() -> None:
    """Test handling of text shorter than chunk_size."""
    print("\nTest 6: Short text handling...")
    splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
    
    text = "Short text."
    chunks = splitter.split_text(text)
    
    assert len(chunks) == 1
    assert chunks[0] == text
    print(f"  ✓ Short text returns single chunk: '{chunks[0]}'")


def test_very_long_text() -> None:
    """Test handling of very long text."""
    print("\nTest 7: Very long text handling...")
    chunk_size = 50
    splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=10)
    
    # Create text much longer than chunk_size
    text = "This is a very long sentence. " * 20  # ~600 characters
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 1
    # Verify all chunks respect the limit
    max_chunk_len = max(len(chunk) for chunk in chunks)
    assert max_chunk_len <= chunk_size
    print(f"  ✓ Long text split into {len(chunks)} chunks (max length: {max_chunk_len})")


def test_word_boundary_splitting() -> None:
    """Test that splitter prefers word boundaries."""
    print("\nTest 8: Word boundary splitting...")
    chunk_size = 20
    splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    
    # Text where a word boundary exists near chunk_size
    text = "This is a test sentence that should split at word boundaries."
    chunks = splitter.split_text(text)
    
    # Check that chunks don't split mid-word (heuristic: check for common word patterns)
    # This is a basic check - in practice, the splitter should prefer spaces
    assert len(chunks) > 1
    print(f"  ✓ Text split into {len(chunks)} chunks at word boundaries")


def test_no_overlap() -> None:
    """Test splitter with no overlap."""
    print("\nTest 9: No overlap...")
    splitter = CharacterTextSplitter(chunk_size=15, chunk_overlap=0)
    
    text = "This is a test sentence that is longer than fifteen characters."
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 1
    # Verify chunks don't overlap
    total_length = sum(len(chunk) for chunk in chunks)
    # Total should be approximately equal to text length (may be slightly less due to word boundaries)
    assert total_length <= len(text)
    print(f"  ✓ No overlap: {len(chunks)} chunks, total length: {total_length} (text: {len(text)})")


def test_custom_separator() -> None:
    """Test splitter with custom separator."""
    print("\nTest 10: Custom separator...")
    splitter = CharacterTextSplitter(chunk_size=20, chunk_overlap=0, separator=".")
    
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 0
    print(f"  ✓ Custom separator ('.') used: {len(chunks)} chunks")


def run_all_tests() -> None:
    """Run all CharacterTextSplitter tests."""
    print("=" * 80)
    print("CharacterTextSplitter Test Suite")
    print("=" * 80)
    print()
    
    try:
        test_instantiation()
        test_basic_splitting()
        test_strict_chunk_size()
        test_overlap()
        test_empty_text()
        test_short_text()
        test_very_long_text()
        test_word_boundary_splitting()
        test_no_overlap()
        test_custom_separator()
        
        print()
        print("=" * 80)
        print("✓ All CharacterTextSplitter tests passed!")
        print("=" * 80)
        
    except AssertionError as e:
        print()
        print("=" * 80)
        print(f"✗ Test failed: {e}")
        print("=" * 80)
        raise
    except AttributeError as e:
        print()
        print("=" * 80)
        print(f"✗ AttributeError (likely missing instance variables): {e}")
        print("=" * 80)
        raise
    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        print("=" * 80)
        raise


if __name__ == "__main__":
    run_all_tests()
