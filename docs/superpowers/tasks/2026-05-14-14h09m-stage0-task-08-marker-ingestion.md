# Stage 0 Task 8 — image-link rewriting + marker_single output ingestion

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 8 — **Status:** Complete — **Date:** 2026-05-14 14:09

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `e4b3005` | `feat(grading-plugin): marker_single output ingestion + image-link rewriting` |

## Files

- Modified: `plugins/grading/python/translate_sources.py` (+33 — two appended functions)
- Modified: `plugins/grading/python/tests/test_translate_sources.py` (+44 — import + 4 tests)

## Symbols introduced

- `_rewrite_image_links(markdown, prefix="figures") -> str` — repoints local image links into the `figures/` subdir; leaves `http(s)://` and absolute `/...` paths untouched.
- `_ingest_marker_single_output(marker_out_dir, dest_dir) -> int` — finds the single `.md` in the `marker_single` output tree (`rglob`), relocates it to `dest_dir/content.md` with links rewritten, copies sibling images into `dest_dir/figures/`; returns figure count. Hard-errors if not exactly one `.md`.

## Tests

- `test_rewrite_image_links_prefixes_local_images`, `test_rewrite_image_links_leaves_external_urls`, `test_ingest_marker_single_output_relocates_and_rewrites`, `test_ingest_marker_single_output_errors_on_zero_md`.
- `test_translate_sources.py`: 9 passing. Full plugin suite: 125 passing.

## Reviewers

- Spec compliance: ✅ — both functions and 4 tests match the plan's Task 8 blocks verbatim; Task 7 code untouched; no later-task functions added.
- Code quality: ✅ Approved with minor notes — clean single-responsibility functions, correct types, `shutil.copy2` preserves metadata. Non-blocking edge cases (pre-existing / inherited from the plan, marker output unlikely to hit them): basename collision when two images share a name across subdirs; `_IMG_LINK_RE` does not parse markdown title attributes; scattered test-import block + in-function `import pytest` (cosmetic, as written in the plan); no `>1 .md` test.

## Notes

- TDD: the 4 new tests failed with `ImportError` before the functions were appended.
