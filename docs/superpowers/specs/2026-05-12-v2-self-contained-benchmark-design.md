# Design — v2 Self-Contained Benchmark on q01–q05

**Date:** 2026-05-12
**Branch:** `version2-self-contained-benchmark`
**Decision context:** This session of `superpowers:brainstorming` settled on
running the v2 ordering benchmark for q01–q05 as the highest-leverage next move.
A new top-level folder `version2/` will hold a vendored copy of v2 plus
everything it needs, with no imports or file reads outside that folder.

---

## Goal

Produce ordering-violation counts for v2's concept-presence judge on
questions q01–q05 using the `oss` model tier (`gemma4:26b` via Ollama),
directly comparable to v1's T4.3 baseline. Place all v2 work inside a
self-contained `version2/` folder so the benchmark and its dependencies are
isolated from the v1 code paths.

## Non-goals

- Wiring `retrieval_core/` into `ConceptJudge` (deferred — Option 2 from
  the brainstorm).
- Running the `foundational` or `mixed` tiers (deferred — Gemini Flash
  is rate-limited at 5 RPM; oss is the practical baseline).
- Deleting `autograder/v2/`, `autograder/tests/v2/`, or any v1 code paths.
  Single source of truth becomes `version2/` only after parity is verified.
- v1 config cleanup (the latent CS101-stub bug for q01/q02) — out of scope.
- q06–q10 — no v1 T4.3 baseline to compare against; needs synthetic-answer
  generation first.
- Persisting v2 rubrics to disk — separate concern.

## Architecture

```
autograder/
  version2/                          # NEW; self-contained v2 work area
    v2/                              # vendored from autograder/v2/
      __init__.py
      models.py
      rubric_schema.py
      question_types.py
      answer_generator.py
      rubric_generator.py
      rubric_critic.py
      karpathy_loop.py
      judge.py
      scoring.py
      benchmark.py
      pipeline.py
    config/
      __init__.py
      llm_config.py                  # TRIMMED copy of autograder/config/llm_config.py
      rubric_generation.yaml         # vendored verbatim
    tests/
      __init__.py
      v2/                            # vendored from autograder/tests/v2/
        __init__.py
        test_*.py
    scripts/
      run_v2_benchmark.py            # vendored; path-adjusted if needed
    sources/
      slides_data_type_quality.pdf   # vendored from grading_pipeline/sources/
      ten_questions.md               # vendored from autograder/
      submissions/                   # 15 files: q01–q05 × {good, less_good, wrong}
    results/                         # benchmark output target
    README.md                        # how to run from inside version2/
```

Scripts and tests run with `version2/` as cwd. Imports inside `version2/v2/*`
stay as `from v2.x import …` and `from config.llm_config import …`; both
resolve against `version2/`'s own subdirectories when `version2/` is on the
Python path.

## Vendoring rules

| Source | Destination | Rule |
|---|---|---|
| `autograder/v2/*` | `version2/v2/*` | Verbatim copy. No edits expected unless an import resolves outside the vendored set. |
| `autograder/config/llm_config.py` | `version2/config/llm_config.py` | Trimmed copy. Keep `load_env_config`, `configure_llm`, `configure_llm_for_tier`, the SOCKS-proxy import guard, and only the provider branches v2 actually calls (`ollama`, `gemini`). Drop LMQL/LlamaCPP code unless v2 imports prove they're needed. |
| `autograder/config/rubric_generation.yaml` | `version2/config/rubric_generation.yaml` | Verbatim. Confirm `model_tier: oss` and `model: gemma4:26b`. |
| `autograder/tests/v2/*` | `version2/tests/v2/*` | Verbatim. Fix any hard-coded paths to source files. |
| `autograder/scripts/run_v2_benchmark.py` | `version2/scripts/run_v2_benchmark.py` | Verbatim modulo path resolution: any walk-up to `autograder/` root must be re-anchored to `version2/`. Default `--report` and `--log` paths under `version2/results/`. |
| `autograder/grading_pipeline/sources/slides_data_type_quality.pdf` | `version2/sources/slides_data_type_quality.pdf` | Verbatim. |
| `autograder/ten_questions.md` | `version2/sources/ten_questions.md` | Verbatim. |
| `autograder/grading_pipeline/submissions/student_001_q0{1..5}_{good,less_good,wrong}.yaml` | `version2/sources/submissions/` | Verbatim. 15 files. |

