# Data Storage Structure

Document describing the directory organization for the weighted checklist grading system.

## Overview

All grading data is organized in a configurable base directory (default: `grading_results/`) with subdirectories for:
- **rubrics** - Rubric definitions
- **grades** - Student grades
- **appeals** - Grade appeals
- **logs** - System logs

## Directory Layout

```
grading_results/
├── rubrics/
│   ├── q01/
│   │   ├── rubric_v1.json
│   │   ├── rubric_v2.json
│   │   └── ...
│   ├── q02/
│   │   └── rubric_v1.json
│   └── ...
├── grades/
│   ├── q01/
│   │   ├── student_001_v1.json
│   │   ├── student_001_v2.json  # Appeal version
│   │   ├── student_002_v1.json
│   │   └── ...
│   ├── q02/
│   │   └── ...
│   └── ...
├── appeals/
│   ├── q01/
│   │   ├── student_001_appeal_v1.json
│   │   ├── student_001_appeal_v2.json
│   │   └── ...
│   └── ...
└── logs/
    ├── 2026-01-26.log
    └── 2026-01-27.log
```

## Naming Conventions

### Rubrics

**Pattern:** `{base}/rubrics/{question_id}/rubric_v{version}.json`

**Examples:**
- `rubrics/q01/rubric_v1.json` - First rubric for question 01
- `rubrics/q02/rubric_v2.json` - Second version of rubric for question 02

**Usage:**
```python
storage.save_rubric(rubric)  # Auto-determines path based on rubric.question_id and rubric.version
storage.load_rubric("q01", version=1)  # Load specific version
storage.load_rubric("q01", version=-1)  # Load latest version
```

### Grades

**Pattern:** `{base}/grades/{question_id}/{student_id}_v{version}.json`

**Examples:**
- `grades/q01/student_001_v1.json` - Original grade
- `grades/q01/student_001_v2.json` - Grade after appeal (version 2)
- `grades/q01/student_002_v1.json` - Another student's original grade

**Version tracking:**
- `v1` = Original grade
- `v2` = First appeal/adjustment
- `v3` = Second appeal/adjustment
- etc.

**Constraint:** Versions must be sequential and each version represents an increase in score (only upward adjustments).

**Usage:**
```python
storage.save_grade(grade)  # Auto-determines path
storage.load_grade("q01", "student_001", version=1)  # Load original
storage.load_grade("q01", "student_001", version=-1)  # Load latest
storage.list_grade_versions("q01", "student_001")  # [1, 2] for original + appeal
storage.list_grades_for_question("q01")  # [("student_001", [1,2]), ("student_002", [1]), ...]
```

### Appeals

**Pattern:** `{base}/appeals/{question_id}/{student_id}_appeal_v{version}.json`

**Examples:**
- `appeals/q01/student_001_appeal_v1.json` - First appeal
- `appeals/q01/student_001_appeal_v2.json` - Second appeal (for same question/student)
- `appeals/q02/student_001_appeal_v1.json` - Appeal for different question

**Relationship to grades:**
- Appeal v1 is referenced by grade v2
- Appeal v2 is referenced by grade v3
- etc.

**Usage:**
```python
storage.save_appeal(appeal)  # Auto-determines path
storage.load_appeal("q01", "student_001", appeal_version=1)
storage.load_appeal("q01", "student_001", appeal_version=-1)  # Latest
storage.list_appeals_for_student("q01", "student_001")  # [1, 2] for both appeals
```

### Logs

**Pattern:** `{base}/logs/{YYYY-MM-DD}.log`

**Examples:**
- `logs/2026-01-26.log` - Today's log
- `logs/2026-01-25.log` - Yesterday's log

**Content:** One log entry per line with ISO timestamp and message.

**Example entry:**
```
[2026-01-26T14:23:45.123456] Graded student_001 on q01: 8.5/10
[2026-01-26T14:23:46.234567] Appeal approved for student_001 on q01: 8.5 -> 9.0
```

**Usage:**
```python
storage.write_log("Grading completed")  # Writes to today's log
storage.get_log_file()  # Get today's log file path
storage.get_log_file(datetime(2026, 1, 25))  # Get specific date
```

## File Format

### Rubric JSON

