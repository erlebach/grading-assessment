# Stage 0 Task 9 — `_translate_pdf` via the `marker_single` CLI

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 9 — **Status:** Complete — **Date:** 2026-05-14 14:17

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `61d8aea` | `feat(grading-plugin): _translate_pdf via marker_single subprocess` |
| `afc246b` | `fix(grading-plugin): correct marker_single image-extraction flag + hoist pypdf import` (review fix) |

## Files

- Modified: `plugins/grading/python/translate_sources.py` (+49 then fix — 4 functions appended)
- Modified: `plugins/grading/python/tests/test_translate_sources.py` (+66 — `import fitz`, `_make_pdf` helper, 3 tests)

## Symbols introduced

- `_marker_pdf_version() -> str` — `marker-pdf` package version via `importlib.metadata`, falls back to `"unknown"`.
- `_pdf_page_count(pdf_path) -> int` — via `pypdf.PdfReader` (a main dependency; pymupdf is test-only).
- `_invoke_marker_single(input_pdf, output_dir, marker_cfg)` — the one external-process seam; shells out to the `marker_single` CLI, raises `RuntimeError` on non-zero exit.
- `_translate_pdf(source_path, dest_dir, marker_cfg) -> (page_count, figure_count, extraction)` — composes invocation + `_ingest_marker_single_output` + page count + extraction metadata; hard-errors on empty `content.md`.

## Tests

- `test_translate_pdf_happy_path` (monkeypatches the `_invoke_marker_single` seam), `test_translate_pdf_errors_on_empty_content`, `test_invoke_marker_single_raises_on_nonzero`.
- `test_translate_sources.py`: 12 passing. Full plugin suite: 128 passing.

## Reviewers

- Spec compliance: ✅ — 4 functions + 3 tests match the plan's Task 9 blocks verbatim; `_pdf_page_count` uses `pypdf`; Tasks 7-8 untouched; no later-task functions added.
- Code quality: initial review **Changes needed** → fix commit `afc246b` → **re-review ✅ Approved**.
  - Fixed: the plan's `--extract_images <value>` argv was wrong — `--extract_images` is not the right CLI toggle; the real `marker_single` CLI uses the flag `--disable_image_extraction` (mirroring `--disable_ocr`). Verified against `marker_single --help`.
  - Fixed: `pypdf` import hoisted from inside `_pdf_page_count` to module level.

## Notes

- TDD: the 3 new tests failed with `AttributeError` (`_translate_pdf` / `_invoke_marker_single` not yet defined) before the functions were appended.
- The code-quality review caught a genuine plan defect (wrong marker CLI flag) — corrected in `afc246b`.
