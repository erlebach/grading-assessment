# v2 Self-Contained Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vendor v2 plus its dependencies into a new top-level `version2/` folder with no imports/paths outside that folder, then run the v2 ordering benchmark on q01–q05 using the `oss` model tier (`gemma4:26b` via Ollama) and record the v1↔v2 comparison.

**Architecture:** Verbatim copies. `v2/` is already module-self-contained (all imports are `from v2.x` or stdlib/third-party). The only external code dependency is `config/llm_config.py` (used by the benchmark script for `configure_llm_for_tier`) — vendor it whole. The only external file dependency is the slides PDF — vendor it. Path fixes are limited to `run_v2_benchmark.py` (`REPO_ROOT` and `PDF_PATH`). Tests run from `version2/` with `PYTHONPATH=.`.

**Tech Stack:** Python 3.11+ via `.venv/`, pytest, Pydantic v2, llama-index (Ollama provider), PyYAML, pypdf. Ollama serving `gemma4:26b` locally.

**Spec:** `docs/superpowers/specs/2026-05-12-v2-self-contained-benchmark-design.md`

**Branch:** `version2-self-contained-benchmark` (already created and checked out).

**Working directory for all commands:** `/Users/erlebach/src/2026/grading_assessment/autograder` (the repo root). `version2/` lives at that path.

---

## File Structure (target)

```
version2/
  v2/                              # 12 files, vendored from autograder/v2/
  config/
    __init__.py
    llm_config.py                  # full copy of autograder/config/llm_config.py
    rubric_generation.yaml         # full copy
  tests/
    __init__.py
    v2/                            # vendored from autograder/tests/v2/
      __init__.py
      conftest.py (if any)
      test_*.py (12 files)
  scripts/
    run_v2_benchmark.py            # path-adjusted: PDF_PATH now points inside version2/sources/
  sources/
    slides_data_type_quality.pdf
  results/
    .gitkeep                       # so the dir is committed empty
  README.md                        # how to run from inside version2/
```

Note: submissions/ and ten_questions.md are NOT vendored. The benchmark script generates its own answers via `AnswerGenerator`; it does not read submission YAMLs. Question text for q01–q05 is hardcoded in `scripts/run_v2_benchmark.py:55–100` (the `QUESTIONS` dict).

---

## Task 1: Create the `version2/` skeleton

**Files:**
- Create: `version2/`
- Create: `version2/v2/`
- Create: `version2/config/`
- Create: `version2/tests/`
- Create: `version2/tests/v2/`
- Create: `version2/scripts/`
- Create: `version2/sources/`
- Create: `version2/results/`

- [ ] **Step 1: Create all subdirectories**

```bash
mkdir -p version2/v2 version2/config version2/tests/v2 version2/scripts version2/sources version2/results
```

- [ ] **Step 2: Add `__init__.py` files for the package directories**

```bash
touch version2/config/__init__.py version2/tests/__init__.py version2/tests/v2/__init__.py
```

(`v2/__init__.py` will arrive with the vendored copy in Task 2.)

- [ ] **Step 3: Add `.gitkeep` for `results/` so the empty dir is committed**

```bash
touch version2/results/.gitkeep
```

- [ ] **Step 4: Verify structure**

Run: `find version2 -type d | sort`
Expected output:
```
version2
version2/config
version2/results
version2/scripts
version2/sources
version2/tests
version2/tests/v2
version2/v2
```

- [ ] **Step 5: Commit**

```bash
git add version2/config/__init__.py version2/tests/__init__.py version2/tests/v2/__init__.py version2/results/.gitkeep
git commit -m "version2: scaffold directory structure"
```

---

## Task 2: Vendor `v2/` module

**Files:**
- Copy: `v2/*.py` → `version2/v2/*.py` (12 files)

- [ ] **Step 1: Copy every Python file in `v2/` to `version2/v2/`**

```bash
cp v2/*.py version2/v2/
```

- [ ] **Step 2: Verify the copy**

