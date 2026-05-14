# Task 16 — PDF render (pymupdf)

**Plan:** §Task 16 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `009f226` | `feat(grading-plugin): pymupdf-based page rendering for Stage 0` |

## Files

- Created: `plugins/grading/python/pdf_render.py`
- Created: `plugins/grading/python/tests/test_pdf_render.py`

## Symbols introduced

- `PageRenderResult` — frozen dataclass: `pdf_path`, `out_dir`, `page_count`, `figure_paths: list[Path]`.
- `render_pages(pdf_path, out_dir, *, dpi=150) -> PageRenderResult` — opens the PDF with `pymupdf`, writes one PNG per page to `<out_dir>/page_NNN.png` with 3-digit zero padding, and returns metadata. `dpi` is keyword-only so positional drift across callers is impossible.

## Tests

3 passing: one-PNG-per-page, zero-padding format, output dir auto-creation. The fixture builds a 2-page PDF in `tmp_path` via `pymupdf.open()` + `new_page()` so no binary fixture is committed. Full plugin suite: 72 passing.

## Reviewers

- Implementer (haiku): DONE.
- Spec-compliance reviewer (haiku): ✅ — files match plan verbatim, only 2 files in commit, co-author trailer present.
- Code-quality reviewer (haiku): ✅ Approved — single responsibility, proper resource handling (`pymupdf.open()` as ctx mgr), `from __future__ import annotations` so `list[Path]` works, no overbuilding.

## Notes

`pymupdf` was already declared in `pyproject.toml` (Task 1) and installed at version 1.27.2.3 in the local `.venv`; no dep work was needed for this task. The fixture-based PDF generation pattern (`new_page` + `insert_text` + `save`) is reusable for Stage 0 tests downstream.
