# Grading Pipeline: YAML Source Loading with PDF Support and Incremental Indexing

Grading Pipeline extends retrieval_core with PDF file support and smart incremental indexing while reusing all existing functionality from retrieval_core.

## Core Principles

1. **Import and reuse retrieval_core** - No code duplication
2. **Extend for PDF only** - PDF-specific loading capabilities
3. **Smart incremental indexing** - Only process new or changed sources

## Features

### Imported from Version1 (Reused As-Is)
- ✅ Word-based index building (512 chars, 50 overlap)
- ✅ Sentence-based index building (pure sentence splitting)
- ✅ Dual-index architecture with ChromaDB persistence
- ✅ Cross-encoder reranking support
- ✅ URL loading with caching

### New in Grading Pipeline
- ✅ **PDF text extraction** using pypdf
- ✅ **PDF-aware file loading** in YAML configuration
- ✅ **Incremental indexing** - Only process new/changed sources
- ✅ **Source manifest tracking** - Knows what's been indexed
- ✅ **Smart change detection** - File size + modification time
- ✅ **Automatic embedding cleanup** - Delete old embeddings on changes

## Performance

### Incremental Indexing Benefits

| Scenario | Before | After | Speedup |
|----------|---------|-------|---------|
| Fresh build | 6-7s | 1.09s | Baseline |
| No changes | 6-7s rebuild | 0.14s reload | **50x faster** |
| Add new source | 6-7s rebuild all | 0.86s add only | **8x faster** |
| Modify source | 6-7s rebuild all | 0.08s update | **87x faster** |

### Key Insight

**When nothing changes, loading takes 0.14 seconds instead of rebuilding for 6+ seconds.**

## Quick Start

### 1. Install Dependencies

```bash
cd autograder
uv sync  # Installs pypdf>=3.0.0 and all retrieval_core dependencies
```

### 2. Build or Update Indexes (Incremental)

```bash
# First run: builds fresh indexes
# Subsequent runs: only processes changes
uv run python -m grading_pipeline.index_builder
```

### 3. Run Comprehensive Tests

```bash
# Test all incremental indexing scenarios
uv run python grading_pipeline/test_incremental_indexing.py
```

**Test Design**: Global cleanup at start ensures all tests begin with a clean slate. All test artifacts are stored in `tests/tmp_chroma_indexes/` (separate from production `grading_pipeline/tmp/`), making it clear what's test-related and easy to clean up. Cleanup behavior is controlled by `tests/test_config.yaml`. 

### 4. Use in Code

```python
from pathlib import Path
from grading_pipeline.index_builder import build_or_update_dual_indexes

# Build or update indexes incrementally
config_path = Path("grading_pipeline/config/sources.yaml")
persist_dir = Path("grading_pipeline/tmp/chroma_db")

# Automatically detects what needs indexing:
# - Fresh build if no indexes exist
# - Load existing if nothing changed (instant)
# - Incremental update if sources added/modified
word_index, sentence_index = build_or_update_dual_indexes(
    config_path, persist_dir
)

# Use indexes for retrieval
query = "What is data quality?"
retriever = word_index.as_retriever(similarity_top_k=5)
results = retriever.retrieve(query)
```

## Incremental Indexing

The key feature of grading_pipeline is **smart incremental indexing**:

### How It Works

1. **Manifest Tracking**: `source_manifest.yaml` tracks all indexed sources
2. **Change Detection**: Compares file size and modification time
3. **Smart Updates**:
   - **NEW sources**: Index and add to manifest
   - **CHANGED sources**: Delete old embeddings, re-index
   - **UNCHANGED sources**: Skip entirely
4. **Fast Reloading**: When nothing changed, load existing indexes instantly

### Example Workflow

