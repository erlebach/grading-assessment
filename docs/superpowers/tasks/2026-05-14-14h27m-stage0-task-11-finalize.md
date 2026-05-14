# Stage 0 Task 11 — `_finalize` (content_sha + meta.yaml)

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 11 — **Status:** Complete — **Date:** 2026-05-14 14:27

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `41972e4` | `feat(grading-plugin): _finalize writes validated meta.yaml` |
| `641fa8b` | `fix(grading-plugin): drop unused name parameter from _finalize` (review fix) |

## Files

- Modified: `plugins/grading/python/translate_sources.py` (+17 then fix — one function appended)
- Modified: `plugins/grading/python/tests/test_translate_sources.py` (+44 — `SourceMeta` import + 3 tests)

## Symbols introduced

- `_finalize(dest_dir, fmt, page_count, figure_count, extraction) -> Path` — computes the SHA-256 `content_sha` over `content.md`, builds the `meta.yaml` dict (`courses`/`topics` empty lists — Stage 0 has no input for them), validates against `schema.SourceMeta` (hard invariant), writes `meta.yaml`.

## Tests

- `test_finalize_writes_valid_meta`, `test_finalize_markdown_extraction_none`, `test_finalize_content_sha_tracks_content`.
- `test_translate_sources.py`: 17 passing. Full plugin suite: 133 passing.

## Reviewers

- Spec compliance: ✅ — function + 3 tests matched the plan's Task 11 blocks verbatim; Tasks 7-10 untouched; no later-task functions added.
- Code quality: **Approved with minor reservations** → fix commit `641fa8b` addressed the one Important item.
  - Fixed: `_finalize` had a dead `name` parameter (in the signature, never used, no `name` field in `SourceMeta`) — a plan defect. Removed from the signature and the 4 test call sites.
  - Remaining minor notes (not actioned, low value): no docstring; `_finalize`'s `Path` return is currently untested.

## Notes

- TDD: the 3 new tests failed with `AttributeError` (`_finalize` not yet defined) before the function was appended.
- **Plan deviation for Task 12:** `_finalize`'s signature is now `(dest_dir, fmt, page_count, figure_count, extraction)` — the plan's Task 12 code calling `_finalize(dest_dir, source_name, fmt, ...)` must drop `source_name`.
