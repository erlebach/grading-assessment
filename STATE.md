# Project State — autograder / v2-concept-rubrics branch

**Last updated:** 2026-05-11
**Branch:** `v2-concept-rubrics`
**Last commit:** `a70db9f` — Move .git into autograder/ (make autograder the repo root)

---

## Narrative Recap

This project is an LLM-based autograder for short-answer questions. It has gone
through two architectural generations:

- **v1 (legacy, still in tree):** Dynamically-generated rubrics with keyword + semantic
  scoring. Lives in `grading_pipeline/` and `grading_dynamic_rubrics/`. Reached T4.3
  (sample grading) and revealed structural failures — keyword scoring cannot judge
  vocabulary-paraphrased concepts, and `evidence_count / top_k` provides no
  discrimination across answer quality levels.
- **v2 (current focus):** Concept-presence LLM-judge pipeline. Lives in `v2/`. Rubrics
  are typed concept checks with precision levels; a Karpathy-style critic loop iterates
  the rubric until `good > less_good > wrong` ordering holds on a held-out validation
  split.

The v2 redesign is documented in `REDESIGN.md`, `USAGE_v2.md`, and `WALKTHROUGH_v2.md`.

### LLM Providers

- **Default (`foundational` tier):** Gemini Flash (`models/gemini-2.5-flash`) via
  `config/llm_config.py::configure_llm_for_tier()`. Requires `GOOGLE_API_KEY`.
- **Local (`oss` tier):** Ollama `gpt-oss:20b`. SOCKS proxy crash fixed
  (`64e7a72`, `2e20ff9`).
- **Mixed:** foundational for rubric generation, oss for scoring.

---

## What's done (v2)

| Component | File(s) | Commit |
|-----------|---------|--------|
| Core data models (ConceptCheck, CriterionV2, RubricV2, GradeV2, SyntheticAnswer) | `v2/models.py` | `410916d` → `8f6b5dc` |
| Rubric schema validation (`parse_rubric_response`) | `v2/rubric_schema.py` | `7f0c9ab` → `af27d14` |
| 10 question types + prompt templates | `v2/question_types.py` | `ac98956` |
| `configure_llm_for_tier` + `config/rubric_generation.yaml` | `config/llm_config.py`, `config/rubric_generation.yaml` | `b30e8c9` |
| Synthetic answer generator (3 × 3 quality levels, T=0.7) | `v2/answer_generator.py` | `07dfb55` |
| Ordering benchmark (`find_violations`, `check_ordering`) | `v2/benchmark.py` | `423ba60`, `5fa28cc` |
| Concept-check, answer-informed rubric generator | `v2/rubric_generator.py` | `ac98ab7` |
| Weighted-mean float scoring (no `int()` truncation) | `v2/scoring.py` | `12fa934` |
| LLM concept judge (single/multi mode) | `v2/judge.py` | `b7ef0e5` |
| Rubric critic + Karpathy iterative refinement loop | `v2/rubric_critic.py`, `v2/karpathy_loop.py` | `5fa28cc` |
| End-to-end pipeline orchestrator | `v2/pipeline.py` | `89e2225` |
| v2 test suite (~45 tests in `tests/v2/`) | `tests/v2/test_*.py` | various |

## What's done (v1, retained)

- Phase 1–3 (T1.1 → T3.4): models, rubric generation pipeline, evaluation, scoring,
  grade storage — all complete in `grading_pipeline/` and `grading_dynamic_rubrics/`.
- Phase 4 partial: T4.1 (183 unit tests), T4.2 (223 integration tests), T4.3
  (sample grading q01–q05).
- **T4.3 follow-up fixes landed** (despite STATE not reflecting them earlier):
  - P1 `int → round/float` scoring comparison — `839af81`
  - P2 stopword filter in `extract_keywords`, semantic mode reverted to count — `1ce1655`
  - P3 reranker-weighted semantic scoring with mode switch + NaN fix — `1524940`, `7f6f71a`
- Major cleanup commit `be97575` removed `version1/`, `mwe/`, obsolete `IMPLEMENTATION_*.md`
  plans, and `grader/grade_question.py` (~11.8k lines deleted).

---

## Open items

1. **Run the v2 ordering benchmark end-to-end on q01–q05.** `v2/benchmark.py` is a
   library (`find_violations`, `check_ordering`), not a runnable script. Driving it
   requires `v2/pipeline.py` with an indexed source corpus and either a Gemini API
   key or local Ollama. No assignment runner script is checked in — `WALKTHROUGH_v2.md`
   provides the template scripts (`generate_rubrics.py`, `grade_students.py`,
   `generate_feedback.py`) but they live in the doc, not in `scripts/`.

2. **v1 vs v2 deprecation policy.** Both pipelines coexist. `REDESIGN.md` section 8
   lists files to carry over vs. files that should not be carried over. The cleanup
   in `be97575` removed the worst offenders but `grading_pipeline/` and
   `grading_dynamic_rubrics/` are still active.

3. **Retrieval wiring.** `ConceptJudge.evaluate(evidence_context: str)` accepts
   retrieval context but the wiring of `retrieval_core` into the v2 pipeline is a
   follow-on task (noted in `USAGE_v2.md` Design Notes).

4. **TASK_LIST.md is v1-only.** It still tracks T4.4 (CI). The v2 work has no
   visible task tracking. Decide whether to extend TASK_LIST.md with a v2 phase or
   open a new task spec.

5. **Per CLAUDE.md authority rule**, any grading-logic change must update
   `grade-spec.md` first. That file was added in `c4c1190` and has not been touched
   during the v2 work — verify it does not conflict with the concept-check schema
   before treating v2 as canonical.

---

## Next time, start by…

1. Run `scripts/run_v2_benchmark.py --tier oss --all` — driver exists; `oss`
   tier in `config/rubric_generation.yaml` now points to `gemma4:26b` (Ollama,
   local, no rate limit). Earlier attempt against Gemini Flash hit the free-tier
   5-RPM cap (q01 smoke failed mid-run with `ResourceExhausted: 429`).
2. Compare v2 ordering-violation count to the v1 T4.3 baseline (q02, q03, q05
   failed on v1). If v2 passes all 5 questions, mark v2 as the canonical
   pipeline and start the v1 deprecation.
3. After-benchmark cleanup: fix `WALKTHROUGH_v2.md` doc gaps — `GOOGLE_API_KEY`
   should be `GEMINI_API_KEY`; `retrieve_context` import does not exist (real
   API is `class DualIndexRetriever`).
