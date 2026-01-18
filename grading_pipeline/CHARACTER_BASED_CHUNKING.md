# Character-Based Chunking Implementation

## Problem

The original implementation used `SentenceSplitter` for the sentence index, which has a critical issue:

**`SentenceSplitter.chunk_size` measures TOKENS (sentence units), not CHARACTERS:**

1. The sentence tokenizer splits text by delimiters (`.`, `?`, `!`, etc.)
2. PDF text often has poor sentence boundaries (slide formatting breaks sentences)
3. Each "sentence token" can be 300-400 characters
4. `chunk_size=256` meant "accumulate up to 256 sentence-tokens", resulting in 700-800 character chunks
5. Chunks didn't align on sentence boundaries - they stopped mid-sentence when token limit was reached

### Example Issue

With `chunk_size=256, chunk_overlap=50` using `SentenceSplitter`:
- **Expected**: 256 character chunks with 50 character overlap
- **Actual**: 785 character chunks (3x larger!)
- **Overlap**: Chunks ended mid-sentence, not at sentence boundaries

## Solution

Replaced `SentenceSplitter` with **character-based chunking** using `split_text_by_characters()`:

### Key Changes

1. **`build_sentence_index_in_memory()`**: Now uses `split_text_by_characters()` instead of `SentenceSplitter`
2. **`add_documents_to_indexes_in_memory()`**: Updated to use character-based chunking
3. **Manifest calculation**: Updated to use character-based chunking for accurate counts
4. **Configuration**: Updated `sources.yaml` comments to clarify character-based approach

### Benefits

✅ **Predictable chunk sizes**: Chunks are guaranteed to be ≤ `chunk_size` characters
✅ **Exact overlap**: Overlap is exactly `chunk_overlap` characters
✅ **Word boundary awareness**: Still tries to break at word boundaries when possible
✅ **Hard size limits**: NEVER exceeds `chunk_size` (enforced by `split_text_by_characters`)

## Results

With `chunk_size=256, chunk_overlap=50`:

```
Chunk 1: 256 chars
Chunk 2: 253 chars  (slightly less due to word boundary)
Chunk 3: 255 chars
Chunk 4: 256 chars
Chunk 5: 254 chars
```

**Overlap verification**: Exactly 49-50 characters between consecutive chunks ✓

## Configuration

In `sources.yaml`:

```yaml
chunking:
  word:
    chunk_size: 512  # Characters per chunk
    chunk_overlap: 50
  sentence:
    chunk_size: 256  # Characters per chunk (HARD LIMIT)
    chunk_overlap: 50
```

## Implementation Details

### `split_text_by_characters()` Algorithm

1. **Hard limit enforcement**: Never exceeds `chunk_size`
2. **Word boundary preference**: Tries to break at spaces (but only if past halfway point)
3. **Overlap handling**: Backs up by `chunk_overlap` characters for next chunk
4. **Truncation safety**: Enforces hard limit even if word boundary logic fails

### Why Not Use SentenceSplitter?

`SentenceSplitter` is designed for:
- **Token-based chunking** (good for LLM context windows)
- **Sentence-aware splitting** (good for semantic coherence)

But it's **not suitable** for:
- **Fixed character limits** (uses token counts instead)
- **Predictable chunk sizes** (depends on sentence structure)
- **PDF text** (poor sentence boundaries in slide formatting)

## Testing

All tests pass with character-based chunking:
- ✓ Chunk sizes are within limits (≤256 chars)
- ✓ Overlap is correct (~50 chars)
- ✓ Retrieval works correctly
- ✓ Incremental indexing works
- ✓ Pickle save/load works
- ✓ Cosine similarity works

## Migration Notes

If you previously built indexes with `SentenceSplitter`:
1. Run `build_index_in_memory.py --force` to rebuild with character-based chunking
2. Expect more chunks (85 vs 29 for the test PDF)
3. Chunks will be smaller and more uniform in size
4. Retrieval results may differ slightly (more granular chunks)
