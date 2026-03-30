# Project State — autograder / dynamic_rubrics branch

**Last updated:** 2026-03-30
**Branch:** `dynamic_rubrics`
**Last commit:** T2.4 (deduplication)

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
| T2.2 | `grading_pipeline/check_extraction.py`, `rubric_schema.py` | `45b1b35` | Extracts Check objects from LLM JSON; rubric_schema updated for new template |
| T2.3 | `grading_pipeline/categorization.py`, `tests/test_categorization.py` | T2.3 | Validate/override check categories; load from grading_categories.yaml; 3 strategies (error/default/fuzzy) |
| T2.4 | `grading_pipeline/deduplication.py`, `tests/test_deduplication.py` | T2.4 | Remove duplicate checks; injectable similarity_fn; threshold=0.85; DeduplicationResult with metadata |
| T6.1 | `config/llm_config.py` | earlier | llama.cpp provider (inactive); Ollama path verified |
| T11.1 | `llamacpp_ollama/TASK_LIST.md` | earlier | Already closed; Ollama decision documented |

---

## Open Tasks

### Phase 2 — Rubric Generation (T2.2 done, T2.3 next)

- [x] **T2.1** — Rubric generation prompt template updated
- [x] **T2.2** — Check extraction implemented (`check_extraction.py`, `rubric_schema.py`)
- [x] **T2.3** — Category validation (`categorization.py`); validates against YAML config, supports error/default/fuzzy strategies
- [x] **T2.4** — Deduplication (`deduplication.py`); injectable similarity_fn, threshold param, DeduplicationResult with removed_pairs metadata
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

1. **Reranking indices** — Per commit `3df9dbf`, reranking was run for at least one question.
   Confirm which questions have reranked indices before building T3.1 (evaluation pipeline).

3. **grade-spec.md** — Per `CLAUDE.md`, any grading logic changes require updating
   `grade-spec.md` first. Locate and review before starting T3.x.

---

## Next time, start by…

1. Implement **T2.5** (integrate full pipeline in `rubric_generator.py`) — chain generate → extract → categorize → deduplicate.