Run: `ls version2/v2/ | sort`
Expected output:
```
__init__.py
answer_generator.py
benchmark.py
judge.py
karpathy_loop.py
models.py
pipeline.py
question_types.py
rubric_critic.py
rubric_generator.py
rubric_schema.py
scoring.py
```

- [ ] **Step 3: Confirm zero imports outside `v2/`**

Run: `grep -rEn "^from |^import " version2/v2/ | grep -v "from v2\.\|from __future__\|^import \|from typing\|from datetime\|from enum\|from dataclasses\|from pydantic"`
Expected output: empty (no lines).

If non-empty: investigate; the audit said only `v2.*`, stdlib, and pydantic appear. Anything else is a finding to raise before continuing.

- [ ] **Step 4: Commit**

```bash
git add version2/v2/
git commit -m "version2: vendor v2/ module (verbatim)"
```

---

## Task 3: Vendor `config/llm_config.py` and `config/rubric_generation.yaml`

**Files:**
- Copy: `config/llm_config.py` → `version2/config/llm_config.py`
- Copy: `config/rubric_generation.yaml` → `version2/config/rubric_generation.yaml`

Rationale for full-file copy (not trimmed): the spec proposed trimming to `configure_llm_for_tier`'s transitive needs, but the file is ~350 lines, single-responsibility, and trimming risks subtle breakage. Vendor whole; revisit only if it creates concrete issues later.

- [ ] **Step 1: Copy both files**

```bash
cp config/llm_config.py version2/config/llm_config.py
cp config/rubric_generation.yaml version2/config/rubric_generation.yaml
```

- [ ] **Step 2: Verify the model tier in the vendored config**

Run: `grep -E "^model_tier:|^  model:" version2/config/rubric_generation.yaml`
Expected: `model_tier: oss` and the model field showing `gemma4:26b` (per JOURNAL 2026-05-12 14:19).

If the model name differs (e.g., `gpt-oss:20b`), note it but do not change — that is the current default and matches the running Ollama instance.

- [ ] **Step 3: Confirm `configure_llm_for_tier` is importable from the vendored copy**

Run from the repo root:
```bash
cd version2 && PYTHONPATH=. ../.venv/bin/python -c "from config.llm_config import configure_llm_for_tier; print(configure_llm_for_tier)"
```
Expected: prints `<function configure_llm_for_tier at 0x...>`. No ImportError.

If `ImportError: No module named 'llama_index.llms.ollama'` or similar: the venv lacks a dep. Diagnose by `../.venv/bin/python -c "import llama_index.llms.ollama"`. Do NOT add new dependencies in this plan — surface the issue to the user.

- [ ] **Step 4: Commit**

```bash
git add version2/config/llm_config.py version2/config/rubric_generation.yaml
git commit -m "version2: vendor config/llm_config.py and rubric_generation.yaml"
```

---

## Task 4: Vendor the slides PDF

**Files:**
- Copy: `grading_pipeline/sources/slides_data_type_quality.pdf` → `version2/sources/slides_data_type_quality.pdf`

- [ ] **Step 1: Copy the PDF**

```bash
cp grading_pipeline/sources/slides_data_type_quality.pdf version2/sources/slides_data_type_quality.pdf
```

- [ ] **Step 2: Verify size matches (sanity check on the copy)**

Run: `wc -c grading_pipeline/sources/slides_data_type_quality.pdf version2/sources/slides_data_type_quality.pdf`
Expected: both files report the same byte count.

- [ ] **Step 3: Commit**

```bash
git add version2/sources/slides_data_type_quality.pdf
git commit -m "version2: vendor slides PDF"
```

---

## Task 5: Vendor and adjust `run_v2_benchmark.py`

**Files:**
- Copy + edit: `scripts/run_v2_benchmark.py` → `version2/scripts/run_v2_benchmark.py`

Path fixes needed (auditing already done in spec step 1):
- `REPO_ROOT = Path(__file__).resolve().parents[1]` — after vendoring, `parents[1]` from `version2/scripts/` is `version2/`, which is the new "root." This is already correct semantically; no edit needed.
- `PDF_PATH = REPO_ROOT / "grading_pipeline" / "sources" / "slides_data_type_quality.pdf"` — must become `REPO_ROOT / "sources" / "slides_data_type_quality.pdf"`.

