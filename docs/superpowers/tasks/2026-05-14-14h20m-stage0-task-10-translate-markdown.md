# Stage 0 Task 10 — `_translate_markdown`

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 10 — **Status:** Complete — **Date:** 2026-05-14 14:20

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `dac4848` | `feat(grading-plugin): _translate_markdown passthrough + inline-image copy` |

## Files

- Modified: `plugins/grading/python/translate_sources.py` (+18 — one function appended)
- Modified: `plugins/grading/python/tests/test_translate_sources.py` (+30 — 2 tests)

## Symbols introduced

- `_translate_markdown(source_path, dest_dir) -> (0, figure_count, None)` — the markdown-source path: verbatim copy to `content.md` with image links rewritten into `figures/`, local inline images copied into `figures/`. No pages, no extraction tool.

## Tests

- `test_translate_markdown_passthrough_and_image_copy`, `test_translate_markdown_no_images`.
- `test_translate_sources.py`: 14 passing. Full plugin suite: 130 passing.

## Reviewers

- Spec compliance: ✅ — function + 2 tests match the plan's Task 10 blocks verbatim; Tasks 7-9 untouched; no later-task functions added.
- Code quality: ✅ Approved with follow-up items — clean, single-responsibility, lazy `figures/` creation correct, parallel structure with `_ingest_marker_single_output`. Follow-ups (non-blocking): missing referenced image is silently skipped (no test); `read_text`/`write_text` calls lack `encoding="utf-8"` (gap shared with `_ingest_marker_single_output` — likely relevant given LaTeX/accented academic content).

## Notes

- TDD: the 2 new tests failed with `AttributeError` (`_translate_markdown` not yet defined) before the function was appended.
- **Carry-forward:** an `encoding="utf-8"` hardening sweep across `translate_sources.py` text I/O is queued as a dedicated commit after Task 12 (once all text I/O exists), per the reviewer's suggestion.
