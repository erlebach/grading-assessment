---
description: "Semantic diff between two run folders — universal rubrics, per-question rubrics, grades."
---

Run the Python helper from `plugins/grading/python/`:

```bash
.venv/bin/python -c "from plugins.grading.python.diff import diff_runs; from pathlib import Path; import sys; d = diff_runs(Path(sys.argv[1]), Path(sys.argv[2])); print(d)" -- <run_a> <run_b>
```

A user-facing CLI wrapper around `diff_runs` arrives in a later plan.

## Arguments

- `<run_a>` — first run prefix or path
- `<run_b>` — second run prefix or path

## Status

Stub.
