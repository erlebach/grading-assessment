# Changes Made - Reverted to SentenceSplitter

## Summary

Reverted the sentence index implementation back to using `SentenceSplitter` (token-based) instead of character-based chunking.

## Issues Fixed

### 1. Hardcoded chunk_overlap=50
**Before:**
```python
chunks = split_text_by_characters(
    doc.text, chunk_size=chunk_size, chunk_overlap=50  # HARDCODED!
)
```

**After:**
```python
# Load word chunking config
chunking_config = load_chunking_config()
word_config = chunking_config["word"]
chunk_size = _get_chunk_size_for_source(source_type)
chunk_overlap = word_config["chunk_overlap"]  # From config

chunks = split_text_by_characters(
    doc.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
)
```

### 2. Removed Character-Based Chunking for Sentence Index
**Before:** Used `split_text_by_characters()` for sentence index (testing approach)

**After:** Reverted to `SentenceSplitter` with commented-out character-based code:
```python
# Get sentence chunks with SentenceSplitter (token-based)
sentence_config = chunking_config["sentence"]
sentence_parser = create_sentence_splitter()
sent_nodes = sentence_parser.get_nodes_from_documents([doc])
num_chunks_sentence = len(sent_nodes)

# COMMENTED OUT: Character-based chunking (was used for testing)
# sent_chunks = split_text_by_characters(
#     doc.text,
#     chunk_size=sentence_config["chunk_size"],
#     chunk_overlap=sentence_config["chunk_overlap"],
# )
# num_chunks_sentence = len(sent_chunks)
```

## Configuration Updates

### sources.yaml
```yaml
chunking:
  word:
    chunk_size: 512  # Characters
    chunk_overlap: 50  # Characters
  sentence:
    chunk_size: 256  # TOKENS (not characters)
    chunk_overlap: 50  # TOKENS
```

## Result

- **Word index**: 231 chunks (128 chars each for slides, with 50-char overlap)
- **Sentence index**: 29 chunks (token-based, ~196 tokens/~785 chars per chunk)
- **chunk_overlap**: Now loaded from config for both indexes

## Token vs Character Measurement

### SentenceSplitter (Sentence Index)
- Uses **token-based** measurement
- `chunk_size=256` means 256 tokens (not characters)
- ~4-5 characters per token
- Result: ~785 character chunks (196 tokens)

### split_text_by_characters (Word Index)
- Uses **character-based** measurement
- `chunk_size=128` means 128 characters (for slides)
- Hard limit, never exceeds specified size
- Result: exactly 128 character chunks

## Files Modified

1. `index_builder_in_memory.py`:
   - Fixed hardcoded chunk_overlap in `build_or_update_dual_indexes_in_memory()`
   - Reverted `build_sentence_index_in_memory()` to use `SentenceSplitter`
   - Reverted `add_documents_to_indexes_in_memory()` to use `SentenceSplitter`
   - Commented out character-based chunking code

2. `config/sources.yaml`:
   - Updated comments to clarify token-based measurement for sentence chunking

## Why This Is Correct

The dual-index approach uses different chunking strategies:

1. **Word Index**: Character-based (predictable, small chunks for keyword matching)
2. **Sentence Index**: Token-based (semantic coherence, larger chunks for context)

This is intentional - each index serves a different purpose in the RAG pipeline.
