# Task 1 — Add pymupdf + hypothesis deps; pytest config

**Plan:** [`docs/superpowers/plans/2026-05-13-grading-plugin-foundation.md`](../plans/2026-05-13-grading-plugin-foundation.md) §Task 1
**Branch:** `version2-self-contained-benchmark`
**Status:** Complete (with follow-up fix commit)
**Date:** 2026-05-13

## Goal

Add `pymupdf>=1.24` and `hypothesis>=6.100` to the project's dev dependencies, and configure pytest to discover both the legacy `tests/` and the new `plugins/grading/python/tests/` trees.

## Commits

| SHA | Message |
|---|---|
| `92a44e1` | `chore: add pymupdf + hypothesis dev deps and pytest config for grading plugin` |
| `fa05f54` | `fix(grading-plugin): lock pymupdf + hypothesis in uv.lock; fix plan's pip-install step` |

## Files

- Modified: `pyproject.toml` — added `pymupdf`, `hypothesis` to `[dependency-groups] dev`; added `[tool.pytest.ini_options]` with `pythonpath=["."]` and `testpaths=["tests", "plugins/grading/python/tests"]`.
- Modified: `uv.lock` — locked pymupdf 1.27.2.3, hypothesis 6.152.7, plus transitive sortedcontainers 2.4.0.
- Modified (plan): `docs/superpowers/plans/2026-05-13-grading-plugin-foundation.md` — Step 4 of Task 1 rewritten to use `uv lock` + `uv sync` instead of `pip install`.

## Tests

- TDD smoke test (`test_deps_smoke.py`) created, confirmed failing, then deleted after the deps installed — per plan.
- `.venv/bin/python -c "import pymupdf, hypothesis; print('ok')"` → `ok`.

## Reviewers

- **Implementer (haiku):** DONE — followed plan literally, including the buggy `pip install` step.
- **Spec reviewer (haiku):** ✅ Spec compliant against the plan as written.
- **Code-quality reviewer (haiku):** ✅ Approved — TOML valid, version pins reasonable, no scope creep.

## Issues encountered

**Latent lockfile drift** caught by the user post-hoc: the plan instructed `.venv/bin/pip install`, which installed the deps into the venv but did NOT update `uv.lock`. The implementer + both reviewers all reported green because `import pymupdf; import hypothesis` worked from the venv. On a fresh checkout, however, `uv sync` would have read the unchanged `uv.lock` and not installed either package, breaking every downstream task at import time.

Fix:
1. Ran `uv lock` (sandbox-disabled, since uv writes to `~/.cache/uv/`) to refresh `uv.lock` against `pyproject.toml`.
2. Ran `uv sync` to apply.
3. Verified both packages now appear in `uv.lock`.
4. Updated the plan to replace `pip install` with `uv lock` + `uv sync`.
5. Recorded the lesson in `~/.claude/memory/feedback/uv-vs-pip.md`. A pre-existing `tools/uv.md` already said the same thing — I should have respected it.

## Lesson for the reviewer prompt going forward

When a plan adds Python deps, the spec/code-quality reviewer should explicitly check that `uv.lock` was updated alongside `pyproject.toml`. A `pyproject.toml`-only diff is a drift bug, not a clean change.
