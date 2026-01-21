## Current Grading Strategy

### Step 1: Score each dimension (keyword + semantic, 50-50)

For each dimension (criterion), the system computes:

```
dimension_score = (0.5 × keyword_score + 0.5 × semantic_score) × max_points
```

Where:
- `keyword_score` (0-1): Based on keyword matches between student answer and criterion description
- `semantic_score` (0-1): Based on semantic similarity of retrieved evidence chunks
- `max_points`: The points allocated to that dimension (3, 3, 2, or 2 in your q02 rubric)

### Step 2: Sum dimension scores (already weighted by points)

The total score is simply:
```
total_score = sum(dimension_scores)
```

This is already weighted by the point allocation:
- Dimension 1 (3 points): contributes up to 3 points
- Dimension 2 (3 points): contributes up to 3 points  
- Dimension 3 (2 points): contributes up to 2 points
- Dimension 4 (2 points): contributes up to 2 points

Total: 10 points maximum

## Example Calculation

For q02 with points (3, 3, 2, 2):

1. Dimension 1 (3 points):
   - keyword_score = 0.8, semantic_score = 0.6
   - dimension_score = (0.5 × 0.8 + 0.5 × 0.6) × 3 = 0.7 × 3 = 2.1 → 2 points

2. Dimension 2 (3 points):
   - keyword_score = 0.9, semantic_score = 0.8
   - dimension_score = (0.5 × 0.9 + 0.5 × 0.8) × 3 = 0.85 × 3 = 2.55 → 3 points

3. Dimension 3 (2 points):
   - keyword_score = 0.5, semantic_score = 0.7
   - dimension_score = (0.5 × 0.5 + 0.5 × 0.7) × 2 = 0.6 × 2 = 1.2 → 1 point

4. Dimension 4 (2 points):
   - keyword_score = 0.6, semantic_score = 0.5
   - dimension_score = (0.5 × 0.6 + 0.5 × 0.5) × 2 = 0.55 × 2 = 1.1 → 1 point

Total: 2 + 3 + 1 + 1 = 7/10 points

## Note

The current implementation in `grading_pipeline/pipeline.py` uses `apply_rubric_scoring()`, which only does keyword matching. The two-dimensional scoring (keyword + semantic) is documented but may not be fully integrated. The rubric structure supports it with `scoring_weights`, but the pipeline needs to use `apply_rubric_scoring_two_dimensional()` instead of `apply_rubric_scoring()` to enable the 50-50 weighting.
