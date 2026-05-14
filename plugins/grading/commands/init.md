---
description: "Create and bootstrap a new preprocessing run folder (skeleton, frozen config, src snapshot, run_meta)."
---

Create a new run folder by invoking the run-init helper directly:

```bash
.venv/bin/python -m plugins.grading.python.run_init [--profile <name>]
```

This creates `preprocessing/runs/<run_id>/` with the stage subdirectory
skeleton, a frozen merged `config.yaml`, `src_snapshot.tar.gz`, and
`run_meta.yaml`. The run folder is self-contained from the moment it exists.

## Arguments

- `--profile <name>` — apply a named profile from `pipeline.yaml`'s `profiles:`
  block (e.g. `smoke` dials all count knobs down to 1 for fast test runs).
  The profile's overrides are deep-merged onto the base config and frozen into
  the run's `config.yaml`; the profile name is recorded in `run_meta.yaml`.

## Notes

Run `/grade:init` once per pipeline run, before `/grade:translate` and the
later stages. Subsequent stages default to the most-recent run folder.
If you edit source code after `/grade:init`, discard the run and re-init —
the `src_snapshot.tar.gz` is frozen at init time.

See `plugins/grading/python/run_init.py` for the implementation.