```python
# Day 1: Add first lecture slide
# Result: Builds fresh index (1.09s)
word_index, sentence_index = build_or_update_dual_indexes(config, persist_dir)

# Day 2: Run again with no changes  
# Result: Loads existing index (0.14s) - 7.8x faster!
word_index, sentence_index = build_or_update_dual_indexes(config, persist_dir)

# Day 3: Add second lecture slide
# Result: Only indexes new slide (0.86s) - 8x faster than rebuild
word_index, sentence_index = build_or_update_dual_indexes(config, persist_dir)

# Day 4: Update first slide
# Result: Deletes old, indexes updated (0.08s) - 87x faster!
word_index, sentence_index = build_or_update_dual_indexes(config, persist_dir)
```

### Manifest Structure

```yaml
version: "1.0"
last_updated: "2026-01-17T00:19:27"
sources:
  file_slides_data_type_quality:
    source_id: "file_slides_data_type_quality"
    file_path: "/path/to/slides_data_type_quality.pdf"
    file_size: 1234567
    file_mtime: 1705497600.0
    source_type: "slide"
    indexed_at: "2026-01-17T00:19:27"
    num_chunks_word: 13
    num_chunks_sentence: 1
```

## File Structure

```
grading_pipeline/
├── __init__.py                    # Module marker
├── manifest.py                    # Source manifest tracking
├── index_builder.py               # PDF extensions + incremental indexing
├── test_incremental_indexing.py  # Comprehensive test suite
├── config/
│   ├── __init__.py
│   └── sources.yaml               # YAML config for PDF sources
├── tmp/
│   ├── .gitignore
│   └── chroma_db/                 # Production persistent indexes
├── tmp/
│   └── chroma_db/                 # Production persistent indexes
├── sources/
│   └── slides_data_type_quality.pdf
├── IMPLEMENTATION_SUMMARY.md      # Initial implementation notes
├── INCREMENTAL_INDEXING_SUMMARY.md # Incremental indexing details
└── README.md                      # This file
```

## Configuration

Edit `grading_pipeline/config/sources.yaml` to configure PDF sources:

```yaml
sources:
  - type: "file"
    path: "/path/to/pdf/directory/"
    patterns: ["*.pdf"]
    metadata:
      source_type: "slide"  # or "textbook", "notes", etc.
```

## Testing

The test suite verifies all incremental indexing scenarios:

1. **Fresh Build**: Build indexes when none exist
2. **No Changes**: Fast reload when sources unchanged
3. **Add New Source**: Incremental indexing of new sources only
4. **Modified Source**: Change detection and re-indexing

```bash
uv run python grading_pipeline/test_incremental_indexing.py
```

**Architecture**: Each test is independent and uses its own subdirectory in `test_tmp/`. Global cleanup at the start ensures a clean slate for every run.

Expected output:
```
[Cleanup] Removing all test artifacts...
✓ Test 1: Fresh Build - PASSED
✓ Test 2: Reload with No Changes - PASSED
✓ Test 3: Add New Source - PASSED
✓ Test 4: Modify Existing Source - PASSED
```

## Code Reuse Summary

| Function | Source | Action |
|----------|--------|--------|
| `_load_url_source()` | retrieval_core | ✓ Imported directly |
| `build_word_index()` | retrieval_core | ✓ Imported directly |
| `build_sentence_index()` | retrieval_core | ✓ Imported directly |
| `build_dual_indexes()` | retrieval_core | ✓ Imported directly |
| `load_dual_indexes()` | retrieval_core | ✓ Imported directly |
| `_extract_text_from_pdf()` | NEW | Created in grading_pipeline |
| `_load_file_source_with_pdf()` | NEW | Created in grading_pipeline |
| `load_sources_from_yaml_with_pdf()` | NEW | Created in grading_pipeline |

**Total new code**: ~100 lines (PDF-specific only)
**Reused from retrieval_core**: All index building, persistence, and URL loading

## Persistent Storage Benefits

ChromaDB indexes are persistent across runs:

- **First build**: ~6-7 seconds (parse PDF, build indexes)
- **Subsequent loads**: ~0.00 seconds (instant reload)

This means when grading students again, the indexes can be loaded instantly without rebuilding, significantly improving performance.

## Dependencies

- All retrieval_core dependencies (inherited)
- **New**: `pypdf>=3.0.0` for PDF text extraction