- [ ] **Step 1: Copy the script**

```bash
cp scripts/run_v2_benchmark.py version2/scripts/run_v2_benchmark.py
```

- [ ] **Step 2: Fix `PDF_PATH` to point inside `version2/sources/`**

In `version2/scripts/run_v2_benchmark.py`, replace:
```python
PDF_PATH = REPO_ROOT / "grading_pipeline" / "sources" / "slides_data_type_quality.pdf"
```
with:
```python
PDF_PATH = REPO_ROOT / "sources" / "slides_data_type_quality.pdf"
```

- [ ] **Step 3: Verify the only path string referring outside `version2/` is gone**

Run: `grep -n "grading_pipeline\|/Users/erlebach\|autograder" version2/scripts/run_v2_benchmark.py`
Expected: matches only inside the docstring comment at line 9–13 (which mentions `grading_pipeline/sources/...` and `t4_3_report.md` historically). These are comments and don't affect execution. Optionally update the docstring to reference `sources/slides_data_type_quality.pdf` and remove the t4_3_report reference, but functional correctness does not require this.

- [ ] **Step 4: Confirm the script's imports resolve when run from `version2/`**

```bash
cd version2 && PYTHONPATH=. ../.venv/bin/python -c "import scripts.run_v2_benchmark"
```
Expected: no output (successful import) or a known warning. NOT acceptable: `ImportError`, `ModuleNotFoundError`, `FileNotFoundError`.

Note: `sys.path.insert(0, str(REPO_ROOT))` inside the script will insert `version2/` itself onto `sys.path`, which is correct for resolving `from config.llm_config` and `from v2.x`.

- [ ] **Step 5: Commit**

```bash
git add version2/scripts/run_v2_benchmark.py
git commit -m "version2: vendor run_v2_benchmark.py with PDF_PATH re-anchored"
```

---

## Task 6: Vendor `tests/v2/` and run the test suite

**Files:**
- Copy: `tests/v2/*.py` → `version2/tests/v2/*.py`

- [ ] **Step 1: Copy every test file**

```bash
cp tests/v2/*.py version2/tests/v2/ 2>/dev/null
ls tests/v2/conftest.py >/dev/null 2>&1 && cp tests/v2/conftest.py version2/tests/v2/
```

- [ ] **Step 2: Verify the copy**

Run: `ls version2/tests/v2/ | sort`
Expected (one per v2 module, plus models/schema):
```
__init__.py
test_answer_generator.py
test_benchmark.py
test_judge.py
test_karpathy_loop.py
test_llm_tier.py
test_models.py
test_pipeline.py
test_question_types.py
test_rubric_generator.py
test_rubric_schema.py
test_scoring.py
```
(Plus `conftest.py` if it existed in the source — Step 1 copies it conditionally.)

- [ ] **Step 3: Run the test suite from `version2/`**

```bash
cd version2 && PYTHONPATH=. ../.venv/bin/python -m pytest tests/v2/ -v
```
Expected: all tests pass. If `tests/v2/test_llm_tier.py` fails because it does live network calls to Ollama, mark it as expected-to-skip; the rest of the suite should be hermetic (uses `MagicMock` for LLM).

If a test fails with `FileNotFoundError` or `ModuleNotFoundError`:
- `FileNotFoundError`: a test reads a file by path. Locate the offending line (`grep -n "open(\|Path(" version2/tests/v2/`) and either vendor the missing file or patch the path. Do not invent test data.
- `ModuleNotFoundError`: an import is escaping `version2/`. Re-run the audit (`grep -rEn "^from |^import " version2/tests/v2/`) and either vendor or fix.

- [ ] **Step 4: Capture test result counts**

After tests pass, run:
```bash
cd version2 && PYTHONPATH=. ../.venv/bin/python -m pytest tests/v2/ --tb=no -q 2>&1 | tail -5
```
Note the passed/failed/skipped numbers — these go in the README written in Task 9.

