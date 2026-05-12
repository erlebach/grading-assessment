# SNAPSHOT — autograder

*Last updated: 2026-05-11 22:22*

## Purpose

LLM-based autograder for short-answer assignments. Two pipelines coexist:

- **v1 (legacy):** keyword + semantic scoring over dynamically generated rubrics.
  Lives in `grading_pipeline/` and `grading_dynamic_rubrics/`. Reached T4.3 sample
  grading; structural failures (vocabulary-dependence, no quality-level
  discrimination) motivated the v2 redesign.
- **v2 (current focus):** concept-presence LLM judge over typed concept-check
  rubrics, with Karpathy-style iterative refinement against a held-out validation
  split. Lives in `v2/`. Design docs: `REDESIGN.md`, `USAGE_v2.md`,
  `WALKTHROUGH_v2.md`.

## Scripts / Components

### v2 (concept-check pipeline)

- `v2/models.py` — `ConceptCheck`, `CriterionV2`, `RubricV2`, `GradeV2`, `SyntheticAnswer`, `PrecisionLevel`
- `v2/rubric_schema.py` — `parse_rubric_response` (LLM JSON → `RubricV2`)
- `v2/question_types.py` — 10 `QuestionType` values + prompt templates
- `v2/answer_generator.py` — 3×3 synthetic answers (good/less_good/wrong) at T=0.7
- `v2/rubric_generator.py` — answer-informed concept-check rubric generator
- `v2/rubric_critic.py` — proposes rubric fixes for ordering violations
- `v2/karpathy_loop.py` — iterative refinement with train/val split
- `v2/judge.py` — `ConceptJudge` in single/multi LLM-call modes
- `v2/scoring.py` — weighted-mean float scoring (no `int()` truncation)
- `v2/benchmark.py` — library: `find_violations`, `check_ordering` for `good > less_good > wrong`
- `v2/pipeline.py` — end-to-end orchestrator (`PipelineV2`)
- `config/rubric_generation.yaml` — model tier, evaluation mode, loop params, scoring mode
- `config/llm_config.py::configure_llm_for_tier()` — tier dispatch (foundational/oss/mixed)
- `tests/v2/` — ~45 tests covering all v2 modules
- `scripts/run_v2_benchmark.py` — end-to-end ordering-benchmark driver (`--tier`)
- `scripts/probe_ollama.py` — Ollama stability MWE: N tiny calls + parallel `app.log` SIGKILL tail; verdict + exit code

### v1 (legacy, still active)

- `grading_pipeline/cli.py`, `pipeline.py` — grading flow + backend selection
- `grading_pipeline/rubric_generator.py`, `check_extraction.py`, `categorization.py`, `deduplication.py` — rubric generation pipeline
- `grading_dynamic_rubrics/pipeline.py`, `check_evaluation.py`, `scoring.py`, `grade_storage.py` — dynamic-rubric evaluation + storage + appeals
- `grading_pipeline/index_builder.py` / `index_builder_in_memory.py` — ChromaDB and pickle backends
- `retrieval_core/retriever.py`, `multi_retriever.py` — dual/multi-index retrieval + reranker, optional `--transparent` tracing

### Shared infrastructure (carried over to v2)

- `retrieval_core/` — index building, retrieval, reranking
- `config/llm_config.py` — provider abstraction (Ollama, Gemini); SOCKS-proxy-safe import
- `grading_pipeline/submission_loader.py`, `submission_converter.py`, `manifest.py`, `transparency_logger.py`

## Output structure

- `rubrics/` — v1 YAML rubrics (authoritative for v1)
- `rubrics_dynamic/` — v1 LLM-generated rubrics (JSON + YAML)
- v2 rubrics + grades + feedback follow the assignment-folder layout in
  `WALKTHROUGH_v2.md` (`rubrics/qNN.json`, `grades/sNNN_qNN.json`,
  `feedback/sNNN_qNN.json`); no canonical repo path yet
- `data/grades/` — v1 grade records
- `logs/` — `grading.log` + `transparency.log` per run

## Key design decisions

- **v2 replaces keyword matching with LLM concept judgment.** Vocabulary-agnostic;
  precision is graded on `full` / `partial` / `none` (weights 1.0 / 0.5 / 0.0).
- **Float scoring throughout v2** — no `int()` truncation anywhere.
- **Karpathy refinement loop with train/val split** — rubric stops iterating only
  when no ordering violations exist on a held-out set (overfitting guard).
- **Configurable model tier:** `foundational` (Gemini Flash, default — note
  free tier is capped at 5 RPM, prohibitive for the v2 pipeline's ~25–45
  calls/question), `oss` (Ollama `gemma4:26b` since 2026-05-11; previously
  `gpt-oss:20b`), or `mixed`.
- **Evaluation mode switch:** `single` (one LLM call per answer) vs. `multi` (one
  per check). Empirical comparison is part of the v2 benchmark plan.
- **Question-type registry (10 types)** anchors prompt templates and example banks,
  constraining the rubric-generation search space.
- **Dual index backends retained from v1:** ChromaDB (persistent) or in-memory pickle.
- **Ollama-only on macOS:** single-instance constraint; grading is sequential.
- `.git` lives at `autograder/.git` (repo root); no `-C` flag needed for git commands.

## TODO

- Write a benchmark driver script (`scripts/run_v2_benchmark.py`) per
  `WALKTHROUGH_v2.md` §4–5, run on q01–q05, compare ordering-violation count to
  the v1 T4.3 baseline.
- Decide v1 deprecation policy. `REDESIGN.md` §8 lists files to carry over vs.
  retire. `grading_pipeline/` and `grading_dynamic_rubrics/` are still in tree.
- Wire `retrieval_core` into `ConceptJudge.evaluate(evidence_context=...)`
  (currently passed empty string).
- Open a v2 task spec (`TASK_LIST.md` is v1-era only).
- Review `grade-spec.md` against v2 concept-check schema before declaring v2 canonical.
- Remove parent `.git` backup at `../grading_assessment/.git` when no longer needed.
