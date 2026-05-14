# Stage 0 Task 3 — Add `marker_single:` and `profiles:` config blocks

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 3 — **Status:** Complete — **Date:** 2026-05-14 13:46

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `76b4bc9` | `feat(grading-plugin): add marker_single and profiles config blocks` |

## Files

- Modified: `plugins/grading/config/pipeline.yaml` (+14 — two appended top-level blocks)
- Modified: `plugins/grading/python/tests/test_pipeline_config.py` (+19 — two appended tests)

## What

- `marker_single:` block — knobs for the `marker_single` CLI: `ocr: false`, `extract_images: true`.
- `profiles:` block — named config-override profiles; `smoke` dials count knobs (`seeds_per_type.default`, `generate_rubric.*_count`) down to 1 for fast test runs.

## Tests

- `test_marker_single_block_present`, `test_profiles_block_has_smoke`.
- `test_pipeline_config.py`: 7 passing.

## Reviewers

- Spec compliance: ✅ — verified directly (`git show 76b4bc9 --stat`). Note: the first spec-review subagent gave a false negative (stale filesystem view, claimed the commit was missing); the commit exists and is correct.
- Code quality: ✅ Approved — YAML + test style consistent with existing blocks; clean append. Minor inherited-from-spec notes: `axis_perturbation_count_per_axis` set in YAML but not asserted in the smoke test; `ocr` comment phrasing slightly awkward.

## Notes

- TDD: both new tests failed with `KeyError: 'marker_single'` / `KeyError: 'profiles'` before the YAML was appended.