## Execution steps

1. **Audit v2 outside-folder dependencies.** `grep -rn "^import\|^from" autograder/v2/` and `autograder/scripts/run_v2_benchmark.py` and `autograder/tests/v2/`. Produce the exhaustive list of non-stdlib, non-third-party imports that come from `autograder/` parents. Expected: `config.llm_config`, possibly `grading_pipeline.index_builder._extract_text_from_pdf` for PDF source loading.
2. **Audit file-path references.** `grep -rn '"\.\./\|"/Users\|Path(__file__).parent.parent' autograder/v2/ autograder/scripts/run_v2_benchmark.py autograder/tests/v2/`. Find anything that resolves to a path outside its module's folder.
3. **Create `version2/` skeleton** with the directory layout above.
4. **Copy vendored files** according to the table.
5. **Trim `version2/config/llm_config.py`** to v2's actual import surface.
6. **Adjust paths in vendored files** as needed — most likely candidates:
   - `run_v2_benchmark.py` default report/log paths
   - `rubric_generation.yaml` if it has any hard-coded absolute paths
   - `tests/v2/conftest.py` if it exists
7. **Run the v2 test suite from `version2/`:**
   `cd version2 && PYTHONPATH=. .venv/bin/python -m pytest tests/v2/ -v`.
   All tests must pass with zero files-not-found errors. Iterate on path fixes
   until green.
8. **Smoke-test the benchmark on q01:**
   `cd version2 && PYTHONPATH=. python scripts/run_v2_benchmark.py --questions q01 --tier oss --report results/v2_smoke_q01.md`.
   Verify end-to-end execution; capture the log; spot-check for path errors.
9. **Run the full benchmark q01–q05:**
   `--questions q01,q02,q03,q04,q05 --tier oss --report results/v2_benchmark_q01-q05.md`.
10. **Extract ordering-violation counts** from the report (per question:
    `good vs less_good` and `less_good vs wrong` checks).
11. **Write `version2/results/v1_v2_comparison.md`** with the v1 T4.3 baseline
    figures (from `REDESIGN.md` §1 — `float` method: q03 less_good < wrong,
    q05 less_good < wrong; `round` method: q05 wrong ≥ less_good) and the
    v2 counts side by side.

## Acceptance criteria

- `grep -r "autograder\|grading_pipeline\|retrieval_core\|/Users/erlebach/src/2026/grading_assessment/autograder" version2/` returns nothing.
- All v2 tests pass when run with `version2/` as cwd.
- `version2/results/v2_benchmark_q01-q05.md` exists with per-question
  ordering-violation counts.
- `version2/results/v1_v2_comparison.md` records the v1↔v2 delta in a table.
- `version2/README.md` documents the run command and acceptance of the result.

## Risks

| Risk | Mitigation |
|---|---|
| `config/llm_config.py` is more entangled with v1 than surface read shows (LMQL, LlamaCPP scaffolding) | Audit imports first (step 1); vendor minimal slice only. |
| Ollama destabilises during the run (GamePolicyAgent / GGML blob crash patterns from 2026-05-11/12) | launchd mitigations from JOURNAL 2026-05-12 are deployed. `--questions` accepts a subset, so reruns can skip completed work. |
| Model-name drift between earlier `gpt-oss-20b` results files and current `gemma4:26b` default | Confirm `version2/config/rubric_generation.yaml` model and note it in the README and comparison file. |
| `_extract_text_from_pdf` lives in `grading_pipeline/index_builder.py` — vendoring it could pull in additional deps | If v2 doesn't import it (likely; v2 may not need PDF reading), skip. If it does, vendor a minimal extraction helper into `version2/v2/_pdf.py`. |

## Open questions

None — both critical scope questions were answered in the brainstorm
(vendor-copy approach; q01–q05 on oss tier only). Anything that surfaces
during the audit step that wasn't anticipated will be raised before further
vendoring.
