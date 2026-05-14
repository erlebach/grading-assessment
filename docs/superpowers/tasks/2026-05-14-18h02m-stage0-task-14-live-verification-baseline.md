# Stage 0 Task 14 — live-verification baseline (manual marker run, frozen fixture)

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 14 — **Status:** Complete — **Date:** 2026-05-14 18:02

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `c461221` | `test(grading-plugin): frozen Stage 0 live-verification baseline` |

## Files

- Created: `plugins/grading/python/tests/fixtures/stage0_baseline/content.md` — frozen real `marker_single` output.
- Created: `plugins/grading/python/tests/fixtures/stage0_baseline/meta.yaml` — frozen `SourceMeta`.
- Created: `plugins/grading/python/tests/fixtures/stage0_baseline/figures/_page_1_Picture_2.jpeg` — extracted figure (~15 KB).
- Created: `plugins/grading/python/tests/test_stage0_baseline.py` — 3-test regression guard (verbatim from plan).

## What

- The one task that exercises the **real** `marker_single` CLI end-to-end. A synthetic 2-page PDF (text on both pages + an embedded raster image on page 2) was generated with `pymupdf`, run through `run_init` + `translate_sources`, and the resulting `sources/baseline/` directory frozen as a committed fixture.
- The input PDF and the generator script were **not** committed; the generator code is preserved in the task report only.
- `test_stage0_baseline.py` asserts the fixture stays well-formed: `content.md` non-empty, `meta.yaml` validates against `SourceMeta` with `format == "pdf"` / `extraction.role == "marker_single"`, and every relative figure link resolves to a real file.

## Tests

- `test_stage0_baseline.py`: 3 passing. Full plugin suite: **142 passing** (139 prior + 3 new).

## Reviewers

- Spec compliance: ✅ — test file matches the plan verbatim; fixture is genuine `marker_single` output (real `content_sha`, characteristic marker artifacts: `\_` escaping, `$$…$$` math block, `![](figures/…)` link); commit touches exactly the 4 declared files; no scratch leakage.
- Code quality: ✅ **Approved** — no Critical/Important issues. Two Minor observations, both informational-only (no trailing newline in `content.md` is authentic marker output and must be preserved; `meta.yaml` numeric fields `figure_count`/`page_count` are not asserted, but plan did not require it).

## Notes

- **`extraction.tier: marker-pdf==unknown`** in the frozen `meta.yaml` is expected, not a defect. `_marker_pdf_version()` resolves the version via `importlib.metadata.version("marker-pdf")`, but `marker-pdf` was intentionally removed from the project venv earlier this session (it is an external `uv tool` install). A follow-up fixes `_marker_pdf_version()` to record the real version.
- The real `marker_single` run required `dangerouslyDisableSandbox` — its ML model weights live under `~/Library/Caches/datalab`, outside the sandbox-writable set.
- `marker_single` resolves via PATH to the external `~/.local/bin/marker_single` (marker-pdf 1.10.2); there is no longer a venv-bundled copy to shadow it.