## Next Steps

Grading Pipeline is ready for integration with the grading pipeline:

1. Use `load_sources_from_yaml_with_pdf()` to load PDF lecture materials
2. Build persistent indexes once with retrieval_core's `build_dual_indexes()`
3. Reload indexes instantly for each grading run with `load_dual_indexes()`
4. Use retrieval_core's `DualIndexRetriever` for evidence retrieval

All retrieval_core functionality (dual indexes, reranking, retrieval) works seamlessly with PDF-loaded documents.

## Batch-by-Question Grading Pipeline

The grading pipeline implements a batch-by-question architecture for efficient grading of student submissions.

### Architecture Overview

- **Self-contained submissions**: Each submission file contains all necessary information (student_id, question_id, question_text, answer)
- **Batch processing**: Process all students for one question at a time
- **Optimized loading**: Rubric and indexes loaded once per question batch
- **Error handling**: Continue on error, don't stop batch on single failure
- **Unbuffered output**: Real-time logging to stdout or log files

### Key Components

1. **config_loader.py**: Loads and validates rubric configuration from YAML
2. **submission_loader.py**: Loads self-contained submissions and groups by question_id
3. **submission_converter.py**: Utility functions for creating self-contained submissions
4. **pipeline.py**: Core grading pipeline with batch processing
5. **cli.py**: Command-line interface for grading
6. **prepare_submissions.py**: Example driving script for submission conversion

### Quick Start

#### 1. Create Rubric Configuration

Create `grading_pipeline/config/rubrics.yaml`:

```yaml
rubrics:
  q01:
    path: "../../rubrics/q01.yaml"
    description: "Question 1: Mutual Information"
```

#### 2. Prepare Submissions

Use the example driving script or create self-contained submissions manually:

```bash
python -m grading_pipeline.prepare_submissions
```

#### 3. Grade a Question Batch

```bash
python -m grading_pipeline.cli grade-question \
  --question q01 \
  --rubrics-config grading_pipeline/config/rubrics.yaml \
  --submissions-dir grading_pipeline/submissions \
  --sources-config grading_pipeline/config/sources.yaml \
  --index-dir grading_pipeline/tmp/chroma_db \
  --output results/q01_results.json
```

#### 4. Grade a Single Student

```bash
python -m grading_pipeline.cli grade-student \
  --rubrics-config grading_pipeline/config/rubrics.yaml \
  --submission grading_pipeline/submissions/student_001_q01.yaml \
  --sources-config grading_pipeline/config/sources.yaml \
  --index-dir grading_pipeline/tmp/chroma_db \
  --output results/student_001_q01.json
```

### Submission Format

Self-contained submissions are YAML files with the following structure:

```yaml
student_id: "student_001"
question_id: "q01"
question_text: "Explain mutual information and its relationship to entropy"
rubric_version: "1.0"
answer: |
  [Student's answer text - can be multi-line]
metadata:
  created_at: "2026-01-17T10:30:00"
  rubric_path: "grading_pipeline/rubrics/q01.yaml"
```

### Results Format

Results are written as JSON files with the following structure:

```json
{
  "question_id": "q01",
  "graded_at": "2026-01-17T10:30:00",
  "total_students": 10,
  "successful": 9,
  "failed": 1,
  "students": [
    {
      "student_id": "student_001",
      "question_id": "q01",
      "score": 8,
      "max_score": 10,
      "feedback": "...",
      "citations": [...],
      "rubric_items": [...]
    }
  ]
}
```

### Error Handling

The pipeline continues processing even if individual students fail:

- Failed students are marked with an `"error"` field in results
- Error messages are logged to stdout or log file
- Batch processing continues for remaining students

### Testing

Run unit tests for individual components:

```bash
python grading_pipeline/test_config_loader.py
python grading_pipeline/test_submission_loader.py
python grading_pipeline/test_submission_converter.py
python grading_pipeline/test_pipeline.py
```

See `EXAMPLES.md` for detailed usage examples and workflows.
