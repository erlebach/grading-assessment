---
name: translate-sources
description: Stage 0 procedure — translate one PDF (via the marker_single CLI) or markdown source into canonical content.md + figures + meta.yaml under the active run folder.
---

# translate-sources (Stage 0)

Translate one source file into the active run folder. Fully deterministic —
PDFs go through the `marker_single` CLI (marker-pdf package); markdown is a
verbatim passthrough. No subagent, no LLM.

## Spec reference

`docs/superpowers/specs/2026-05-14-stage0-translate-sources-design.md`

## Inputs read

- A `.pdf` or `.md` file (conventionally placed under `preprocessing/inputs/sources_raw/`)
- The active run folder's `config.yaml` (`marker_single:` knobs)

## Outputs written (into the active run folder)

- `sources/<source_name>/content.md`
- `sources/<source_name>/figures/<figure-name>` — marker_single's extracted
  figures (PDFs) or copied inline images (markdown)
- `sources/<source_name>/meta.yaml` — validated `SourceMeta`
- `traces/translate_sources/timeline.jsonl` — one `python_helper_call` event

## Procedure

Invoke the Python helper directly:

```bash
.venv/bin/python -m plugins.grading.python.translate_sources <source_path> \
    [--name <source_name>] [--run <prefix>] [--force]
```

The helper resolves the active run folder (most-recent unless `--run` is
given), skips sources already translated in that run (unless `--force`), and
hard-errors if `marker_single` cannot produce usable content — there is no
LLM fallback.

## Failure modes

- No run folder exists → error directing the user to `/grade:init`.
- `marker_single` exits non-zero or yields empty `content.md` → hard error,
  surfaced to the user; an empty `sources/<source_name>/` directory may be left
  behind — re-running (without `--force`) will retry the translation, since the
  skip-if-present check requires a valid `content.md` + `meta.yaml`.
- Unsupported file type (not `.pdf` / `.md`) → `ValueError`.
