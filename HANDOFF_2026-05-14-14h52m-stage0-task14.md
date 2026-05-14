# Handoff — Stage 0 plan execution, paused before Task 14

**Date:** 2026-05-14 14:52 EDT
**Branch:** `version2-self-contained-benchmark`
**HEAD:** `239a367`
**Status:** Tasks 1–13 of 15 complete. **Task 14 not started** (its subagent dispatch was interrupted by the user). Task 15 pending.

## What this is

Executing the Stage 0 implementation plan via the **subagent-driven-development** workflow:
- Plan: `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` (15 tasks, TDD).
- Spec: `docs/superpowers/specs/2026-05-14-stage0-translate-sources-design.md`.
- Per task: dispatch a fresh implementer subagent (model `sonnet`) with the **full task text pasted in** (do not make it read the plan file), then a spec-compliance reviewer subagent, then a code-quality reviewer subagent. Fix-loop until both pass. Then write a per-task completion record and commit it.

## Progress: Tasks 1–13 done

Plugin test suite is **green at 139 tests** (`/.venv/bin/python -m pytest plugins/grading/python/tests/ -q`). What was built:
- `marker-pdf` dependency added (provides the `marker_single` CLI).
- `schema.RunMeta.profile` field; `pipeline.yaml` gained `marker_single:` + `profiles:` blocks.
- `plugins/grading/python/run_init.py` — `init_run()` + `/grade:init` command.
- `plugins/grading/python/translate_sources.py` — full Stage 0 translate pipeline: `_resolve_source_name`, `_is_already_translated`, `_rewrite_image_links`, `_ingest_marker_single_output`, `_marker_pdf_version`, `_pdf_page_count`, `_invoke_marker_single`, `_translate_pdf`, `_translate_markdown`, `_finalize`, `translate_source()`, `_load_marker_config`, `_append_timeline`, `main()`.
- `/grade:translate` command + real `translate-sources` SKILL.md wired.

Reviews caught (and fixed) real defects along the way: wrong marker CLI flag (`--extract_images` → `--disable_image_extraction`), dead `_finalize` `name` param, `--runs-dir`→`--runs-root` consistency, a utf-8-encoding hardening sweep, and several doc inaccuracies.

## Deviations from the plan text (already applied — do NOT re-introduce)

- `_finalize` signature is `(dest_dir, fmt, page_count, figure_count, extraction)` — the plan text's `name`/`source_name` arg was removed (Task 11 review). `translate_source` calls it with 5 args.
- The CLI flag is `--runs-root` (not the plan's `--runs-dir`) in both `run_init.py` and `translate_sources.py`.
- All Stage 0 text I/O uses `encoding="utf-8"` explicitly.

## NEXT: Task 14 — Live-verification baseline

This is the one task that runs the **real `marker_single` CLI** (everything else stubs it). Read Task 14 in the plan file for the full text. Key adaptations / gotchas to brief the implementer with:

1. **Synthetic PDF, not a "real" downloaded paper.** The plan Step 1 says "obtain a small real PDF" — a subagent can't fetch one. Instead, generate a 2-page synthetic PDF at `preprocessing/inputs/sources_raw/baseline.pdf` with `pymupdf` (`fitz`): text via `page.insert_text(...)` on both pages, plus an embedded raster image via `page.insert_image(...)` on page 2 so marker has a figure to detect. Do NOT commit the PDF or the generator; paste the generator code into the task report for documentation. (Spec §6.2 explicitly sanctions a synthetic `pymupdf` PDF.)
2. **Sandbox:** the real `marker_single` downloads ML weights from huggingface.co and writes to `~/.cache/` — outside the sandbox-writable set. The Bash calls running `marker_single` will likely need `dangerouslyDisableSandbox: true` (Task 1 hit the same with the `uv` cache). Retry with it disabled if an "Operation not permitted"/cache/network error appears.
3. **Timeout:** `marker_single` is slow (download + inference). Use `timeout: 600000` on the `translate_sources` Bash call.
4. **Run for real:**
   `.venv/bin/python -m plugins.grading.python.run_init` → note the printed `<run_id>`.
   `.venv/bin/python -m plugins.grading.python.translate_sources preprocessing/inputs/sources_raw/baseline.pdf`
5. **Freeze:** `cp -r preprocessing/runs/<run_id>/sources/baseline/. plugins/grading/python/tests/fixtures/stage0_baseline/` (gives `content.md`, `meta.yaml`, `figures/`). If marker extracted 0 figures, that's acceptable — the baseline is still valid.
6. **Regression test:** create `plugins/grading/python/tests/test_stage0_baseline.py` (exact code is in Task 14 Step 4 of the plan — 3 tests: content nonempty, meta validates against `SourceMeta` with `extraction.role == "marker_single"`, figure links resolve). Use `encoding="utf-8"` on the `read_text` calls.
7. **Do NOT fake it.** If `marker_single` genuinely cannot run, report BLOCKED — the whole point is a real marker run. Do NOT hand-edit the frozen `meta.yaml` to make the test pass; it is ground truth.
8. **Clean up + commit:** `rm -rf preprocessing/inputs preprocessing/runs` (only — they are untracked). Then `git add` ONLY `plugins/grading/python/tests/fixtures/stage0_baseline` + `plugins/grading/python/tests/test_stage0_baseline.py` (never `git add -A`). Commit message: `test(grading-plugin): frozen Stage 0 live-verification baseline`.

Expected suite after Task 14: **142** (139 + 3 baseline tests).

## Then: Task 15 — Full-suite verification

Run the full plugin suite + the broader project check (`tests/` with `--ignore=tests/tmp_chroma_indexes`); commit any fix needed. After Task 15, the subagent-driven-development workflow's terminal step is a final whole-implementation code review, then `superpowers:finishing-a-development-branch`.

## Per-task completion records (user requirement)

After each task's two reviews pass, write a completion record to `docs/superpowers/tasks/` named `YYYY-MM-DD-HHhMMm-stage0-task-NN-<slug>.md` (timestamped to stay distinct from the 23-task foundation plan's `2026-05-13-task-NN-*.md` records). Follow the format of the existing `2026-05-14-*-stage0-task-*.md` files. Commit each record with `docs(grading-plugin): Stage 0 per-task record NN`. Records for Tasks 1–13 are already written and committed. (This preference is also saved in `~/.claude/memory/feedback/plan-execution-task-records.md`.)

## Task-tracker state

The harness task list has items #6–#20 = Stage 0 Tasks 1–15. #6–#18 (Tasks 1–13) are `completed`; #19 (Task 14) is `in_progress`; #20 (Task 15) is `pending`. On resume, keep #19 `in_progress`, dispatch the Task 14 implementer, and proceed.

## Resume recipe

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
git log --oneline -3            # expect HEAD = 239a367
.venv/bin/python -m pytest plugins/grading/python/tests/ -q   # expect 139 passed
```
Then re-enter the `superpowers:subagent-driven-development` workflow and dispatch the Task 14 implementer per the briefing above.