- [ ] **Step 5: Commit**

```bash
git add version2/tests/v2/
git commit -m "version2: vendor tests/v2/ and verify all pass from inside version2/"
```

---

## Task 7: Smoke-test the benchmark on q01

This is the integration sanity check: confirm the end-to-end pipeline runs on a single question before committing to a 5-question run that takes much longer.

- [ ] **Step 1: Verify Ollama is running and the model is available**

```bash
curl -s http://localhost:11434/api/tags | grep -E "gemma4:26b|gpt-oss:20b"
```
Expected: at least one of the tier-default models is listed. If empty: start Ollama (`! ollama serve` if needed) or pull the model. Do not proceed until this is green.

- [ ] **Step 2: Run the smoke benchmark on q01**

```bash
cd version2 && PYTHONPATH=. ../.venv/bin/python scripts/run_v2_benchmark.py --questions q01 --tier oss --report results/v2_smoke_q01.md
```

Expected: the script writes `version2/results/v2_smoke_q01.md` and `version2/results/v2_smoke_q01.log`. It runs answer generation → rubric generation → Karpathy refinement → scoring → violation check, and prints a final summary line with the converged/violation status. Total wall time depends on Ollama latency; gemma4:26b on Apple Silicon typically completes one question in 5–15 minutes.

If the run errors:
- `FileNotFoundError: …slides_data_type_quality.pdf`: Task 5 step 2 didn't apply or Task 4 didn't run. Fix and retry.
- `ConnectionError: Failed to connect to Ollama`: Ollama is not running on `localhost:11434`. Start it.
- `httpx.ReadTimeout`: the request timeout in `config/llm_config.py` is too low or the model is slow. Confirm `request_timeout=300.0` is set (it was bumped in commit 39ece9d).
- Anything else: do not paper over. Capture the traceback in the log and stop the plan; the user needs to see it.

- [ ] **Step 3: Inspect the smoke report**

Run: `cat version2/results/v2_smoke_q01.md`
Expected: a small Markdown table with at least one row for q01 showing converged/violation_count. The exact format is set by `run_v2_benchmark.py`'s reporting code.

- [ ] **Step 4: Commit smoke artifacts**

```bash
git add version2/results/v2_smoke_q01.md version2/results/v2_smoke_q01.log
git commit -m "version2: smoke-test benchmark on q01 (oss tier)"
```

---

## Task 8: Run the full q01–q05 benchmark

- [ ] **Step 1: Run the benchmark across q01–q05**

```bash
cd version2 && PYTHONPATH=. ../.venv/bin/python scripts/run_v2_benchmark.py --questions q01,q02,q03,q04,q05 --tier oss --report results/v2_benchmark_q01-q05.md
```

Expected wall time: roughly 5× the q01 smoke run, so 25–75 minutes total depending on Ollama latency and Karpathy iteration count. If Ollama destabilises mid-run (GamePolicyAgent / GGML blob crash), the run will fail. Recovery: rerun with only the unfinished questions (e.g., `--questions q03,q04,q05`).

- [ ] **Step 2: Inspect the full report**

Run: `cat version2/results/v2_benchmark_q01-q05.md`
Expected: one row per question (q01–q05) showing converged/violation_count.

- [ ] **Step 3: Capture the per-question violation counts for the comparison file**

Read off the table. Format:

| Question | Converged | Iterations | Violations |
|---|---|---|---|
| q01 | … | … | … |
| q02 | … | … | … |
| q03 | … | … | … |
| q04 | … | … | … |
| q05 | … | … | … |

- [ ] **Step 4: Commit the benchmark artifacts**

```bash
git add version2/results/v2_benchmark_q01-q05.md version2/results/v2_benchmark_q01-q05.log
git commit -m "version2: full q01-q05 ordering benchmark (oss tier, gemma4:26b)"
```

---

## Task 9: Write the v1↔v2 comparison and the README

**Files:**
- Create: `version2/results/v1_v2_comparison.md`
- Create: `version2/README.md`

