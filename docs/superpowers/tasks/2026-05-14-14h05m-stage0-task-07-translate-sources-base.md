# Stage 0 Task 7 — `translate_sources.py` name resolution + skip-if-present

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 7 — **Status:** Complete — **Date:** 2026-05-14 14:05

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `9aef2e6` | `feat(grading-plugin): translate_sources name resolution + skip-if-present` |

## Files

- Created: `plugins/grading/python/translate_sources.py` (+58 — module skeleton)
- Created: `plugins/grading/python/tests/test_translate_sources.py` (+41 — 5 tests)

## Symbols introduced

- Module docstring + all imports (many forward-declared for Tasks 8-12 — intentional).
- `_IMG_LINK_RE`, `_IMAGE_SUFFIXES` — module constants.
- `_resolve_source_name(source_path, name) -> str` — `--name` override, else filename stem lowercased + non-alphanumeric runs collapsed to `_`.
- `_is_already_translated(dest_dir) -> bool` — true iff `content.md` + a `SourceMeta`-valid `meta.yaml` both exist.

## Tests

- 5 tests covering snake-casing, `--name` override, and the three skip-if-present branches (missing / invalid meta / valid).
- `test_translate_sources.py`: 5 passing. Full plugin suite: 121 passing.

## Reviewers

- Spec compliance: ✅ — both files match the plan's Task 7 blocks line-for-line; no later-task functions added early.
- Code quality: ✅ Approved — helpers clean, correctly typed, single-responsibility; tests verify real behavior. Minor deferred notes: `_resolve_source_name` returns `""` for an all-non-alphanumeric stem (worth a guard when wired in at Task 12); `_is_already_translated` does not catch `OSError` (inherited from spec).

## Notes

- TDD: all 5 tests failed with `ModuleNotFoundError` before the module existed.
- **Carry to Task 12:** consider a guard rejecting an empty derived source name.
