# Stage 0 Task 12 — `translate_source()` entry + timeline + CLI

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 12 — **Status:** Complete — **Date:** 2026-05-14 14:37

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `f36a3e1` | `feat(grading-plugin): translate_source entry + timeline event + CLI` |
| `0978cc7` | `fix(grading-plugin): unify --runs-root flag, consistent marker-config default, +skip/unsupported-type tests` (review fix) |
| `87d7a40` | `fix(grading-plugin): explicit utf-8 encoding on Stage 0 text I/O` (cross-cutting hardening; resolves Task 10 carry-forward) |

## Files

- Modified: `plugins/grading/python/translate_sources.py` — `translate_source`, `_load_marker_config`, `_append_timeline`, `main` appended; `--runs-root` rename; `_DEFAULT_MARKER_CONFIG` constant; utf-8 encoding sweep.
- Modified: `plugins/grading/python/run_init.py` — `--runs-root` rename; utf-8 encoding sweep.
- Modified: `plugins/grading/python/tests/test_translate_sources.py` — `_run_dir_with_config` helper + 6 tests (5 from Task 12 + 1 unsupported-type from the review fix).

## Symbols introduced

- `translate_source(source_path, run_dir, *, name=None, force=False) -> Path` — the public Stage 0 entry point: resolve name → skip-if-present → dispatch `.pdf`/`.md` → `_finalize` → timeline event.
- `_load_marker_config(run_dir) -> dict` — reads the run's `config.yaml` `marker_single:` block, falls back to `_DEFAULT_MARKER_CONFIG`.
- `_append_timeline(run_dir, source_name, *, skipped)` — appends one `python_helper_call` `TimelineEvent` line to `traces/translate_sources/timeline.jsonl`.
- `main(argv=None) -> int` — CLI; resolves the active run (most-recent unless `--run`), errors with a `/grade:init` hint if none exists.
- `_DEFAULT_MARKER_CONFIG` module constant.

## Tests

- 6 new: end-to-end markdown, skip-if-present (+ timeline assertion), `--force`, missing-file, no-run-folder CLI error, unsupported-type `ValueError`.
- `test_translate_sources.py`: 23 passing. Full plugin suite: 139 passing.

## Reviewers

- Spec compliance: ✅ — matches the plan's Task 12 blocks; the one intended deviation (`_finalize` called without `source_name`, per Task 11's fix) applied correctly.
- Code quality: **Changes needed** → fix `0978cc7` → **re-review ✅ Approved**.
  - Fixed: `--runs-dir` → `--runs-root` across `run_init.py` + `translate_sources.py` (consistency with `validate_run.py`); `_load_marker_config` now returns one shared default in both fallback branches; added skip-path timeline assertion + unsupported-type test.

## Notes

- TDD: the 5 new tests failed with `AttributeError` (`translate_source` / `main` not yet defined) before the implementation was appended.
- `87d7a40` is a cross-cutting hardening commit (not part of any single plan task): explicit `encoding="utf-8"` on all Stage 0 text I/O — resolves the carry-forward flagged in the Task 10 review. `translate_sources.py` is now complete.
