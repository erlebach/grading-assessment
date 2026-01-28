# Version 1: Dual-Index Chroma RAG with Reranking

This version extends the MWE 5 pipeline with advanced retrieval capabilities:

- **Chroma Vector Database**: Persistent storage replacing in-memory SimpleVectorStore
- **Dual Embedding Indexes**: Word-based (512 chars) + sentence-based chunking strategies
- **Cross-Encoder Reranking**: Improved relevance using ms-marco-MiniLM-L-6-v2
- **Smart Deduplication**: Removes only exact duplicates, keeps overlapping chunks
- **YAML Configuration**: Flexible source management for files and URLs

## Architecture

```
YAML Config → Load Sources → Dual Indexes (Word + Sentence)
                                    ↓
                            Chroma Collections
                                    ↓
                        Top-K from Both Indexes
                                    ↓
                        Union & Smart Deduplication
                                    ↓
                        Cross-Encoder Reranking
                                    ↓
                            Final Evidence
```

### Dual-Index Strategy

1. **Word-Based Index**
   - Chunk size: 512 characters
   - Overlap: 50 characters
   - Best for: Capturing context around keywords

2. **Sentence-Based Index**
   - Large chunk size (10,000 characters) for sentence-level chunking
   - No overlap
   - Best for: Semantic coherence and complete thoughts

### Smart Deduplication

Removes only **exact duplicates** (same `source_id` AND identical text content).

Keeps:
- Different chunks from the same source
- Overlapping chunks with different text
- Chunks that provide different context

This preserves valuable overlapping information while eliminating true duplicates.

### Reranking

Uses cross-encoder model (default: `cross-encoder/ms-marco-MiniLM-L-6-v2`) to:
- Re-score all candidate chunks from both indexes
- Produce more accurate relevance scores than cosine similarity alone
- Return top-k most relevant chunks after reranking

## Installation

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv sync
```

Required dependencies (already in `pyproject.toml`):
- `chromadb>=0.4.0`
- `llama-index-vector-stores-chroma>=0.1.0`
- `sentence-transformers>=2.2.0`

## Configuration

### Environment Variables

Create or update `$HOME/.env`:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LMQL_BACKEND=ollama  # or "openai", "anthropic"

# Embedding Configuration
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Reranker Configuration (optional)
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Ollama Configuration (if using Ollama)
OLLAMA_NUM_PARALLEL=4
```

### Source Configuration

Edit `version1/config/sources.yaml`:

```yaml
sources:
  # Local files
  - type: "file"
    path: "../../evidence/sources/"
    patterns: ["*.md", "*.txt", "*.pdf"]
    metadata:
      source_type: "course_material"
  
  # Web URLs
  - type: "url"
    url: "https://example.com/docs"
    cache_dir: "../../evidence/cache/"
    metadata:
      source_type: "documentation"
      source_id: "web_docs"

# Retrieval settings
retrieval:
  top_k_per_index: 10  # Results from each index
  final_top_k: 5       # Results after reranking
  similarity_threshold: 0.0

# Reranker settings
reranker:
  model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
  batch_size: 32
```

## Usage

### Building Indexes

```python
from pathlib import Path
from config.llm_config import setup_llamaindex_defaults
from version1.index_builder import build_dual_indexes

# Setup
setup_llamaindex_defaults()

# Build indexes from YAML config
config_path = Path("version1/config/sources.yaml")
persist_dir = Path("version1/chroma_db")

word_index, sentence_index = build_dual_indexes(config_path, persist_dir)
print(f"✓ Dual indexes built and persisted to {persist_dir}")
```

### Loading Existing Indexes

```python
from version1.index_builder import load_dual_indexes

persist_dir = Path("version1/chroma_db")
word_index, sentence_index = load_dual_indexes(persist_dir)
```

### Retrieval with Reranking

```python
from version1.retriever import DualIndexRetriever

# Create retriever
retriever = DualIndexRetriever(word_index, sentence_index)

# Retrieve and rerank
query = "What is mutual information?"
results = retriever.retrieve(
    query,
    top_k_per_index=10,  # Get 10 from each index
    final_top_k=5,       # Return top 5 after reranking
)

# Results include reranking scores
for result in results:
    print(f"{result['source_id']}: {result['rerank_score']:.3f}")
```

### Running the Pipeline

