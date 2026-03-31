# Running the T4.3 Benchmark

## Prerequisites

All commands run from `autograder/`.

## Input files

| File | Purpose |
|------|---------|
| `grading_pipeline/sources/slides_data_type_quality.pdf` | Evidence corpus (pre-indexed) |
| `grading_pipeline/submissions/student_001_q0{1-5}_{good,less_good,wrong}.yaml` | Synthetic answer files |
| `grading_dynamic_rubrics/config/rubrics.yaml` | Rubric definitions |
| `grading_dynamic_rubrics/config/sources.yaml` | Index/retrieval config |
| `grading_dynamic_rubrics/tmp/in_memory_indexes/` | Pre-built vector indexes (reused automatically) |

## Run the benchmark

```bash
.venv/bin/python t4_3_grading_sample.py
```

Optional flags:

```bash
# Subset of questions (default: q01–q05)
.venv/bin/python t4_3_grading_sample.py --questions q01 q02 q03

# Custom output path (default: t4_3_report.md, overwritten each run)
.venv/bin/python t4_3_grading_sample.py --output results/my_report.md
```

## Output files

| File | Contents |
|------|---------|
| `t4_3_report.md` | Human-readable comparison of `int`/`round`/`float` scoring across 2 runs |
| `grading_dynamic_rubrics/results/t4_3/t4_3_run1.json` | Raw grading data, run 1 |
| `grading_dynamic_rubrics/results/t4_3/t4_3_run2.json` | Raw grading data, run 2 |
| `grading_dynamic_rubrics/results/t4_3/t4_3_results.json` | Combined results |

## What the report checks

For each question × answer type, it compares scores under three methods:

- **`int`** — `int(score × max_pts)` — current pipeline (truncates)
- **`round`** — `round(score × max_pts)` — proposed fix
- **`float`** — `score × max_pts` as float — no rounding

A question **passes** if `good ≥ less_good ≥ wrong` for both runs.

## Key pipeline switches (edit before running)

| File | Variable | Values |
|------|----------|--------|
| `grading_dynamic_rubrics/pipeline.py` | `SEMANTIC_SCORING_MODE` | `"count"` (default) or `"reranker"` (P3) |
