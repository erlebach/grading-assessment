# Quick Start: Grading Selected Questions

## Understanding Your Files

You have **10 questions**, and for each question, **3 different answers**:

- **q01** = Question 1 (has 3 files: good, less_good, wrong)
- **q02** = Question 2 (has 3 files: good, less_good, wrong)
- **q03** = Question 3 (has 3 files: good, less_good, wrong)
- ... and so on up to **q10**

## Grading a Single Question

To grade **one question** (which will grade all 3 answer types for that question):

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder

python -m grading_pipeline.cli grade-question \
    --question q06 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

This will:
1. Find all files for q06: `student_001_q06_good.yaml`, `student_001_q06_less_good.yaml`, `student_001_q06_wrong.yaml`
2. Grade all 3 answers together
3. Save results to `q06_results.json`

## Grading Multiple Questions

To grade **3 questions** (e.g., q01, q03, q06), just run the command 3 times:

```bash
# Grade q01
python -m grading_pipeline.cli grade-question \
    --question q01 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q01_results.json

# Grade q03
python -m grading_pipeline.cli grade-question \
    --question q03 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q03_results.json

# Grade q06
python -m grading_pipeline.cli grade-question \
    --question q06 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

## Results

After grading, you'll get:
- `grading_pipeline/results/q01_results.json` - Contains scores for good, less_good, and wrong answers to q01
- `grading_pipeline/results/q03_results.json` - Contains scores for good, less_good, and wrong answers to q03
- `grading_pipeline/results/q06_results.json` - Contains scores for good, less_good, and wrong answers to q06

Each results file shows which answer type scored highest (should be "good" > "less_good" > "wrong").
