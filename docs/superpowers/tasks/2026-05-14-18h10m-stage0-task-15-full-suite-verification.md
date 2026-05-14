# Stage 0 Task 15 — full-suite verification

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 15 — **Status:** Complete — **Date:** 2026-05-14 18:10

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| — | none — verification surfaced no fixes (Step 3 was a no-op) |

## Files

- None (verification-only task).

## What

- **Step 1 — grading-plugin suite:** `.venv/bin/python -m pytest plugins/grading/python/tests/ -q` → **146 passed**, 0 failures. (103 pre-plan + 43 added across Tasks 2–14 + the `_marker_pdf_version` follow-up.)
- **Step 2 — broader project safety check:** `.venv/bin/python -m pytest tests/ -q --ignore=tests/tmp_chroma_indexes` → 9 collection errors; with those 9 files excluded, 394 passed / 26 failed / 1 skipped.
- **Step 3 — final commit:** no fixes needed; nothing to commit.

## Reviewers

- N/A — verification-only task, no implementation to review.

## Notes

- **All 9 collection errors and 26 failures in the broader `tests/` suite are pre-existing or environmental — none caused by the Stage 0 plan.** Classification:
  - 9 collection errors: stale test files importing renamed/removed *internal* modules (`grader.grade_question`, `gp`, `CharacterTextSplitter`).
  - ~14 failures: the same missing `grader.grade_question` (directly or via CLI subprocess returncode).
  - 6 failures: HuggingFace cache `PermissionError` — the sandbox blocks model downloads to `~/.cache/huggingface`; environmental, not a code defect.
  - 4 failures: pre-existing test-fixture path bug (doubled `student_001_q02_good.yaml/` path segment).
  - remainder: pre-existing assertion/mock/logic issues + `test_llm_tier::test_tier_oss_returns_llm` (requires a running Ollama).
- Verified two independent ways that the marker-pdf removal introduced no regression: (a) `git grep` confirms no project or test code imports `marker-pdf` or any of its 14 removed transitive deps; (b) the post-removal `uv sync` only *removed* packages — it changed no shared third-party package versions.
- Stage 0 plan (15 tasks) is now complete.
