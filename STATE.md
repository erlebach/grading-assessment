# Project State — autograder / dynamic_rubrics branch

**Last updated:** 2026-03-30
**Branch:** `dynamic_rubrics`
**Last commit:** `8b2d3d9` (T2.1)

---

## Narrative Recap

The project is an LLM-based autograder for short-answer questions. Work is proceeding on
a new **weighted checklist grading architecture** where rubrics are decomposed into discrete,
categorized, binary checks, each carrying a weight. The pipeline is:

> Generate rubric → Extract checks → Assign categories → Deduplicate → Evaluate per student → Score

### LLM Provider Decision (concluded 2026-01-29)

Ollama (`gpt-oss:20b`) is the chosen provider. llama.cpp was abandoned due to GBNF grammar
hangs and unfiltered thinking-chain output. Ollama filters `<|channel|>` blocks internally
and returns clean JSON. Smoke-tested 2026-03-30 — confirmed working.

**Known constraint:** Only one Ollama instance on macOS at a time. Grading is sequential.

---

## Completed Tasks

| Task | File(s) | Commit | Notes |
|------|---------|--------|-------|
| T1.1 | `config/grading_categories.yaml`, `config/grading_config.yaml` | earlier | YAML configs |
| T1.2 | `grading_pipeline/models.py`, `schemas.py` | `5fe539f` | Pydantic V2 models: Check, Rubric, CheckEvaluation, GradeResult, Appeal |
| T1.3 | `data/` directory tree | `395d1ff` | Storage dirs created; naming conventions in `data/README.md` |
| T2.1 | `grading_pipeline/rubric_generator_template.txt` | `8b2d3d9` | Updated for check-based output with `category` + `checks[]` per dimension |
| T2.2 | `grading_pipeline/check_extraction.py`, `rubric_schema.py` | (next commit) | Extracts Check objects from LLM JSON; rubric_schema updated for new template |
| T6.1 | `config/llm_config.py` | earlier | llama.cpp provider (inactive); Ollama path verified |
| T11.1 | `llamacpp_ollama/TASK_LIST.md` | earlier | Already closed; Ollama decision documented |

---

## Open Tasks

### Phase 2 — Rubric Generation (T2.2 done, T2.3 next)

- [x] **T2.1** — Rubric generation prompt template updated
- [x] **T2.2** — Check extraction implemented (`check_extraction.py`, `rubric_schema.py`)
- [ ] **T2.3** — Category assignment
  → file: `grading_pipeline/categorization.py` (create)
  → Note: categories are now embedded in the rubric template output — T2.3 may reduce
    to validation/override logic rather than a separate LLM call
- [ ] **T2.4** — Deduplication
  → file: `grading_pipeline/deduplication.py` (create)
- [ ] **T2.5** — Integrate full rubric generation pipeline
  → file: `grading_pipeline/rubric_generator.py` (update/create)

### Phase 3 — Evaluation & Scoring (depends on Phase 2)

- [ ] **T3.1** — Check evaluation via LLM
  → file: `grading_dynamic_rubrics/check_evaluation.py` (create)
- [ ] **T3.2** — Hybrid evaluation with human override
  → file: `grading_dynamic_rubrics/check_evaluation.py` (update)
- [ ] **T3.3** — Scoring algorithm
  → file: `grading_dynamic_rubrics/scoring.py` (create)
- [ ] **T3.4** — Grade storage and appeal tracking
  → file: `grading_dynamic_rubrics/grade_storage.py` (create)

---

## Blockers & Open Questions

1. **T2.3 scope** — Categories are now produced by the LLM prompt directly (T2.1 template).
   T2.3 may only need to validate/override categories rather than call the LLM again.
   Confirm approach before implementing.

2. **Reranking indices** — Per commit `3df9dbf`, reranking was run for at least one question.
   Confirm which questions have reranked indices before building T3.1 (evaluation pipeline).

3. **grade-spec.md** — Per `CLAUDE.md`, any grading logic changes require updating
   `grade-spec.md` first. Locate and review before starting T3.x.

---

## Next time, start by…

1. Implement **T2.3** (category assignment / validation) — scope is likely small since the
   LLM template already embeds categories; may just need a validation + fallback path.
2. Then **T2.4** (deduplication) — remove semantically redundant checks across dimensions.
3. Then **T2.5** (integrate full pipeline in `rubric_generator.py`).
