# Task 14 — Run resolution (`--run <prefix>`)

**Plan:** §Task 14 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `4ba7783` | `feat(grading-plugin): --run prefix resolution helper`  |

## Files

- Created: `plugins/grading/python/run_resolution.py`
- Created: `plugins/grading/python/tests/test_run_resolution.py`

## Symbols introduced

- `NoRunMatch(LookupError)` and `AmbiguousRunPrefix(LookupError)` — the latter carries `prefix` and `candidates` attributes for programmatic handling.
- `_list_run_dirs(runs_dir) -> list[Path]` — returns sorted-ascending dir entries, or `[]` if `runs_dir` doesn't exist.
- `resolve_run(prefix, runs_dir) -> Path` — git-style prefix matching: exact match wins; otherwise unique prefix match; otherwise raise.
- `most_recent_run(runs_dir) -> Path` — last of sorted list (lexical = chronological because run IDs start with `YYYY-MM-DD_HH-MM-SSZ__`).

## Tests

6 passing: exact, unique-prefix, ambiguous-prefix, no-match, most-recent, empty-runs-dir. Full plugin suite: 65 passing.

## Reviewers

- Implementer (haiku): DONE.
- Combined spec + code-quality reviewer (haiku): ✅ Approved (no issues).

## Notes

Self-contained module — no imports from `schema` or `aggregation`. CLI commands and `validate_run` (Task 19) will use this for `--run <prefix>` argument resolution.
