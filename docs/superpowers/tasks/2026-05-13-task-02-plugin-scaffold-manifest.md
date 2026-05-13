# Task 2 — Plugin scaffold + manifest

**Plan:** [`docs/superpowers/plans/2026-05-13-grading-plugin-foundation.md`](../plans/2026-05-13-grading-plugin-foundation.md) §Task 2
**Branch:** `version2-self-contained-benchmark`
**Status:** Complete
**Date:** 2026-05-13

## Goal

Stand up the `plugins/grading/` package skeleton: empty `__init__.py` chain (so subsequent test files can `from plugins.grading.python.<x> import ...`), test-side `conftest.py` for sys.path, the `.claude-plugin/plugin.json` manifest at the format Claude Code actually expects, a `README.md`, and a 4-assertion test that locks the manifest fields.

## Commits

| SHA | Message |
|---|---|
| `7c5a6be` | `feat(grading-plugin): scaffold plugin manifest, package layout, README` |

## Files created

- `plugins/__init__.py` (empty)
- `plugins/grading/__init__.py` (empty)
- `plugins/grading/python/__init__.py` (empty)
- `plugins/grading/python/tests/__init__.py` (empty)
- `plugins/grading/python/tests/contracts/__init__.py` (empty)
- `plugins/grading/python/tests/conftest.py` — adds repo root to sys.path
- `plugins/grading/.claude-plugin/plugin.json` — manifest
- `plugins/grading/README.md` — slash-command quick reference + MAX quota note
- `plugins/grading/python/tests/test_plugin_manifest.py` — 4 tests

## Tests

```
plugins/grading/python/tests/test_plugin_manifest.py::test_manifest_file_exists       PASSED
plugins/grading/python/tests/test_plugin_manifest.py::test_manifest_is_valid_json     PASSED
plugins/grading/python/tests/test_plugin_manifest.py::test_manifest_required_fields   PASSED
plugins/grading/python/tests/test_plugin_manifest.py::test_manifest_author_present    PASSED
```

Repo regression: full pre-existing 183-test suite still green.

## Reviewers

- **Implementer (haiku):** DONE — caught and fixed a `parents[3]` typo in the plan (correct value: `parents[2]`).
- **Spec reviewer (haiku):** ✅ Spec compliant. Confirmed `parents[2]` fix.
- **Code-quality reviewer (haiku):** ✅ Approved. No issues found.

## Issues encountered

**Plan typo:** the plan as I originally wrote it had `PLUGIN_ROOT = Path(__file__).resolve().parents[3]`. From `plugins/grading/python/tests/test_plugin_manifest.py`, `parents[2]` is `plugins/grading/` — the correct value. Implementer noticed the resulting test would fail and fixed it inline. Plan document was patched after the fact so future re-execution lines up.

## Lessons

When a plan contains parent-directory arithmetic, the writing-plans self-review needs to trace from the test file's actual location, not from an assumed depth.
