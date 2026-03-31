# Running the T4.3 Benchmark

All commands run from `autograder/`.

---

## Step 1 — Generate rubrics (LLM call, slow)

Only needed when rubrics don't exist or you want to regenerate them.

```bash
.venv/bin/python -m grading_pipeline.create_dynamic_rubrics_for_each_question \
  --source-file grading_pipeline/sources/slides_data_type_quality.pdf \
  --questions-file ten_questions.md \
  --rubrics-dir rubrics_dynamic
```

Optional flags:
- `--start-from 3` — regenerate from q03 onward
- `--llm-provider anthropic` / `--llm-model claude-...` — override LLM
- `--dry-run` — preview without calling LLM

**Input:**

| File | Purpose |
|------|---------|
| `grading_pipeline/sources/slides_data_type_quality.pdf` | Source material for rubric context |
| `ten_questions.md` | Exam questions |

**Output** (written to `rubrics_dynamic/`):

| File | Contents |
|------|---------|
| `rubrics_dynamic/yaml/q0N.yaml` | Rubric used by the pipeline |
| `rubrics_dynamic/json/q0N_raw.json` | Raw LLM output |
| `rubrics_dynamic/json/q0N_converted.json` | Converted grading structure |
| `rubrics_dynamic/json/q0N_title_description_converted.json` | Criterion titles/descriptions |

> Note: output directories are emptied before writing new rubrics.

---

## Step 2 — Run scoring benchmark (fast, no LLM)

Grades 3 answer types (good / less_good / wrong) for each question,
compares `int` / `round` / `float` scoring, runs twice for reproducibility.

```bash
.venv/bin/python t4_3_grading_sample.py
```

Optional flags:
```bash
# Subset of questions (default: q01–q05)
.venv/bin/python t4_3_grading_sample.py --questions q01 q02 q03

# Custom output path — use this to preserve old results before re-running
.venv/bin/python t4_3_grading_sample.py --output results/my_report.md
```

**Input:**

| File | Purpose |
|------|---------|
| `grading_pipeline/submissions/student_001_q0{1-5}_{good,less_good,wrong}.yaml` | Synthetic answers |
| `rubrics_dynamic/yaml/q0N.yaml` | Rubrics (from step 1) |
| `grading_dynamic_rubrics/config/rubrics.yaml` | Maps question IDs to rubric files |
| `grading_dynamic_rubrics/config/sources.yaml` | Index/retrieval config |
| `grading_dynamic_rubrics/tmp/in_memory_indexes/` | Pre-built vector indexes (reused automatically) |

**Output:**

| File | Contents |
|------|---------|
| `t4_3_report.md` | Human-readable scoring comparison (**overwritten each run**) |
| `grading_dynamic_rubrics/results/t4_3/t4_3_run1.json` | Raw grading data, run 1 |
| `grading_dynamic_rubrics/results/t4_3/t4_3_run2.json` | Raw grading data, run 2 |
| `grading_dynamic_rubrics/results/t4_3/t4_3_results.json` | Combined results |

A question **passes** if `good ≥ less_good ≥ wrong` for both runs.

---

## Step 3 — Run feedback generation (LLM call, slow)

Generates per-student feedback with citations for a single question.

```bash
bash grading_pipeline/run_grading.sh student_001 q01
```

Or directly:

```bash
.venv/bin/python -m grading_pipeline.cli grade-student \
  --question q01 \
  --submission grading_pipeline/submissions/student_001_q01_good.yaml \
  --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \
  --sources-config grading_dynamic_rubrics/config/sources.yaml \
  --index-dir grading_dynamic_rubrics/tmp/in_memory_indexes \
  --index-backend in-memory \
  --output grading_pipeline/results/q01_student_001_good.json
```

Run all three answer types to compare feedback quality:
```bash
for atype in good less_good wrong; do
  .venv/bin/python -m grading_pipeline.cli grade-student \
    --question q01 \
    --submission grading_pipeline/submissions/student_001_q01_${atype}.yaml \
    --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \
    --sources-config grading_dynamic_rubrics/config/sources.yaml \
    --index-dir grading_dynamic_rubrics/tmp/in_memory_indexes \
    --index-backend in-memory \
    --output grading_pipeline/results/q01_student_001_${atype}.json
done
```

**Output** (`grading_pipeline/results/q0N_student_NNN_TYPE.json`):

```
{
  "student_id": ...,
  "score": ...,
  "max_score": ...,
  "feedback": "...",       ← narrative feedback with citations
  "citations": [...],
  "rubric_items": [...]    ← per-criterion breakdown
}
```

---

## Key switches (edit before running)

| File | Variable | Effect |
|------|----------|--------|
| `grading_dynamic_rubrics/pipeline.py` | `SEMANTIC_SCORING_MODE = "count"` | Uses evidence count for semantic score (default) |
| `grading_dynamic_rubrics/pipeline.py` | `SEMANTIC_SCORING_MODE = "reranker"` | Uses reranker-weighted semantic score (P3) |
