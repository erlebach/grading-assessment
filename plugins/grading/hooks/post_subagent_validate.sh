#!/usr/bin/env bash
# Post-subagent validation hook.
# Re-runs validate_run against the most-recent run folder under preprocessing/runs.
# Exit 0 = OK; exit 1 = at least one artifact failed schema validation.
#
# Status: stub. The per-stage plan that introduces an active-run pointer will
# wire this to the actual active run folder rather than always picking the
# most recent one.

set -euo pipefail

if [[ ! -d "preprocessing/runs" ]]; then
  # No runs yet — nothing to validate.
  exit 0
fi

.venv/bin/python -m plugins.grading.python.validate_run \
  --runs-root preprocessing/runs
