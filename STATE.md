# Project State — autograder / dynamic_rubrics branch

**Last updated:** 2026-03-30
**Branch:** `dynamic_rubrics`
**Last commit:** `7806625` (2026-01-29)

---

## Narrative Recap

The project is an LLM-based autograder for short-answer questions. Work was proceeding on two fronts simultaneously:

### 1. Weighted Checklist Grading System (main effort)

A new grading architecture was designed (see `TASK_LIST.md`) where rubrics are decomposed into discrete, categorized checks, each carrying a weight. The pipeline is:

> Generate rubric → Extract checks → Assign categories → Deduplicate → Evaluate per student → Score

Infrastructure groundwork was laid (YAML config files created, task plan written). The Pydantic data models and all downstream phases (T1.2 onward) are **not yet implemented**.

### 2. LLM Provider Investigation — llama.cpp vs Ollama (concluded)

Several sessions (Jan 28–29) were spent attempting to use `llama-cpp-python` directly with the `gpt-oss:20b Q4_K_M` model as an alternative to Ollama. This was **abandoned**:

- GBNF grammar + sampling params caused `llama_decode()` hangs
- Without grammar, the model produced meta-commentary / thinking chains instead of JSON
- Ollama works cleanly because it filters `<|channel|>analysis...<|end|>` blocks internally
- `filter_gpt_oss_output()` was implemented in `config/llm_config.py` to strip channels if llama.cpp is ever used again
- A batch benchmark tool was added at `llamacpp_ollama/batch_benchmark.py`

**Decision: Use Ollama for the grading pipeline going forward.**

---

## Open Tasks

### Immediate / Blocked by nothing

- [ ] **T1.2** — Define Pydantic data models (`Check`, `Rubric`, `CheckEvaluation`, `GradeResult`, `Appeal`)
  → file: `grading_pipeline/models.py` (create)
  → file: `grading_pipeline/schemas.py` (create)

- [ ] **Close T11.1** — Mark llama.cpp experiment done in `llamacpp_ollama/TASK_LIST.md`; document Ollama decision

### Phase 2 — Rubric Generation (depends on T1.2)

- [ ] **T2.1** — Update rubric generation prompt template
  → file: `grading_pipeline/rubric_generator_template.txt`

- [ ] **T2.2** — Implement check extraction
  → file: `grading_pipeline/check_extraction.py` (create)

- [ ] **T2.3** — Implement category assignment
  → file: `grading_pipeline/categorization.py` (create)

- [ ] **T2.4** — Implement deduplication
  → file: `grading_pipeline/deduplication.py` (create)

- [ ] **T2.5** — Integrate full rubric generation pipeline
  → file: `grading_pipeline/rubric_generator.py` (update)

### Phase 3 — Evaluation & Scoring (depends on Phase 2)

- [ ] **T3.1** — Check evaluation via LLM
  → file: `grading_dynamic_rubrics/check_evaluation.py` (create)

- [ ] **T3.2** — Hybrid evaluation with human override
  → file: `grading_dynamic_rubrics/check_evaluation.py` (update)

- [ ] **T3.3** — Scoring algorithm
  → file: `grading_dynamic_rubrics/scoring.py` (create)

- [ ] **T3.4** — Grade storage and appeal tracking
  → file: `grading_dynamic_rubrics/grade_storage.py` (create)

### Infrastructure / Config (done or partially done)

- [x] **T1.1** — YAML config files created
  → `config/grading_categories.yaml`, `config/grading_config.yaml`

- [x] **T6.1** — llama.cpp provider added to `config/llm_config.py`

---

## Blockers & Open Questions

1. **Ollama path not verified end-to-end** — `config/llm_config.py` was modified heavily during the llama.cpp experiment. Before building Phase 2/3, confirm Ollama still works cleanly for grading (run a smoke test with one question).

2. **T1.3 (storage structure)** — Directory structure for storing rubric artifacts, grades, and appeals was designed but not confirmed as created. Check `grading_dynamic_rubrics/` layout before starting T2.5.

3. **Reranking is done once** — Per commit `3df9dbf`, reranking was run for at least one question and stored. Confirm which questions have reranked indices before building the evaluation pipeline.

4. **Grade-spec.md** — Per `CLAUDE.md`, any grading logic changes require updating `grade-spec.md` first. Locate and review this file before starting T3.x.

---

## Next time, start by…

1. Run `python -c "from config.llm_config import configure_llm; configure_llm('ollama')"` to verify Ollama path is intact.
2. Implement **T1.2** (Pydantic models) — this unblocks everything in Phases 2 and 3.
3. Then move to **T2.1** (rubric template update) and **T2.2** (check extraction).
