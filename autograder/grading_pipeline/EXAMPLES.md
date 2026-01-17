# Grading Pipeline Examples

This document provides detailed examples for using the batch-by-question grading pipeline.

## Table of Contents

1. [Configuration](#configuration)
2. [Submission Format](#submission-format)
3. [Workflow Examples](#workflow-examples)
4. [Driving Script Examples](#driving-script-examples)
5. [Spot-Checking Guide](#spot-checking-guide)

## Configuration

### Rubric Configuration File

Create `grading_pipeline/config/rubrics.yaml`:

```yaml
# Rubric path configuration
rubrics:
  q01:
    path: "../../rubrics/q01.yaml"
    description: "Question 1: Mutual Information"
  q02:
    path: "../../rubrics/q02.yaml"
    description: "Question 2: Data Quality"
```

**Key Points:**
- Paths can be relative (resolved relative to config file directory) or absolute
- Each question ID maps to a rubric file path
- Descriptions are optional but helpful for documentation

### Sources Configuration

The sources configuration (`grading_pipeline/config/sources.yaml`) defines what documents to index for evidence retrieval:

```yaml
sources:
  - type: "file"
    path: "grading_pipeline/sources"
    patterns: ["*.pdf"]
    metadata:
      source_type: "slide"
      description: "Data type and quality lecture slides"
```

## Submission Format

### Self-Contained Submission Structure

Each submission is a YAML file named `student_XXX_qYY.yaml`:

```yaml
student_id: "student_001"
question_id: "q01"
question_text: "Explain mutual information and its relationship to entropy"
rubric_version: "1.0"
answer: |
  Mutual information I(X;Y) measures the reduction in uncertainty
  about variable X when we observe variable Y. It quantifies the
  amount of information obtained about one random variable through
  observing the other random variable.
  
  The relationship to entropy is that mutual information can be
  expressed as:
  
  I(X;Y) = H(X) - H(X|Y)
  
  where H(X) is the entropy of X and H(X|Y) is the conditional
  entropy of X given Y.
metadata:
  created_at: "2026-01-17T10:30:00"
  rubric_path: "grading_pipeline/rubrics/q01.yaml"
```

**Required Fields:**
- `student_id`: Unique student identifier
- `question_id`: Question identifier (must match rubric config)
- `question_text`: Full question text (for spot-checking)
- `answer`: Student's answer (can be multi-line)

**Optional Fields:**
- `rubric_version`: Version from rubric metadata
- `metadata`: Additional metadata (created_at, rubric_path, etc.)

### Example Rubric File

Example rubric file (`rubrics/q01.yaml`):

```yaml
question_id: "q01"
question_text: "Explain mutual information and its relationship to entropy"
total_points: 10

criteria:
  - criterion_id: "definition"
    description: "Correctly defines mutual information"
    points: 4
    evidence_required: true
    evaluation_method: "semantic"
  
  - criterion_id: "properties"
    description: "Explains key properties like non-negative and symmetric"
    points: 3
    evidence_required: true
    evaluation_method: "semantic"
  
  - criterion_id: "entropy_relation"
    description: "Relates mutual information to entropy concepts"
    points: 3
    evidence_required: true
    evaluation_method: "semantic"

metadata:
  course: "CS101"
  assignment: "hw01"
  version: "1.0"
```

## Workflow Examples

### Example 1: Grade All Students for One Question

**Step 1**: Prepare submissions (see Driving Script Examples below)

**Step 2**: Run grading pipeline

```bash
python -m grading_pipeline.cli grade-question \
  --question q01 \
  --rubrics-config grading_pipeline/config/rubrics.yaml \
  --submissions-dir grading_pipeline/submissions \
  --sources-config grading_pipeline/config/sources.yaml \
  --index-dir grading_pipeline/tmp/chroma_db \
  --output results/q01_results.json \
  --log results/q01_grading.log
```

**Output:**
- `results/q01_results.json`: Batch results for all students
- `results/q01_grading.log`: Detailed logging output

**What Happens:**
1. Loads rubric config and finds rubric path for q01
2. Loads all submissions for q01 from submissions directory
3. Builds or updates indexes (incremental, fast if unchanged)
4. Loads rubric once for the batch
5. Grades each student sequentially
6. Writes results to JSON file

### Example 2: Grade a Single Student

```bash
python -m grading_pipeline.cli grade-student \
  --rubrics-config grading_pipeline/config/rubrics.yaml \
  --submission grading_pipeline/submissions/student_001_q01.yaml \
  --sources-config grading_pipeline/config/sources.yaml \
  --index-dir grading_pipeline/tmp/chroma_db \
  --output results/student_001_q01.json
```

**Note**: Single student grading uses the same batch pipeline with a batch size of 1, ensuring consistency.

### Example 3: Using Python API

```python
from pathlib import Path
from grading_pipeline.pipeline import grade_question_batch, write_results
from grading_pipeline.submission_loader import load_all_submissions_for_question
from grading_pipeline.config_loader import get_rubric_path

# Setup paths
rubrics_config = Path("grading_pipeline/config/rubrics.yaml")
submissions_dir = Path("grading_pipeline/submissions")
sources_config = Path("grading_pipeline/config/sources.yaml")
index_dir = Path("grading_pipeline/tmp/chroma_db")
output_path = Path("results/q01_results.json")

# Get rubric path
rubric_path = get_rubric_path("q01", rubrics_config)

# Load submissions
submissions = load_all_submissions_for_question(submissions_dir, "q01")

# Grade batch
results = grade_question_batch(
    question_id="q01",
    rubric_path=rubric_path,
    submissions=submissions,
    persist_dir=index_dir,
    config_path=sources_config,
    execution_mode="sequential",
)

# Write results
write_results(results, "q01", output_path)
```

## Driving Script Examples

### Example 1: Basic Conversion Script

```python
from pathlib import Path
import yaml
from grading_pipeline.submission_converter import create_self_contained_submission

# Simple student data
students_data = [
    {
        "student_id": "student_001",
        "question_id": "q01",
        "answer": "Mutual information measures the reduction in uncertainty...",
    },
    {
        "student_id": "student_002",
        "question_id": "q01",
        "answer": "I think mutual information is related to entropy...",
    },
]

# Convert to self-contained submissions
rubrics_config = Path("grading_pipeline/config/rubrics.yaml")
output_dir = Path("grading_pipeline/submissions")
output_dir.mkdir(parents=True, exist_ok=True)

for student_data in students_data:
    submission = create_self_contained_submission(
        student_id=student_data["student_id"],
        question_id=student_data["question_id"],
        answer=student_data["answer"],
        rubrics_config_path=rubrics_config,
    )
    
    output_file = output_dir / f"{submission['student_id']}_{submission['question_id']}.yaml"
    with open(output_file, "w") as f:
        yaml.dump(submission, f, default_flow_style=False, sort_keys=False)
```

### Example 2: Reading from CSV

```python
import csv
from pathlib import Path
import yaml
from grading_pipeline.submission_converter import create_self_contained_submission

# Read from CSV
with open("student_answers.csv", "r") as f:
    reader = csv.DictReader(f)
    students_data = list(reader)

# Convert each row
rubrics_config = Path("grading_pipeline/config/rubrics.yaml")
output_dir = Path("grading_pipeline/submissions")
output_dir.mkdir(parents=True, exist_ok=True)

for row in students_data:
    submission = create_self_contained_submission(
        student_id=row["student_id"],
        question_id=row["question_id"],
        answer=row["answer"],
        rubrics_config_path=rubrics_config,
    )
    
    output_file = output_dir / f"{submission['student_id']}_{submission['question_id']}.yaml"
    with open(output_file, "w") as f:
        yaml.dump(submission, f, default_flow_style=False, sort_keys=False)
```

### Example 3: Batch Conversion for Multiple Questions

```python
from pathlib import Path
import yaml
from grading_pipeline.submission_converter import create_self_contained_submission

# Students with answers for multiple questions
students_answers = {
    "student_001": {
        "q01": "Answer for question 1...",
        "q02": "Answer for question 2...",
    },
    "student_002": {
        "q01": "Answer for question 1...",
        "q02": "Answer for question 2...",
    },
}

rubrics_config = Path("grading_pipeline/config/rubrics.yaml")
output_dir = Path("grading_pipeline/submissions")
output_dir.mkdir(parents=True, exist_ok=True)

for student_id, answers in students_answers.items():
    for question_id, answer in answers.items():
        submission = create_self_contained_submission(
            student_id=student_id,
            question_id=question_id,
            answer=answer,
            rubrics_config_path=rubrics_config,
        )
        
        output_file = output_dir / f"{submission['student_id']}_{submission['question_id']}.yaml"
        with open(output_file, "w") as f:
            yaml.dump(submission, f, default_flow_style=False, sort_keys=False)
```

## Spot-Checking Guide

### Verifying Submission Format

Check that submissions have all required fields:

```python
from pathlib import Path
import yaml
from grading_pipeline.submission_loader import load_submission

submission_path = Path("grading_pipeline/submissions/student_001_q01.yaml")
submission = load_submission(submission_path)

# Verify required fields
assert "student_id" in submission
assert "question_id" in submission
assert "question_text" in submission
assert "answer" in submission
```

### Verifying Rubric Configuration

Check that rubric paths resolve correctly:

```python
from pathlib import Path
from grading_pipeline.config_loader import get_rubric_path

rubrics_config = Path("grading_pipeline/config/rubrics.yaml")
rubric_path = get_rubric_path("q01", rubrics_config)

assert rubric_path.exists()
print(f"Rubric path: {rubric_path}")
```

### Checking Index Status

Verify that indexes are built and up-to-date:

```python
from pathlib import Path
from grading_pipeline.manifest import load_manifest

index_dir = Path("grading_pipeline/tmp/chroma_db")
manifest = load_manifest(index_dir)

print(f"Indexed sources: {len(manifest.get('sources', {}))}")
for source_id, source_info in manifest.get("sources", {}).items():
    print(f"  {source_id}: {source_info['file_path']}")
```

### Reviewing Results

Check grading results for errors:

```python
import json
from pathlib import Path

results_path = Path("results/q01_results.json")
with open(results_path) as f:
    results = json.load(f)

print(f"Total students: {results['total_students']}")
print(f"Successful: {results['successful']}")
print(f"Failed: {results['failed']}")

# Check for errors
for student_result in results["students"]:
    if "error" in student_result:
        print(f"Error for {student_result['student_id']}: {student_result['error']}")
```

## Troubleshooting

### Common Issues

1. **"Question ID not found in rubric config"**
   - Check that question_id exists in `config/rubrics.yaml`
   - Verify question_id matches exactly (case-sensitive)

2. **"Rubric file not found"**
   - Check that rubric path in config is correct
   - Verify path is relative to config file directory or absolute

3. **"No submissions found for question"**
   - Check that submission files exist in submissions directory
   - Verify question_id in submission files matches the requested question

4. **"Submission missing required fields"**
   - Ensure all required fields are present: student_id, question_id, question_text, answer
   - Check YAML syntax is valid

### Debug Mode

Enable detailed logging by specifying a log file:

```bash
python -m grading_pipeline.cli grade-question \
  --question q01 \
  ... \
  --log results/debug.log
```

Check the log file for detailed processing information and error messages.
