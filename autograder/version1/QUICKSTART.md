# Version 1 Quick Start Guide

## Installation

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv sync
```

## Basic Usage

### 1. Run with Sample Data (Fastest Way to Test)

```bash
# Run with built-in sample data
python -m version1.pipeline --mode batched --num-students 2
```

This will:
- Create sample dual indexes in a temporary directory
- Grade 2 sample students
- Show timing breakdown including reranking

### 2. Build Indexes from Your Own Sources

#### Step 1: Configure Sources

Edit `version1/config/sources.yaml`:

```yaml
sources:
  - type: "file"
    path: "path/to/your/evidence/files/"
    patterns: ["*.md", "*.txt"]
    metadata:
      source_type: "course_material"
```

#### Step 2: Build Indexes

```python
from pathlib import Path
from config.llm_config import setup_llamaindex_defaults
from version1.index_builder import build_dual_indexes

setup_llamaindex_defaults()

config_path = Path("version1/config/sources.yaml")
persist_dir = Path("version1/chroma_db")

word_index, sentence_index = build_dual_indexes(config_path, persist_dir)
```

#### Step 3: Use in Pipeline

Modify `pipeline.py` to use your indexes instead of sample data.

### 3. Retrieve Evidence

```python
from version1.index_builder import load_dual_indexes
from version1.retriever import DualIndexRetriever

# Load indexes
persist_dir = Path("version1/chroma_db")
word_index, sentence_index = load_dual_indexes(persist_dir)

# Create retriever
retriever = DualIndexRetriever(word_index, sentence_index)

# Retrieve with reranking
results = retriever.retrieve(
    "What is mutual information?",
    top_k_per_index=10,
    final_top_k=5
)

# Print results
for i, result in enumerate(results, 1):
    print(f"{i}. {result['source_id']}")
    print(f"   Rerank score: {result['rerank_score']:.3f}")
    print(f"   From: {result['index_type']} index")
    print(f"   Text: {result['text'][:100]}...")
    print()
```

## Configuration

### Environment Variables

Add to `$HOME/.env`:

```bash
# Required
EMBEDDING_PROVIDER=sentence-transformer
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Optional (defaults shown)
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

### Change Reranker Model

```bash
# Faster but less accurate
export RERANKER_MODEL=cross-encoder/ms-marco-TinyBERT-L-6

# More accurate but slower
export RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
```

## Execution Modes

```bash
# Sequential (one at a time)
python -m version1.pipeline --mode sequential --num-students 4

# Batched (single LLM call)
python -m version1.pipeline --mode batched --num-students 4

# Async concurrent (parallel LLM calls)
python -m version1.pipeline --mode async --num-students 4

# Compare all modes
python -m version1.pipeline --mode all --num-students 2
```

## Testing Components

```bash
# Test index builder
python -m version1.index_builder

# Test retriever
python -m version1.retriever
```

## Key Differences from MWE 5

1. **Persistent Storage**: Indexes saved to disk (no rebuild needed)
2. **Dual Indexes**: Two chunking strategies for better coverage
3. **Reranking**: More accurate relevance scoring
4. **Smart Deduplication**: Keeps overlapping chunks
5. **YAML Config**: Flexible source management

## Troubleshooting

### "chromadb not found"
```bash
uv add chromadb llama-index-vector-stores-chroma
```

### "sentence-transformers not found"
```bash
uv add sentence-transformers
```

### Slow first run
First run downloads models (~200MB total). Subsequent runs are fast.

### Out of memory
Use a smaller reranker:
```bash
export RERANKER_MODEL=cross-encoder/ms-marco-TinyBERT-L-6
```

## File Structure

```
version1/
├── __init__.py              # Package init
├── config/
│   └── sources.yaml         # Configure your sources here
├── index_builder.py         # Build dual indexes
├── retriever.py             # Retrieve with reranking
├── pipeline.py              # Full grading pipeline
├── README.md                # Full documentation
├── QUICKSTART.md            # This file
└── IMPLEMENTATION_SUMMARY.md # Implementation details
```

## Next Steps

1. Read [README.md](README.md) for detailed documentation
2. Configure your sources in `config/sources.yaml`
3. Build indexes from your evidence corpus
4. Run the pipeline on your student submissions

## Support

See [README.md](README.md) for:
- Architecture details
- Performance considerations
- Advanced configuration
- Troubleshooting guide
