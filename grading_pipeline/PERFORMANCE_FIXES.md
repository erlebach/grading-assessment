# Performance Fixes for Chunking

## Problem

Chunking was taking a long time due to redundant operations:

1. **Redundant Chunking**: Text was being chunked twice - once during index creation and again just to count chunks
2. **Inefficient Counting**: Using `split_text()` to count chunks instead of querying ChromaDB directly
3. **Unnecessary Parser Creation**: Creating sentence parsers multiple times in loops

## Fixes Applied

### 1. Removed Redundant Chunking ✅

**Before:**
```python
# Chunking happens here (with embedding generation)
word_index = VectorStoreIndex.from_documents(
    type_docs,
    storage_context=word_storage_context,
    transformations=[word_parser],
)

# Then chunking happens AGAIN just to count! (Wasteful)
for doc in type_docs:
    test_chunks = word_parser.split_text(doc.text)  # ← REMOVED
    total_word_chunks += len(test_chunks)
```

**After:**
```python
# Chunking happens here (with embedding generation)
word_index = VectorStoreIndex.from_documents(
    type_docs,
    storage_context=word_storage_context,
    transformations=[word_parser],
)

# Get count directly from ChromaDB (no redundant chunking)
num_chunks_word = word_collection.count()
```

### 2. Direct ChromaDB Count ✅

**Before:**
- Used `split_text()` to re-chunk documents just for counting
- Used fallback logic with `get_nodes_from_documents()` when counts weren't available

**After:**
- Get actual counts directly from ChromaDB collections: `word_collection.count()`
- Get sentence counts: `sentence_collection.count()`
- No redundant text processing

### 3. Optimized Manifest Entry Creation ✅

**Before:**
```python
for doc in documents:
    # Created parser on every iteration
    sentence_parser = SentenceSplitter(...)
    word_parser = CharacterTextSplitter(...)
```

**After:**
```python
# Create parser once outside loop
sentence_parser = SentenceSplitter(...)
for doc in documents:
    # Only create word_parser per document (needed for source-type-specific sizes)
    word_parser = CharacterTextSplitter(...)
```

**Note**: `get_nodes_from_documents()` is still used for manifest estimation, but this is efficient because it only chunks text without generating embeddings.

## Performance Impact

### Before
- **Chunking**: Text processed twice (once for indexing, once for counting)
- **Time**: ~2x the necessary chunking time
- **Memory**: Temporary chunk lists created unnecessarily

### After
- **Chunking**: Text processed once (only for indexing)
- **Counting**: Direct database query (instant)
- **Time**: ~50% reduction in chunking overhead
- **Memory**: No redundant chunk storage

## What Still Takes Time

The remaining time is primarily from:

1. **Embedding Generation**: This is the main bottleneck
   - With 128-char chunks for slides: ~4x more embeddings than 512-char chunks
   - This is expected and necessary for retrieval quality

2. **ChromaDB Storage**: Writing embeddings to disk
   - Necessary for persistence
   - Optimized by ChromaDB internally

3. **PDF Text Extraction**: Reading and parsing PDF files
   - One-time cost per document
   - Necessary for content extraction

## Files Modified

- `grading_pipeline/index_builder.py`:
  - `add_documents_to_indexes()`: Removed redundant chunking, use ChromaDB counts
  - `build_or_update_dual_indexes()`: Optimized manifest entry creation

## Verification

After these fixes, you should see:
- Faster chunking phase (no redundant text processing)
- Instant chunk counting (direct database queries)
- Same functionality (chunks are still created correctly)

The embedding generation phase will still take time, but that's expected and necessary for the RAG pipeline to work.