```json
{
  "id": "q01_rubric_v1",
  "question_id": "q01",
  "title": "Understanding Object-Oriented Concepts",
  "description": "...",
  "checks": [
    {
      "id": "q01_check_1",
      "text": "Student defines 'object' correctly",
      "category": "semantic",
      "weight": 1.0,
      "question_id": "q01"
    }
  ],
  "total_points": 10,
  "created_at": "2026-01-26T10:00:00",
  "version": 1
}
```

### Grade JSON

```json
{
  "id": "student_001_q01_v1",
  "question_id": "q01",
  "student_id": "student_001",
  "rubric_id": "q01_rubric_v1",
  "rubric_version": 1,
  "check_evaluations": [
    {
      "check_id": "q01_check_1",
      "result": "pass",
      "score": 1.0,
      "evidence": "Student correctly stated: 'An object is a collection of attributes'",
      "confidence": 1.0
    }
  ],
  "calculation": {
    "total_checks": 5,
    "checks_passed": 4,
    "checks_failed": 1,
    "weighted_sum": 7.2,
    "weight_denominator": 8.0,
    "final_score": 9.0
  },
  "final_score": 9.0,
  "graded_at": "2026-01-26T10:05:00",
  "version": 1
}
```

### Appeal JSON

```json
{
  "id": "appeal_student_001_q01_v1",
  "original_grade_id": "student_001_q01_v1",
  "student_id": "student_001",
  "question_id": "q01",
  "original_score": 9.0,
  "new_score": 9.5,
  "reason": "Disagreement with evaluation of check_2 (should be pass, not fail)",
  "decision": "approved",
  "instructor_notes": "Reviewer confirmed: check evaluation was incorrect",
  "requested_at": "2026-01-26T10:10:00",
  "decided_at": "2026-01-26T10:15:00"
}
```

## Version Management

### Grade Versions

Grades use sequential versioning to track appeals:
- **Original (v1):** Initial grading result
- **Appeal v1 (v2):** Grade after first appeal
- **Appeal v2 (v3):** Grade after second appeal
- etc.

**Constraint:** Each version must have a score >= previous version (only upward adjustments).

### Rubric Versions

Rubrics use sequential versioning if updated:
- **v1:** Initial rubric generation
- **v2:** Updated rubric (if regenerated with changes)
- etc.

Grades always reference the rubric version they were graded with (`rubric_version` field).

## Reproducibility and Audit Trail

The storage structure enables complete reproducibility:

1. **Check Evaluations:** All check pass/fail results stored with evidence
2. **Calculation Details:** Score calculation fully documented in `GradeCalculation`
3. **Version History:** Can load any previous version of grade or appeal
4. **Audit Trail:** All grading and appeal decisions logged with timestamps
5. **No Re-evaluation Needed:** Can recalculate scores with new weights without LLM re-invocation

## Storage Configuration

Configure storage via `config/grading_config.yaml`:

```yaml
storage:
  base_directory: "grading_results"  # Can override with CLI
  rubrics_directory: "rubrics"
  grades_directory: "grades"
  appeals_directory: "appeals"
  logs_directory: "logs"
```

## Storage Manager API

### Basic Usage

```python
from grading_pipeline.storage import StorageManager

# Initialize
storage = StorageManager("grading_results")

# Save/load rubrics
storage.save_rubric(rubric)
rubric = storage.load_rubric("q01", version=1)

# Save/load grades
storage.save_grade(grade)
grade = storage.load_grade("q01", "student_001", version=1)

# Save/load appeals
storage.save_appeal(appeal)
appeal = storage.load_appeal("q01", "student_001", appeal_version=1)

# Logging
storage.write_log("Grading completed for q01")

# Statistics
stats = storage.get_storage_stats()
```

## Size Considerations

Each data file is typically small (JSON):
- Rubric: ~5-10 KB
- Grade: ~3-5 KB
- Appeal: ~2-3 KB
- Log entries: ~100 bytes each

For 100 students × 10 questions:
- Rubrics: ~1 MB (10 files)
- Grades (original): ~3-5 MB (1000 files)
- Grades + appeals (with 2 appeals per student): ~9-15 MB (3000 files)
- Total: ~15-25 MB

Easily manageable for typical deployments.
