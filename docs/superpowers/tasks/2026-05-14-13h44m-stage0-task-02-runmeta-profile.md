# Stage 0 Task 2 — Add `RunMeta.profile` schema field

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 2 — **Status:** Complete — **Date:** 2026-05-14 13:44

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `f2a2c3a` | `feat(grading-plugin): add RunMeta.profile field` |

## Files

- Modified: `plugins/grading/python/schema.py` (+1 line in `RunMeta`)
- Modified: `plugins/grading/python/tests/test_schema.py` (+2 tests)

## Symbols introduced

- `RunMeta.profile: str | None = None` — records which config profile a run used; written into `run_meta.yaml` by the run-init step (Task 5).

## Tests

- `test_run_meta_profile_defaults_to_none`, `test_run_meta_profile_accepts_string`.
- `test_schema.py`: 20 passing.

## Reviewers

- Spec compliance: ✅ — exactly one line added to `RunMeta` after `stages_run`; exactly the two named tests appended; nothing else touched.
- Code quality: ✅ Approved — declaration consistent with adjacent `str | None = None` fields; tests correctly scoped and match file style.

## Notes

- TDD: the failing test confirmed `ValidationError: Extra inputs are not permitted` before the field was added (`RunMeta` is `_Strict` / `extra="forbid"`).
