# Quick Start Guide - Dynamic Rubrics Grading

Get started with the dynamic rubrics grading pipeline in 5 minutes.

## Prerequisites

- Dynamic rubrics generated in `rubrics_dynamic/yaml/` (q01, q02 currently available)
- Submission files in YAML format
- Source documents in `grading_pipeline/sources/`

## Step 1: Verify Setup

Check that you have the required files:

```bash
# Check dynamic rubrics exist
ls rubrics_dynamic/yaml/
# Should show: q01.yaml, q02.yaml

# Check config files
ls grading_dynamic_rubrics/config/
# Should show: rubrics.yaml, sources.yaml
```

## Step 2: Create Submissions

Create submission files in `grading_dynamic_rubrics/submissions/`:

```yaml
# grading_dynamic_rubrics/submissions/student_001_q01_good.yaml
student_id: student_001
question_id: q01
question_text: "In the context of a data table, precisely distinguish..."
rubric_version: "1.0"
answer: |
  An object is a row-level entity in the dataset (a "data object," 
  often also called an instance, example, or sample). An attribute 
  is a column-level variable describing objects (often also called 
  a feature, variable, or dimension).
metadata:
  answer_type: good
```

## Step 3: Grade a Question

Run the grading pipeline:

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder

uv run python -m grading_dynamic_rubrics.cli grade-question \
    --question q01 \
    --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \
    --submissions-dir grading_dynamic_rubrics/submissions \
    --sources-config grading_dynamic_rubrics/config/sources.yaml \
    --output grading_dynamic_rubrics/results/q01_results.json
```

## Step 4: Review Results

Check the output:

```bash
cat grading_dynamic_rubrics/results/q01_results.json
```

Results include:
- Total score and breakdown by criterion
- Keyword scores (0-1)
- Semantic scores (0-1)
- Combined scores (weighted average)
- LLM-generated feedback with citations

## Example Output

```json
{
  "question_id": "q01",
  "students": [
    {
      "student_id": "student_001",
      "score": 8,
      "max_score": 10,
      "rubric_items": [
        {
          "criterion_id": "definition_accuracy",
          "score": 3,
          "max_score": 3,
          "keyword_score": 0.85,
          "semantic_score": 0.92,
          "combined_score": 0.885
        }
      ],
      "feedback": "The answer correctly distinguishes...",
      "citations": ["file_slides_data_type_quality"]
    }
  ]
}
```

## Understanding the Scores

Each criterion shows three scores:

1. **keyword_score** (0-1): How many expected keywords appear in the answer
2. **semantic_score** (0-1): How semantically similar the answer is to reference material
3. **combined_score** (0-1): Weighted average based on rubric's `scoring_weights`

Final score = `combined_score × max_points` (rounded to integer)

## Next Steps

- **Add more questions**: Update `config/rubrics.yaml` with q03-q10
- **Adjust weights**: Modify `scoring_weights` in dynamic rubrics to emphasize keyword or semantic scoring
- **Batch grading**: Create multiple submission files and grade them all at once
- **Compare results**: Grade same question with different answer types (good, less_good, wrong)

## Troubleshooting

**Problem**: "Question ID not found"
- **Solution**: Add question to `grading_dynamic_rubrics/config/rubrics.yaml`

**Problem**: "No submissions found"
- **Solution**: Create submission files with correct naming: `student_XXX_qYY.yaml`

**Problem**: Slow performance
- **Solution**: Normal - in-memory indexes rebuild on each run (~2-3 seconds)

## Full Documentation

See [README.md](README.md) for complete documentation.
