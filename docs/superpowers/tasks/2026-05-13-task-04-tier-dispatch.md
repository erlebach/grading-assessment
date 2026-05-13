# Task 4 — tier_dispatch.yaml

**Plan:** §Task 4 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `f8a6b22` | `feat(grading-plugin): tier_dispatch.yaml binding all 10 roles to Claude tiers` |

## Files

- Created: `plugins/grading/config/tier_dispatch.yaml`
- Created: `plugins/grading/python/tests/test_tier_dispatch.py`

## Tier bindings

- claude-opus-4-7 (heaviest): pdf_translator, materialize_seed, judge, critic, question_workup, gold_annotator
- claude-sonnet-4-6 (mid): seed_gen, axis_criterion_drafter, overlay_critic (also `default_tier`)
- claude-haiku-4-5 (cheap): seed_validator

## Tests

4 passing: `test_default_tier_supported`, `test_every_role_in_catalog_is_mapped`, `test_every_mapped_role_exists_in_catalog`, `test_every_mapped_tier_supported`. Tests cross-check against `role_catalog.yaml`; only `SUPPORTED_TIERS` is hard-coded.

## Reviewers

- Implementer (haiku): DONE.
- Spec reviewer (haiku): ✅
- Code-quality reviewer (haiku): ✅

## Notes

None.
