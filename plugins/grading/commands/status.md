---
description: "Print the current run's state: stage completion, pending questions, last error."
---

Run the Python helper in `plugins/grading/python/`:

```bash
.venv/bin/python -m plugins.grading.python.validate_run --runs-root preprocessing/runs
```

This will print `OK: <run_dir>` or `FAIL: <run_dir>` plus a list of failing artifacts.

## Arguments

- `--run <prefix>` — target a specific run folder; defaults to most recent

## Status

Stub.