- [ ] **Step 1: Write `version2/results/v1_v2_comparison.md`**

Content template (substitute real numbers from Task 8 step 3):

```markdown
# v1 vs v2 Ordering Comparison — q01–q05

**Date:** 2026-05-12
**v1 baseline source:** `t4_3_report.md` (cited from `REDESIGN.md` §1)
**v2 source:** `version2/results/v2_benchmark_q01-q05.md`
**v2 model tier:** oss (`gemma4:26b` via Ollama)

## v1 T4.3 baseline (per REDESIGN.md §1)

- `float` scoring: q03 less_good < wrong (FAIL); q05 less_good < wrong (FAIL).
  q01, q02, q04 held the ordering.
- `round` scoring: q05 wrong ≥ less_good (FAIL). q01–q04 held.
- `int` scoring: held for q01–q05 (but 80% of scores were 0 due to truncation,
  so the ordering is uninformative).

## v2 results (this run)

| Question | Converged | Iterations used | Violations on held-out |
|---|---|---|---|
| q01 | <fill> | <fill> | <fill> |
| q02 | <fill> | <fill> | <fill> |
| q03 | <fill> | <fill> | <fill> |
| q04 | <fill> | <fill> | <fill> |
| q05 | <fill> | <fill> | <fill> |

## Summary

<2–3 sentences: which questions converged for v2 vs which were ordering-violating for v1.
Be cautious: v2 violations are computed on the held-out validation answers per Karpathy loop,
not on the same answer-set v1 was scored on. Direct comparability is approximate.>
```

Replace the `<fill>` and `<2-3 sentences>` placeholders with real values before committing.

- [ ] **Step 2: Write `version2/README.md`**

```markdown
# version2 — self-contained v2 benchmark

This folder contains a vendored copy of the v2 grading pipeline and everything
it needs to run the ordering benchmark in isolation.

## Run the benchmark

From the repo root (`autograder/`):

```bash
cd version2
PYTHONPATH=. ../.venv/bin/python scripts/run_v2_benchmark.py \
    --questions q01,q02,q03,q04,q05 \
    --tier oss \
    --report results/v2_benchmark_q01-q05.md
```

The log file is auto-derived from the report path (`results/v2_benchmark_q01-q05.log`).

## Run the tests

```bash
cd version2
PYTHONPATH=. ../.venv/bin/python -m pytest tests/v2/ -v
```

Current count (as of vendoring commit): <fill from Task 6 step 4>.

## Layout

- `v2/` — vendored from `autograder/v2/` (no edits)
- `config/llm_config.py` — vendored from `autograder/config/llm_config.py`
- `config/rubric_generation.yaml` — vendored verbatim
- `scripts/run_v2_benchmark.py` — vendored; `PDF_PATH` re-anchored to `sources/`
- `tests/v2/` — vendored from `autograder/tests/v2/`
- `sources/slides_data_type_quality.pdf` — vendored from `autograder/grading_pipeline/sources/`
- `results/` — benchmark output target

## Self-containment guarantee

```bash
grep -r "autograder\|grading_pipeline\|retrieval_core" version2/ \
    --include="*.py" --include="*.yaml" --include="*.md" \
    | grep -v "version2/README.md\|version2/results/v1_v2_comparison.md\|version2/scripts/run_v2_benchmark.py:.*\".*#"
```
Should return nothing functionally affecting execution (matches are limited to docstrings and the comparison-doc reference).
```

Substitute the test-count placeholder.

- [ ] **Step 3: Verify self-containment**

Run:
```bash
grep -rn "autograder\|grading_pipeline\|retrieval_core" version2/ --include="*.py" --include="*.yaml" | grep -v "^Binary"
```
Expected: matches only inside `version2/scripts/run_v2_benchmark.py` docstring (lines 9 and 11–13) — these are comments, not code paths. If a match appears in actual code or YAML data, fix before committing.

- [ ] **Step 4: Commit**

```bash
git add version2/results/v1_v2_comparison.md version2/README.md
git commit -m "version2: comparison vs v1 baseline and README"
```

---

