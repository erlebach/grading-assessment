# Data Storage Structure

Runtime artifacts for the weighted checklist grading pipeline.

## Directory Layout

```
data/
├── rubrics/
│   ├── raw/          # LLM-generated rubrics before any post-processing
│   ├── extracted/    # Checks extracted from raw dimensions
│   ├── categorized/  # Checks with category assignments applied
│   └── deduped/      # Final deduplicated check sets (canonical rubrics)
├── grades/
│   ├── evaluations/  # Per-check evaluation results (CheckEvaluation records)
│   └── final/        # Final GradeResult records (one per student/question/version)
├── appeals/          # Appeal records (one per appeal submission)
└── logs/             # Grading run logs and error traces
```

## File Naming Conventions

### Rubrics
| Stage | Pattern | Example |
|-------|---------|---------|
| raw | `{question_id}_rubric_raw_v{N}.json` | `q01_rubric_raw_v1.json` |
| extracted | `{question_id}_rubric_extracted_v{N}.json` | `q01_rubric_extracted_v1.json` |
| categorized | `{question_id}_rubric_categorized_v{N}.json` | `q01_rubric_categorized_v1.json` |
| deduped | `{question_id}_rubric_v{N}.json` | `q01_rubric_v1.json` |

### Grades
| Type | Pattern | Example |
|------|---------|---------|
| evaluations | `{student_id}_{question_id}_evals_v{N}.json` | `student_001_q01_evals_v1.json` |
| final | `{student_id}_{question_id}_grade_v{N}.json` | `student_001_q01_grade_v1.json` |

### Appeals
| Pattern | Example |
|---------|---------|
| `appeal_{student_id}_{question_id}_v{N}_{ISO_timestamp}.json` | `appeal_student_001_q01_v1_2026-03-30T14:22:00.json` |

### Logs
| Pattern | Example |
|---------|---------|
| `grading_run_{ISO_timestamp}.log` | `grading_run_2026-03-30T14:00:00.log` |

## Versioning Rules

- `v1` is the original grade. Appeals increment: `v2`, `v3`, etc.
- Rubric versions increment when the instructor modifies the rubric after grading begins.
- Never overwrite existing versioned files — always write a new version.
- ISO timestamps in appeal filenames use `T` separator, no microseconds.
