# Similarity Score Normalization Fix

## Problem

Cross-encoder rerank scores (from `rerank_score` field) can be outside the [-1, 1] range expected for cosine similarity. For example, scores like `-7.858076572418213` were observed, which caused negative final scores in the grading pipeline.

## Root Cause

The `DualIndexRetriever` uses a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for reranking, which produces raw relevance scores that are **not** cosine similarity scores. These scores can be:
- Negative (e.g., -7.85)
- Greater than 1 (e.g., 5.2)
- In a wide range (typically -10 to +10)

The original `apply_rubric_scoring_dynamic()` function was treating these scores as if they were cosine similarity scores in [-1, 1], which caused:
1. Negative semantic scores
2. Negative combined scores
3. Negative final scores (e.g., -14 out of 10)

## Solution

Added **score normalization** in `apply_rubric_scoring_dynamic()`:

### For Cross-Encoder Scores (`rerank_score`)

Use **sigmoid normalization** to map to [0, 1]:
```python
normalized_score = 1.0 / (1.0 + exp(-raw_score))
```

This handles:
- Negative scores (e.g., -7.85 → ~0.0004)
- Large positive scores (e.g., 5.2 → ~0.9945)
- Any real number → [0, 1]

### For Cosine Similarity Scores (`score`)

Use **linear mapping** from [-1, 1] to [0, 1]:
```python
normalized_score = (raw_score + 1.0) / 2.0
```

This ensures:
- -1 → 0
- 0 → 0.5
- 1 → 1.0

## Implementation

The fix is in `grading_dynamic_rubrics/pipeline.py`:

```python
# Check if this is a rerank_score (cross-encoder) or score (cosine)
is_rerank = "rerank_score" in evidence

if is_rerank:
    # Cross-encoder score: use sigmoid normalization
    normalized_score = 1.0 / (1.0 + math.exp(-raw_score))
else:
    # Cosine similarity score: linear map from [-1, 1] to [0, 1]
    normalized_score = (raw_score + 1.0) / 2.0
    normalized_score = max(0.0, min(1.0, normalized_score))  # Clamp
```

## Testing

Created `tests/test_dynamic_similarity_scores.py` to verify:

1. **Cosine similarity scores** are in [-1, 1] (should always be)
2. **Cross-encoder scores** are detected (may be outside [-1, 1])
3. **Final scores** are never negative (normalization prevents this)

## Example

Before fix:
```
Raw rerank_score: -7.858
→ Used directly in semantic_score calculation
→ semantic_score = -7.858 (invalid!)
→ combined_score = 0.5 × 0.8 + 0.5 × (-7.858) = -3.529
→ final_score = int(-3.529 × 10) = -35 (invalid!)
```

After fix:
```
Raw rerank_score: -7.858
→ Normalized: 1 / (1 + exp(7.858)) ≈ 0.0004
→ semantic_score = 0.0004 (valid, in [0, 1])
→ combined_score = 0.5 × 0.8 + 0.5 × 0.0004 = 0.4002
→ final_score = int(0.4002 × 10) = 4 (valid!)
```

## Debug Mode

Use `--debug` flag to see normalization in action:

```bash
uv run python -m grading_dynamic_rubrics.cli grade-question \
    --question q01 \
    --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \
    --submissions-dir grading_dynamic_rubrics/submissions \
    --sources-config grading_dynamic_rubrics/config/sources.yaml \
    --output grading_dynamic_rubrics/results/q01_results.json \
    --debug
```

Debug output shows:
```
[DEBUG] Cross-encoder score: -7.858076 -> normalized: 0.000400
  Evidence: file_slides_data_type_quality
  Raw scores: ['-7.858', '2.145', '1.234']
  Normalized scores: ['0.000', '0.895', '0.775']
  Final semantic_score: 0.556
```

## Verification

Run the test to verify the fix:

```bash
uv run python tests/test_dynamic_similarity_scores.py
```

Expected output:
- ✅ Cosine similarity scores in [-1, 1]
- ⚠️ Cross-encoder scores may be outside [-1, 1] (expected)
- ✅ Final scores never negative (normalization works)

## Impact

- **Fixes**: Negative scores in grading results
- **Improves**: Semantic scoring accuracy (normalized scores are more meaningful)
- **Maintains**: Backward compatibility (same API, just better normalization)
- **Adds**: Debug visibility into score normalization

## Related Files

- `grading_dynamic_rubrics/pipeline.py` - Score normalization implementation
- `tests/test_dynamic_similarity_scores.py` - Test suite
- `grading_dynamic_rubrics/DEBUG_GUIDE.md` - Debug mode documentation
