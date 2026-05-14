---
name: translate-sources
description: Stage 0 procedure — convert a PDF or markdown source into canonical content.md + figures + meta.yaml under the active run folder.
---

# translate-sources (Stage 0)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 0.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.1.

## Inputs read

- `inputs/sources_raw/<source>/<original>.{pdf,md}` in the active run folder
- `plugins/grading/config/pipeline.yaml` (`pdf_translator` knobs)
- `plugins/grading/config/tier_dispatch.yaml`

## Outputs written

- `sources/<source>/content.md`
- `sources/<source>/figures/page_NNN.png` (PDFs only)
- `sources/<source>/meta.yaml`
- `traces/translate_sources/<subagent_id>.json` per dispatched subagent
- `traces/translate_sources/timeline.jsonl` append-only

## Algorithm summary (implementation deferred)

1. Resolve active run folder via `python -m plugins.grading.python.run_resolution`.
2. For each source under `inputs/sources_raw/`:
   - If PDF: invoke `plugins/grading/python/pdf_render.py:render_pages` to emit `page_NNN.png`, then dispatch one `role: pdf_translator` subagent to produce `content.md`. Write `meta.yaml`.
   - If markdown: passthrough to `content.md`; write `meta.yaml`.
3. Emit a `python_helper_call` and `subagent_dispatch` timeline event around each operation.
4. Halt the stage if any artifact fails validation; surface to the user.

## Failure modes

- PDF render error → stage halts; trace records `error` event with the offending file path.
- pdf_translator subagent returns malformed markdown → one redispatch, then hard fail.
