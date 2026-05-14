# Preprocessing — external `marker_single` requirement

The Stage 0 preprocessing pipeline (`plugins/grading/python/translate_sources.py`,
exposed as `/grade:translate`) converts PDF source documents to normalized
markdown by shelling out to the **`marker_single` CLI** from the
[`marker-pdf`](https://pypi.org/project/marker-pdf/) package.

`marker-pdf` is **not** a project dependency and is intentionally absent from
`pyproject.toml`. Every user who runs the preprocessing pipeline must install
the `marker_single` CLI separately.

## Why it is not a project dependency

- It is a heavy standalone CLI (pulls `torch`, `surya-ocr`, large transitive
  tree) — the project code never imports the `marker` package, it only invokes
  the CLI as a subprocess.
- When `marker-pdf` was a project dependency, `.venv/bin/marker_single`
  shadowed the user's own install on `PATH`, and the version the lockfile
  resolved to (`marker-pdf==1.5.5` / `surya-ocr==0.12.1`) fails to load the
  current Surya model weights with a stack trace.

## Install

Install it as an isolated `uv` tool (its own interpreter, on `PATH`,
independent of the project venv):

```bash
uv tool install marker-pdf
```

This places `marker_single` at `~/.local/bin/marker_single`. Confirm it is
found:

```bash
which marker_single        # -> ~/.local/bin/marker_single
marker_single --help
```

Verified working: **`marker-pdf` 1.10.2 / `surya-ocr` 0.17.1**.
`marker-pdf` 1.5.5 is known to be broken (Surya weights format mismatch) —
do not pin to it.

## How the pipeline finds it

The pipeline invokes the bare command `marker_single` via `subprocess.run`,
so it is resolved through `PATH`. Ensure no other `marker_single` (e.g. an old
copy inside a project `.venv`) precedes `~/.local/bin` on your `PATH`.

OCR is disabled by default (`marker_single ... --disable_ocr`; see
`config/pipeline.yaml` → `marker_single.ocr`). On first run, `marker_single`
downloads model weights to `~/Library/Caches/datalab` (macOS).
