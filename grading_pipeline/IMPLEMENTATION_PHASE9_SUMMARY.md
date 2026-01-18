# Phase 9: Two-Dimensional Scoring System - Implementation Summary

## Overview

Successfully implemented the two-dimensional scoring system as specified in plan `6d75f648`, Phase 9. This adds keyword matching and semantic similarity scoring to the grading pipeline.

## Completed Components

### 1. Keyword Extraction During Indexing ✅

**File**: `grading_pipeline/index_builder.py`

- Added `_extract_keywords_from_text()` function that uses `extract_keywords()` from `grader.grade_question`
- Added `_add_keywords_to_metadata()` function to add keywords to document metadata
- Integrated keyword extraction into:
  - `_load_file_source_with_pdf()` - extracts keywords for file sources
  - `load_sources_from_yaml_with_pdf()` - extracts keywords for URL sources
- Keywords are now stored in document metadata and preserved through indexing

### 2. Two-Dimensional Scoring Functions ✅

**File**: `grader/grade_question.py`

Added three new functions:

- **`compute_keyword_score()`**: 
  - Extracts keywords from student answer
  - Collects keywords from evidence chunks (from metadata)
  - Compares student keywords vs evidence keywords
  - Returns keyword score (0-1) with detailed match information

- **`compute_semantic_score()`**:
  - Takes evidence chunks with similarity scores
  - Normalizes scores per-query to [0, 1]
  - Applies rank-based weighting (linear or exponential decay)
  - Returns semantic score (0-1) with normalized scores and weights

- **`apply_rubric_scoring_two_dimensional()`**:
  - Combines keyword and semantic scores per criterion
  - Uses configurable weights per criterion and dimension
  - Scales combined score to max_points
  - Returns detailed score information including both dimensions

### 3. Pipeline Integration ✅

**File**: `grading_pipeline/pipeline.py`

- Updated to use `apply_rubric_scoring_two_dimensional()` instead of `apply_rubric_scoring()`
- Loads scoring configuration from rubric (scoring_weights, semantic_decay, semantic_top_k)
- Preserves keyword and semantic score information in results
- Results now include:
  - `keyword_score`: Keyword-based score (0-1)
  - `semantic_score`: Semantic similarity score (0-1)
  - `evidence_scores`: Normalized evidence chunk scores
  - `evidence_weights`: Rank-based weights applied

### 4. Evidence Citation Metadata ✅

**File**: `evidence/index_builder.py`

- Updated `extract_citation_from_node()` to include full metadata in citation dictionary
- Added `"metadata"` field to citations containing all node metadata (including keywords)
- Maintains backward compatibility with existing citation fields

### 5. Transparency Logging ✅

**File**: `grading_pipeline/transparency_logger.py` (NEW)

Created new transparency logger with:
- `log_retrieval_results()`: Logs top-10 from word index, top-10 from sentence index, top-5 after reranking
- `log_keyword_matches()`: Logs keyword analysis with found/missing keywords
- `log_semantic_scores()`: Logs semantic analysis with normalized scores and weights
- Colored output for better readability
- Optional file logging with unbuffered writes

### 6. Detailed Retrieval Results ✅

**File**: `retrieval_core/retriever.py`

- Added `retrieve_for_criterion_with_details()` method
- Returns intermediate retrieval results:
  - `top_10_word`: Top 10 results from word index
  - `top_10_sentence`: Top 10 results from sentence index
  - `top_5_reranked`: Final top 5 after reranking
- Enables transparency logging of retrieval process

### 7. Random Question Selection ✅

**File**: `grading_pipeline/cli.py`

- Added `--random-questions N` argument to randomly select N questions
- Added `--seed` argument for reproducible random selection
- Made `--question` optional when using `--random-questions`
- Supports grading multiple questions in one run with per-question output files

### 8. Rubric Structure Update ✅

**File**: `rubrics/q01.yaml`

Updated rubric to include:
- `scoring_weights`: Per-criterion weights for keyword and semantic dimensions
- `semantic_decay`: "linear" or "exponential" for rank-based weighting
- `semantic_top_k`: Number of evidence chunks to use for semantic scoring

## Scoring Formula

The two-dimensional scoring combines keyword and semantic scores:

```
final_score = (w_keyword * keyword_score + w_semantic * semantic_score) * max_points
```

Where:
- `keyword_score`: Computed from keyword matches between student answer and evidence
- `semantic_score`: Computed from normalized similarity scores with rank-based weighting
- `w_keyword + w_semantic = 1.0` (default: 0.5 each)

## Configuration

Scoring configuration is specified in rubric YAML:

```yaml
scoring_weights:
  correctness:
    keyword: 0.5
    semantic: 0.5
  terminology:
    keyword: 0.5
    semantic: 0.5

semantic_decay: "linear"  # or "exponential"
semantic_top_k: 5
```

## Usage

The two-dimensional scoring is automatically used when:
1. Rubric includes `scoring_weights` configuration
2. Evidence chunks have keywords in metadata (from indexing)
3. Pipeline uses `apply_rubric_scoring_two_dimensional()`

## Remaining Work

### Tests (Pending)
- Integration tests for two-dimensional scoring
- Tests for keyword extraction during indexing
- Tests for transparency logging
- Tests for random question selection

### Documentation (Pending)
- Update README.md with two-dimensional scoring documentation
- Update EXAMPLES.md with scoring examples
- Add transparency logging usage examples

## Notes

- Keyword extraction happens during indexing, so existing indexes need to be rebuilt to include keywords
- The system gracefully falls back if keywords are missing from evidence chunks
- Default weights are 0.5/0.5 if not specified in rubric
- Transparency logging is optional and can be enabled via log file parameter