```bash
# Sequential mode (one student at a time)
python -m version1.pipeline --mode sequential --num-students 4

# Batched mode (single LLM call for all students)
python -m version1.pipeline --mode batched --num-students 4

# Async concurrent mode (parallel LLM calls)
python -m version1.pipeline --mode async --num-students 4

# Run all modes and compare
python -m version1.pipeline --mode all --num-students 2
```

## File Structure

```
version1/
├── __init__.py              # Package initialization
├── config/
│   ├── __init__.py
│   └── sources.yaml         # Source configuration
├── index_builder.py         # Dual-index building with Chroma
├── retriever.py             # Dual-index retrieval + reranking
├── pipeline.py              # Extended pipeline (based on mwe5)
└── README.md                # This file
```

## Key Features

### 1. Persistent Storage

Chroma provides persistent storage, so indexes don't need to be rebuilt every time:

```python
# First time: build indexes
word_index, sentence_index = build_dual_indexes(config_path, persist_dir)

# Subsequent times: load existing indexes
word_index, sentence_index = load_dual_indexes(persist_dir)
```

### 2. Flexible Source Management

YAML configuration supports:
- Multiple local file paths with glob patterns
- Web URLs with automatic caching
- Custom metadata for each source
- Easy addition of new sources

### 3. Improved Relevance

Dual-index + reranking provides:
- Better coverage (two chunking strategies)
- More accurate scoring (cross-encoder vs. cosine similarity)
- Preserved context (smart deduplication keeps overlapping chunks)

### 4. Configurable Reranker

Change reranker model via environment variable:

```bash
# Use a different cross-encoder model
export RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2

# Or in Python
import os
os.environ["RERANKER_MODEL"] = "cross-encoder/ms-marco-MiniLM-L-12-v2"
```

Popular cross-encoder models:
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (fast, default)
- `cross-encoder/ms-marco-MiniLM-L-12-v2` (more accurate)
- `cross-encoder/ms-marco-TinyBERT-L-6` (fastest)

## Performance Considerations

### Index Building

- **First build**: Slower (downloads models, creates embeddings)
- **Subsequent loads**: Fast (reads from Chroma)
- **Tip**: Build indexes once, reuse for all grading sessions

### Retrieval

- **Dual-index retrieval**: ~2x slower than single index
- **Reranking**: Adds ~100-500ms depending on candidate count
- **Overall**: Still fast enough for interactive grading (<2s per query)

### Memory

- **Chroma**: Uses disk storage, minimal RAM
- **Reranker**: Loads model into memory (~100MB)
- **Embeddings**: Cached by LlamaIndex

## Comparison with MWE 5

| Feature | MWE 5 | Version 1 |
|---------|-------|-----------|
| Vector Store | In-memory (SimpleVectorStore) | Persistent (Chroma) |
| Chunking | Single strategy (512 chars) | Dual strategy (word + sentence) |
| Retrieval | Single index | Dual-index with union |
| Scoring | Cosine similarity only | Cosine + cross-encoder reranking |
| Deduplication | By source_id only | Smart (exact duplicates only) |
| Source Config | Hardcoded | YAML-based (files + URLs) |

## Testing

Test individual components:

```bash
# Test index builder
python -m version1.index_builder

# Test retriever
python -m version1.retriever

# Test full pipeline
python -m version1.pipeline --mode batched --num-students 1
```

## Troubleshooting

### Issue: "chromadb not found"

```bash
uv add chromadb llama-index-vector-stores-chroma
```

### Issue: "sentence-transformers not found"

```bash
uv add sentence-transformers
```

### Issue: Slow first run

First run downloads models:
- Embedding model (~100MB)
- Reranker model (~100MB)

Subsequent runs are much faster.

### Issue: Out of memory

Reduce batch size in reranker or use a smaller model:

```bash
export RERANKER_MODEL=cross-encoder/ms-marco-TinyBERT-L-6
```

## Future Enhancements

- [ ] Support for PDF parsing and chunking
- [ ] Hybrid search (BM25 + vector)
- [ ] Query expansion and reformulation
- [ ] Adaptive top-k based on query complexity
- [ ] Multi-modal evidence (images, tables)
- [ ] Custom reranker training on grading data

## References

- [Chroma Documentation](https://docs.trychroma.com/)
- [LlamaIndex Vector Stores](https://docs.llamaindex.ai/en/stable/module_guides/storing/vector_stores/)
- [Sentence Transformers Cross-Encoders](https://www.sbert.net/examples/applications/cross-encoder/README.html)
- [MS MARCO Models](https://huggingface.co/cross-encoder)

## License

Same as parent project.
