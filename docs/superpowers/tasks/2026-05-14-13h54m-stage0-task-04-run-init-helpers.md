# Stage 0 Task 4 — `run_init.py` fingerprint / run-id / deep-merge helpers

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 4 — **Status:** Complete — **Date:** 2026-05-14 13:54

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `b799998` | `feat(grading-plugin): run_init fingerprint + run-id + deep-merge helpers` |

## Files

- Created: `plugins/grading/python/run_init.py` (+47 — module + three pure helpers)
- Created: `plugins/grading/python/tests/test_run_init.py` (+38 — 4 tests)

## Symbols introduced

- `_deep_merge(base, overrides) -> dict` — recursive non-mutating dict merge.
- `_run_fingerprint(merged_config, git_sha) -> str` — 4-char SHA-256 fingerprint of `yaml.safe_dump(config, sort_keys=True) + git_sha`.
- `_generate_run_id(now, fingerprint) -> str` — `YYYY-MM-DD_HH-MM-SSZ__<fingerprint>`.

The module also forward-declares imports (`argparse`, `subprocess`, `sys`, `RunMeta`, `create_snapshot`, ...) that Task 5's `init_run()` / `main()` consume — intentional per the plan.

## Tests

- `test_deep_merge_overrides_nested_keys`, `test_run_fingerprint_is_deterministic`, `test_run_fingerprint_changes_with_input`, `test_generate_run_id_format`.
- `test_run_init.py`: 4 passing. Full plugin suite: 111 passing.

## Reviewers

- Spec compliance: ✅ — both files match the plan's Task 4 code line-by-line; no `init_run()`/`main()` added early.
- Code quality: ✅ Approved — pure single-responsibility helpers; `copy.deepcopy` guarantees non-mutation; `sort_keys=True` makes the fingerprint deterministic. Minor cosmetic notes only (a rationale comment for the 4-char truncation would be nice).

## Notes

- TDD: all 4 tests failed with `ModuleNotFoundError` before the module existed.
