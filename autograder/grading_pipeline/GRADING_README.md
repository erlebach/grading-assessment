# Grading Pipeline - User Guide

Complete guide for using the grading pipeline to grade student submissions.

## Table of Contents

1. [Understanding the Structure](#understanding-the-structure)
2. [Setup and Installation](#setup-and-installation)
3. [Preparing Submissions](#preparing-submissions)
4. [Running Grading](#running-grading)
5. [Understanding Results](#understanding-results)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)

## Understanding the Structure

### File Organization

```
autograder/
├── grading_pipeline/          # Main grading pipeline code
│   ├── cli.py                 # Command-line interface (this is what you run)
│   ├── submissions/           # Student submission files (YAML format)
│   ├── results/               # Grading results (JSON files)
│   ├── config/
│   │   ├── rubrics.yaml      # Maps question IDs to rubric files
│   │   └── sources.yaml      # Evidence source configuration
│   └── tmp/
│       └── chroma_db/         # Index storage (auto-created)
├── rubrics/                   # Rubric files (q01.yaml, q02.yaml, etc.)
└── ten_questions.md          # Your 10 questions
└── ten_answers.md            # Answer examples
```

### Submission File Structure

Each submission file is named: `student_XXX_qYY_answer_type.yaml`

- **student_XXX**: Student identifier (e.g., `student_001`)
- **qYY**: Question identifier (e.g., `q01`, `q06`)
- **answer_type**: Type of answer (`good`, `less_good`, `wrong`)

**Example files:**
- `student_001_q01_good.yaml` - Student 001, Question 1, good answer
- `student_001_q01_less_good.yaml` - Student 001, Question 1, less good answer
- `student_001_q01_wrong.yaml` - Student 001, Question 1, wrong answer

### Understanding n Students × m Questions

- **n students**: Number of unique students (e.g., `student_001`, `student_002`)
- **m questions**: Number of questions (q01 through q10)
- **For each question**: You may have multiple answer types (good, less_good, wrong)

**Example:**
- 1 student (`student_001`)
- 10 questions (q01 through q10)
- 3 answer types per question (good, less_good, wrong)
- **Total**: 1 × 10 × 3 = 30 submission files

## Setup and Installation

### 1. Navigate to Project Directory

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
```

### 2. Install Dependencies

```bash
uv sync
```

This installs all required packages including:
- LlamaIndex (for RAG/retrieval)
- ChromaDB (for vector storage)
- PyYAML (for configuration)
- pypdf (for PDF processing)

### 3. Verify Installation

```bash
# Check that the CLI is accessible
uv run python -m grading_pipeline.cli --help
```

## Preparing Submissions

### Option 1: Create Submissions from Questions and Answers

If you have questions in `ten_questions.md` and answers in `ten_answers.md`:

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder

uv run python -m grading_pipeline.create_single_student_submissions \
    --student-id student_001 \
    --questions-file ten_questions.md \
    --answers-file ten_answers.md \
    --output-dir grading_pipeline/submissions
```

This creates 30 submission files (10 questions × 3 answer types).

### Option 2: Manual Submission Files

Create YAML files in `grading_pipeline/submissions/` with this structure:

```yaml
student_id: student_001
question_id: q01
question_text: "Your question text here"
rubric_version: "1.0"
answer: |
  Student's answer text here
  (can be multi-line)
metadata:
  created_at: "2026-01-17T10:30:00"
  rubric_path: "../../rubrics/q01.yaml"
  answer_type: good  # or "less_good" or "wrong"
```

## Running Grading

### Location of CLI

The CLI is located at: `grading_pipeline/cli.py`

You run it using: `uv run python -m grading_pipeline.cli`

### Basic Command Structure

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder

uv run python -m grading_pipeline.cli grade-question \
    --question <QUESTION_ID> \
    --student-id <STUDENT_ID> \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/<QUESTION_ID>_results.json
```

### Specifying Number of Students and Questions

#### Grade One Question for One Student

```bash
uv run python -m grading_pipeline.cli grade-question \
    --question q06 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

This will:
- Find all submissions for `student_001` and question `q06`
- Grade all answer types (good, less_good, wrong) together
- Save results to `q06_results.json`

#### Grade One Question for All Students

Omit `--student-id` to grade all students:

```bash
uv run python -m grading_pipeline.cli grade-question \
    --question q06 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

#### Grade Multiple Questions

Run the command multiple times, once per question:

```bash
# Grade q01
uv run python -m grading_pipeline.cli grade-question \
    --question q01 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q01_results.json

# Grade q03
uv run python -m grading_pipeline.cli grade-question \
    --question q03 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q03_results.json

# Grade q06
uv run python -m grading_pipeline.cli grade-question \
    --question q06 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

#### Grade Random Questions

```bash
uv run python -m grading_pipeline.cli grade-question \
    --random-questions 3 \
    --seed 42 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/random_results.json
```

This randomly selects 3 questions to grade.

### Command Options

| Option | Required | Description | Example |
|--------|----------|-------------|---------|
| `--question` | Yes* | Question ID to grade | `q06` |
| `--student-id` | No | Filter to specific student | `student_001` |
| `--rubrics-config` | Yes | Path to rubric config | `grading_pipeline/config/rubrics.yaml` |
| `--submissions-dir` | Yes | Directory with submission files | `grading_pipeline/submissions` |
| `--sources-config` | Yes | Path to sources config | `grading_pipeline/config/sources.yaml` |
| `--index-dir` | Yes | Directory for indexes | `grading_pipeline/tmp/chroma_db` |
| `--output` | Yes | Output JSON file path | `grading_pipeline/results/q06_results.json` |
| `--mode` | No | Execution mode | `sequential` (default) |
| `--log` | No | Optional log file path | `grading_pipeline/results/q06.log` |
| `--random-questions` | No | Number of random questions | `3` |
| `--seed` | No | Random seed | `42` |

*Required unless using `--random-questions`

### What Happens When You Run Grading

1. **Results Backup**: Previous results are backed up to `results_backup_YYYYMMDD_HHMMSS/`
2. **Results Cleanup**: The results folder is cleaned (old files removed)
3. **Index Loading**: Evidence indexes are loaded (or built if first time)
4. **Submission Loading**: All submissions for the specified question are loaded
5. **Grading**: Each submission is graded using:
   - Keyword matching (extracts keywords from answers)
   - Semantic similarity (RAG-based evidence retrieval)
   - Two-dimensional scoring (combines both methods)
6. **Results Writing**: Results are saved to JSON file

### Example Output

```
Backing up previous results to results_backup_20260117_163045...
Cleaning results folder...
✓ Results folder cleaned
Loaded 3 submission(s) for question q06 (student: student_001)
[Index Setup] Building or updating indexes...
[Index Setup] Indexed files:
  - grading_pipeline/sources/slides_data_type_quality.pdf
[Index Setup] Index ready in 1.09s
[Grading] Processing student_001 for q06...
[Grading] ✓ student_001 completed for q06
[Grading] Processing student_001 for q06...
[Grading] ✓ student_001 completed for q06
[Grading] Processing student_001 for q06...
[Grading] ✓ student_001 completed for q06

✓ Grading complete for q06: 3 successful, 0 failed
  Results written to: grading_pipeline/results/q06_results.json
```

## Understanding Results

### Results File Structure

Each results file (`q06_results.json`) contains:

```json
{
  "question_id": "q06",
  "graded_at": "2026-01-17T16:30:00",
  "total_students": 1,
  "successful": 3,
  "failed": 0,
  "students": [
    {
      "student_id": "student_001",
      "question_id": "q06",
      "score": 8,
      "max_score": 10,
      "rubric_items": [
        {
          "criterion_id": "correctness",
          "score": 5,
          "max_score": 6,
          "keyword_score": 0.75,
          "semantic_score": 0.82,
          "found_keywords": ["nominal", "ordinal", "interval"],
          "missing_keywords": ["ratio"]
        }
      ],
      "feedback": "...",
      "citations": ["file_slides_data_type_quality"],
      "timings": {
        "retrieve_evidence": 0.45,
        "apply_scoring": 0.12,
        "generate_feedback": 2.3,
        "total": 2.87
      }
    }
  ]
}
```

### Key Fields

- **score**: Total points awarded (out of max_score)
- **keyword_score**: Score from keyword matching (0-1)
- **semantic_score**: Score from semantic similarity (0-1)
- **found_keywords**: Keywords that matched
- **missing_keywords**: Keywords that were missing
- **feedback**: LLM-generated feedback with citations
- **citations**: Evidence sources used

## Common Workflows

### Workflow 1: Grade 3 Selected Questions for 1 Student

```bash
# Grade q01, q03, q06 for student_001
for question in q01 q03 q06; do
    uv run python -m grading_pipeline.cli grade-question \
        --question $question \
        --student-id student_001 \
        --rubrics-config grading_pipeline/config/rubrics.yaml \
        --submissions-dir grading_pipeline/submissions \
        --sources-config grading_pipeline/config/sources.yaml \
        --index-dir grading_pipeline/tmp/chroma_db \
        --output grading_pipeline/results/${question}_results.json
done
```

### Workflow 2: Grade All Questions for 1 Student

```bash
# Grade all 10 questions for student_001
for question in q01 q02 q03 q04 q05 q06 q07 q08 q09 q10; do
    uv run python -m grading_pipeline.cli grade-question \
        --question $question \
        --student-id student_001 \
        --rubrics-config grading_pipeline/config/rubrics.yaml \
        --submissions-dir grading_pipeline/submissions \
        --sources-config grading_pipeline/config/sources.yaml \
        --index-dir grading_pipeline/tmp/chroma_db \
        --output grading_pipeline/results/${question}_results.json
done
```

### Workflow 3: Grade One Question for Multiple Students

```bash
# Grade q06 for all students (omit --student-id)
uv run python -m grading_pipeline.cli grade-question \
    --question q06 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

### Workflow 4: Test with Random Questions

```bash
# Grade 3 random questions for student_001
uv run python -m grading_pipeline.cli grade-question \
    --random-questions 3 \
    --seed 42 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/random_results.json
```

## Troubleshooting

### Error: "Question ID 'q06' not found in rubric config"

**Solution**: Make sure the question exists in `grading_pipeline/config/rubrics.yaml`:

```yaml
rubrics:
  q06:
    path: "../../rubrics/q06.yaml"
    description: "Question 6: ..."
```

### Error: "No submissions found for question 'q06'"

**Solution**: Check that submission files exist:
```bash
ls grading_pipeline/submissions/student_*_q06*.yaml
```

### Error: "Metadata length (2481) is longer than chunk size (512)"

**Solution**: This is fixed automatically. Keywords are now limited to prevent this error. If you see it, rebuild indexes:

```bash
# Delete old indexes and rebuild
rm -rf grading_pipeline/tmp/chroma_db/*
```

### Results Folder Not Cleaned

**Solution**: The cleanup happens automatically at the start of each run. If you see old results, they should be in `results_backup_*/` folders.

### Index Building Takes Too Long

**Solution**: Indexes are built incrementally. First run builds indexes (~1-2 seconds), subsequent runs load instantly (~0.14 seconds) if nothing changed.

## Quick Reference

### Most Common Command

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder

uv run python -m grading_pipeline.cli grade-question \
    --question q06 \
    --student-id student_001 \
    --rubrics-config grading_pipeline/config/rubrics.yaml \
    --submissions-dir grading_pipeline/submissions \
    --sources-config grading_pipeline/config/sources.yaml \
    --index-dir grading_pipeline/tmp/chroma_db \
    --output grading_pipeline/results/q06_results.json
```

### File Locations

- **CLI**: `grading_pipeline/cli.py` (run with `python -m grading_pipeline.cli`)
- **Submissions**: `grading_pipeline/submissions/`
- **Results**: `grading_pipeline/results/`
- **Rubrics**: `rubrics/q01.yaml`, `rubrics/q02.yaml`, etc.
- **Config**: `grading_pipeline/config/rubrics.yaml`, `grading_pipeline/config/sources.yaml`

### Understanding the Output

- **"Loaded 3 submission(s) for question q06 (student: student_001)"**: Found 3 files (good, less_good, wrong)
- **"✓ student_001 completed for q06"**: One submission graded successfully
- **"Results written to: q06_results.json"**: All results saved to this file

## Next Steps

1. **Create submissions** using `create_single_student_submissions.py`
2. **Grade questions** using the CLI commands above
3. **Review results** in `grading_pipeline/results/`
4. **Compare scores** across answer types (good should score highest)

For more details, see:
- `grading_pipeline/EXAMPLES.md` - Detailed examples
- `grading_pipeline/README.md` - Technical documentation
- `grading_pipeline/QUICK_START.md` - Quick reference
