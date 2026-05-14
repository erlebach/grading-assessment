---
description: "Stage 0 — translate a PDF or markdown source into canonical content.md + figures + meta.yaml under the active run folder."
---

Use the `grading:translate-sources` skill to translate one source file into
the active run folder.

## Arguments

- `<source_path>` — path to a `.pdf` or `.md` file (conventionally placed under
  `preprocessing/inputs/sources_raw/`)
- `--name <source_name>` — override the auto-derived source name (filename
  stem, lowercased + snake_cased)
- `--run <prefix>` — target a specific run folder (prefix match);
  defaults to the most-recent run
- `--force` — re-translate even if this source is already translated in the
  target run

## Prerequisites

A run folder must exist — run `/grade:init` first. PDFs require the
`marker_single` CLI on PATH (installed via the `marker-pdf` dependency).
