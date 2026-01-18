# CharacterTextSplitter Implementation

## Problem

The word index was using `SentenceSplitter` with `chunk_size=512`, but this does NOT enforce strict character limits. `SentenceSplitter` prioritizes sentence boundaries and will create chunks larger than `chunk_size` if a single sentence exceeds the limit.

This resulted in chunks of 1642+ characters in the word_index, which was supposed to have max 512-character chunks.

## Solution

Created a custom `CharacterTextSplitter` class that enforces strict 512-character chunks:

### Implementation

**Location**: `retrieval_core/index_builder.py`

```python
class CharacterTextSplitter(TextSplitter):
    """Text splitter that enforces strict character-based chunk sizes.
    
    Unlike SentenceSplitter, this splitter strictly enforces the chunk_size
    limit in characters, splitting text at exact character boundaries regardless
    of sentence boundaries.
    """
```

### Key Features

1. **Strict character limit**: Chunks will never exceed `chunk_size` characters
2. **Word boundary preference**: Tries to split at word boundaries when possible
3. **Configurable overlap**: Supports `chunk_overlap` for context preservation
4. **Separator-aware**: Uses specified separator (default: space) for clean splits

### Changes Made

1. **`retrieval_core/index_builder.py`**:
   - Added `CharacterTextSplitter` class
   - Replaced `SentenceSplitter` with `CharacterTextSplitter` in `build_word_index()`

2. **`grading_pipeline/index_builder.py`**:
   - Imported `CharacterTextSplitter` from `retrieval_core`
   - Replaced all instances of `SentenceSplitter(chunk_size=512)` with `CharacterTextSplitter(chunk_size=512)`

## How to Rebuild Indexes

### Quick Rebuild (Force Word Index Only)

To rebuild just the word index with strict 512-char chunks:

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv run python -m grading_pipeline.build_index --force-word
```

### Complete Rebuild (All Indexes)

To rebuild both word and sentence indexes:

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv run python -m grading_pipeline.build_index --force
```

### Incremental Update (Default)

For normal operation (only indexes new/changed sources):

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv run python -m grading_pipeline.build_index
```

### All CLI Options

```bash
# See all available options
uv run python -m grading_pipeline.build_index --help

# Options:
#   --config PATH          Path to sources.yaml (default: grading_pipeline/config/sources.yaml)
#   --output PATH          Output directory (default: grading_pipeline/tmp/chroma_db)
#   --force                Force complete rebuild (deletes all indexes)
#   --force-word           Rebuild word index only
#   --force-sentence       Rebuild sentence index only
#   --no-lazy              Load embeddings upfront (don't use lazy loading)
```

## Verification

After rebuilding, run the test to verify chunk sizes:

```bash
uv run python -m grading_pipeline.test_chromadb_scores
```

The output should show:
- `Total chunks in word_index: X`
- `Chunk lengths: min=..., max=512, avg=...`
- `✓ All chunks are ≤ 512 characters`

## Trade-offs

**Pros**:
- ✅ Strict 512-character limit enforced
- ✅ Predictable chunk sizes
- ✅ Memory-efficient (smaller chunks)

**Cons**:
- ⚠️ May break sentences mid-way
- ⚠️ Slightly lower semantic coherence compared to SentenceSplitter
- ⚠️ May split technical terms or code snippets

For the grading use case, strict size limits are more important than perfect sentence boundaries, so `CharacterTextSplitter` is the better choice.

## File Structure

```
grading_pipeline/
├── build_index.py              # CLI tool to build/rebuild indexes
├── test_index_builder.py       # Tests for index_builder functionality
├── index_builder.py            # Library functions (no test code)
├── test_chromadb_scores.py     # ChromaDB verification tests
└── CHARACTER_SPLITTER_IMPLEMENTATION.md  # This file
```
