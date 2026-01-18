# Slide-Aware Chunking Implementation

## Problem

For a 30-page slide deck, only 38 chunks were created with 512-character chunks. This is too few because:
1. **Chunks span multiple slides**: PDF pages are joined into one text string, then chunked at 512 characters, causing chunks to cross slide boundaries
2. **Poor granularity**: With ~19,000 characters total (38 × 512), we get roughly 1.27 chunks per slide, losing slide-level context

## Solution

Implemented **source-type-aware chunking** that uses smaller chunk sizes for slides:

- **Slides** (`source_type: "slide"`): **128-character chunks** (4x more granular)
- **Other sources**: **512-character chunks** (default)

This ensures:
- ✅ More chunks per slide (~4x increase)
- ✅ Better slide-level granularity
- ✅ Chunks are less likely to span multiple slides
- ✅ Still respects word boundaries

## Implementation

### New Function: `_get_chunk_size_for_source()`

```python
def _get_chunk_size_for_source(source_type: str | None) -> int:
    """Get appropriate chunk size based on source type."""
    if source_type == "slide":
        return 128  # Slides need finer granularity
    else:
        return 512  # Default for other sources
```

### Modified Functions

1. **`add_documents_to_indexes()`**: Groups documents by `source_type` and processes each group with its appropriate chunk size
2. **`build_or_update_dual_indexes()`**: Fresh builds now use source-aware chunking
3. **Manifest entry creation**: Uses correct chunk size when estimating chunk counts

### How It Works

```python
# Group documents by source_type
docs_by_type = defaultdict(list)
for doc in documents:
    source_type = doc.metadata.get("source_type", "file")
    docs_by_type[source_type].append(doc)

# Process each group with appropriate chunk size
for source_type, type_docs in docs_by_type.items():
    chunk_size = _get_chunk_size_for_source(source_type)  # 128 for slides, 512 for others
    word_parser = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=50)
    # ... process documents
```

## Expected Results

### Before (512-char chunks for slides)
- 30-page slide deck → ~38 chunks
- ~1.27 chunks per slide
- Chunks often span 2-3 slides

### After (128-char chunks for slides)
- 30-page slide deck → ~150 chunks (estimated)
- ~5 chunks per slide
- Chunks typically stay within a single slide
- Better retrieval granularity

## Usage

No changes needed! The system automatically detects `source_type: "slide"` from your YAML config:

```yaml
sources:
  - id: slides_quality
    type: file
    path: grading_pipeline/sources/slides_data_type_quality.pdf
    metadata:
      source_type: "slide"  # ← This triggers 128-char chunks
```

## Rebuilding Indexes

After this change, you **must rebuild** the word index to apply the new chunk sizes:

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
./build_index.x --force-word
```

Then verify with:
```bash
uv run python -m grading_pipeline.test_chromadb_scores
```

You should see:
- More chunks (e.g., ~150 instead of 38)
- Chunk length distribution showing many chunks in [0, 128) range
- Better slide-level granularity

## Future Enhancements

Potential improvements:
1. **Per-page chunking**: Create one document per PDF page to strictly enforce slide boundaries
2. **Configurable chunk sizes**: Allow custom chunk sizes per source in YAML config
3. **Slide boundary detection**: Use PDF page markers to prevent cross-slide chunks

For now, 128-char chunks provide a good balance between granularity and performance.