## Task 10: Update JOURNAL.md and finalize

- [ ] **Step 1: Get current time**

```bash
date "+%Y-%m-%d %H:%M"
```

- [ ] **Step 2: Prepend a JOURNAL entry**

Open `JOURNAL.md` and prepend (after the leading `---`) a new entry of this shape:

```markdown
## YYYY-MM-DD HH:MM — version2/ vendored; v2 q01–q05 ordering benchmark on oss tier

Created self-contained `version2/` folder with vendored copies of `v2/`,
`config/llm_config.py`, `config/rubric_generation.yaml`, the slides PDF,
`tests/v2/`, and `scripts/run_v2_benchmark.py` (with `PDF_PATH` re-anchored).
All v2 tests pass from inside `version2/`. Benchmark ran on q01–q05 with
`gemma4:26b` (oss tier); results in `version2/results/v2_benchmark_q01-q05.md`
and the v1 comparison in `version2/results/v1_v2_comparison.md`. Outcome:
<one-line summary of converged/non-converged counts>.

### Details

<Optional: per-question table if it adds value; otherwise omit and end the
entry above.>
```

Replace `YYYY-MM-DD HH:MM` with the time from Step 1 and the `<…>` placeholders with the real summary.

- [ ] **Step 3: Commit JOURNAL last**

```bash
git add JOURNAL.md
git commit -m "journal: YYYY-MM-DD HH:MM — version2/ vendored; q01–q05 benchmark on oss tier"
```

(Substitute the timestamp.)

- [ ] **Step 4: Final sanity check**

```bash
git log --oneline -12
git status --short
```
Expected:
- The last ~10 commits show the version2 vendoring + benchmark sequence.
- `git status` is clean (no `M` files, no untracked files inside `version2/`).

If untracked or modified files remain inside `version2/`: investigate, do not blindly add. Some may be log files written by the benchmark that you intended to commit (Tasks 7–8 did that); others may be byproducts you do not want in git.

---

## What this plan does NOT cover

- Wiring `retrieval_core/` into `ConceptJudge` — separate work, deferred.
- Running the foundational or mixed tiers — single-tier (`oss`) only this round.
- Deleting `autograder/v2/`, `autograder/tests/v2/`, `autograder/scripts/run_v2_benchmark.py` after parity — explicitly out of scope; `version2/` is parallel until the benchmark verifies the approach.
- q06–q10 — no v1 baseline; needs synthetic answers first.
- Cleaning up the ~100 untracked scratch files (`a`, `err`, `output_q01.txt`, etc.) in `autograder/` — separate hygiene task.
- Updating `SNAPSHOT.md` — defer until the benchmark result tells us whether v2 has been promoted to first-class status.

---

## Risks and recovery

| Risk | Trigger | Recovery |
|---|---|---|
| Ollama crashes mid-run | `ConnectionError` or empty response from the LLM call | Restart Ollama via launchd agent, rerun with `--questions <remaining>`. |
| `pypdf` extraction returns empty text | The vendored PDF is corrupted or pypdf misreads it | `cd version2 && ../.venv/bin/python -c "from pypdf import PdfReader; r = PdfReader('sources/slides_data_type_quality.pdf'); print(sum(len(p.extract_text() or '') for p in r.pages))"` should print a large number (~50k chars). If 0: re-copy the PDF in binary mode. |
| `configure_llm_for_tier` fails to import in vendored config | Some llm_config dep is missing from `.venv/` | Run `../.venv/bin/python -c "from config.llm_config import configure_llm_for_tier"` inside `version2/` and read the actual error. Surface to user; do not install new packages. |
| Tests pass standalone but fail under benchmark | Stateful Ollama session bleeds between tests | Acceptable for this round; document in the README. |
| Benchmark converges trivially (0 iterations on all questions) | Karpathy loop terminates too eagerly because the rubric generator is producing useless rubrics that get 0/0 violations | Inspect `version2/results/v2_benchmark_q01-q05.log` for actual scores; if scores are all 0, the issue is in rubric generation or judge prompt — surface to user, do not silently accept. |
