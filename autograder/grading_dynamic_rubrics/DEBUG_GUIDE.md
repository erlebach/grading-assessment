# Debug Mode Guide

How to use debug mode to troubleshoot scoring issues in the dynamic rubrics grading pipeline.

## When to Use Debug Mode

Use `--debug` flag when:
- Scores seem incorrect or unexpected
- You see **negative scores** (which should never happen)
- You want to understand how keyword and semantic scores are combined
- You're tuning `scoring_weights` in your rubrics
- You're investigating why a student got a particular score

## Enabling Debug Mode

Add `--debug` to any grading command:

```bash
uv run python -m grading_dynamic_rubrics.cli grade-question \
    --question q01 \
    --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \
    --submissions-dir grading_dynamic_rubrics/submissions \
    --sources-config grading_dynamic_rubrics/config/sources.yaml \
    --output grading_dynamic_rubrics/results/q01_results.json \
    --debug
```

## Debug Output Example

```
[DEBUG] Debug mode enabled - detailed scoring information will be printed
[Index Setup] Building in-memory indexes...
...
[Grading] Processing student_001 for q01...

[DEBUG] Criterion: definition_accuracy
  keyword_score: 0.857 (found 6/7 keywords)
  semantic_score: 0.923
  weights: keyword=0.5, semantic=0.5
  combined_score: 0.890
  final_score: 3/3

[DEBUG] Criterion: alternative_terminology
  keyword_score: 0.750 (found 3/4 keywords)
  semantic_score: 0.812
  weights: keyword=0.5, semantic=0.5
  combined_score: 0.781
  final_score: 2/3

[DEBUG] Criterion: illustrative_example
  keyword_score: 0.667 (found 4/6 keywords)
  semantic_score: 0.856
  weights: keyword=0.5, semantic=0.5
  combined_score: 0.762
  final_score: 2/2

[DEBUG] Criterion: clarity_and_organization
  keyword_score: 0.600 (found 3/5 keywords)
  semantic_score: 0.789
  weights: keyword=0.5, semantic=0.5
  combined_score: 0.695
  final_score: 1/2

[Grading] ✓ student_001 completed for q01
```

## Understanding Debug Output

Each criterion shows:

1. **keyword_score** (0-1): Proportion of expected keywords found in answer
   - Example: `0.857 (found 6/7 keywords)` means 6 out of 7 keywords matched

2. **semantic_score** (0-1): Weighted average of evidence similarity scores
   - Higher = answer is more semantically similar to reference material
   - Uses `semantic_decay` (linear) and `semantic_top_k` from rubric

3. **weights**: Keyword vs semantic balance from rubric's `scoring_weights`
   - Example: `keyword=0.5, semantic=0.5` means equal weight (50-50)

4. **combined_score** (0-1): Weighted combination
   - Formula: `keyword_weight × keyword_score + semantic_weight × semantic_score`
   - Example: `0.5 × 0.857 + 0.5 × 0.923 = 0.890`

5. **final_score**: Combined score scaled by max points and rounded
   - Formula: `int(combined_score × max_points)`
   - Example: `int(0.890 × 3) = 2` (but shown as 3 if rounded up)

## Warning Messages

### Negative Similarity Score

```
[WARNING] Negative similarity score detected: -0.123
  Evidence: file_slides_data_type_quality
```

**What it means**: Evidence retrieval returned a negative similarity score (shouldn't happen with cosine similarity)

**Action**: Check the evidence retrieval system - this indicates a bug

### Negative Semantic Score

```
[WARNING] Negative semantic_score after decay: -0.045
  similarity_scores: [0.8, -0.2, 0.6]
  decay: linear
```

**What it means**: After applying decay function, semantic score became negative

**Action**: Check similarity scores - one or more are negative

### Negative Final Score

```
[WARNING] Negative score detected! final_score=-2
  Criterion: definition_accuracy
  keyword_score=0.857, semantic_score=-0.123
  combined_score=-0.045, max_points=3
  Evidence count: 5
  Evidence scores: [0.9, -0.2, 0.7]
```

**What it means**: The final score for a criterion is negative (major bug!)

**Action**: 
1. Look at which component is negative (keyword, semantic, or combined)
2. Check evidence scores - are any negative?
3. Verify scoring weights are positive
4. Report the issue with this debug output

## Troubleshooting Scenarios

### Scenario 1: Score Too Low

**Debug shows:**
```
keyword_score: 0.200 (found 1/5 keywords)
semantic_score: 0.850
combined_score: 0.525
final_score: 1/3
```

**Analysis**: 
- Semantic score is high (0.85) but keyword score is low (0.20)
- With 50-50 weights, combined score is moderate (0.525)
- Student's answer is semantically correct but missing key terminology

**Solution**: 
- If semantic understanding is more important, adjust weights:
  ```yaml
  scoring_weights:
    definition_accuracy:
      keyword: 0.3
      semantic: 0.7
  ```

### Scenario 2: Score Too High

**Debug shows:**
```
keyword_score: 0.900 (found 9/10 keywords)
semantic_score: 0.300
combined_score: 0.600
final_score: 2/3
```

**Analysis**:
- Student used correct keywords but semantic score is low
- Answer may be keyword-stuffed without real understanding

**Solution**:
- Emphasize semantic scoring:
  ```yaml
  scoring_weights:
    definition_accuracy:
      keyword: 0.4
      semantic: 0.6
  ```

### Scenario 3: Inconsistent Scores

**Debug shows different weights per criterion:**
```
[DEBUG] Criterion: definition_accuracy
  weights: keyword=0.5, semantic=0.5
  
[DEBUG] Criterion: illustrative_example
  weights: keyword=0.3, semantic=0.7
```

**Analysis**: Different criteria use different weights (this is intentional!)

**Why**: Some criteria (like definitions) may emphasize keywords, while others (like examples) emphasize semantic understanding

## Environment Variable

You can also enable debug mode via environment variable:

```bash
export GRADING_DEBUG=1
uv run python -m grading_dynamic_rubrics.cli grade-question ...
```

Or inline:

```bash
GRADING_DEBUG=1 uv run python -m grading_dynamic_rubrics.cli grade-question ...
```

## Performance Impact

Debug mode has minimal performance impact:
- Adds ~0.01 seconds per criterion for printing
- No impact on scoring logic
- Safe to use in production for troubleshooting

## Tips

1. **Save debug output**: Redirect to file for analysis
   ```bash
   uv run python -m grading_dynamic_rubrics.cli grade-question ... --debug > debug.log 2>&1
   ```

2. **Compare students**: Run debug mode for multiple students to see scoring patterns

3. **Tune weights**: Use debug output to find optimal keyword/semantic balance

4. **Verify rubrics**: Check that `scoring_weights` in rubric match your intentions

5. **Report bugs**: If you see negative scores, save the debug output and report it
