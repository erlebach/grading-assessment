# Task 3 — role_catalog.yaml

**Plan:** [`docs/superpowers/plans/2026-05-13-grading-plugin-foundation.md`](../plans/2026-05-13-grading-plugin-foundation.md) §Task 3
**Branch:** `version2-self-contained-benchmark`
**Status:** Complete
**Date:** 2026-05-13

## Goal

Canonicalize the 10 subagent roles dispatched by the grading plugin's stages, with one-line descriptions and stage attribution per role. This file is the source of truth that `config/tier_dispatch.yaml` (Task 4) binds to model tiers.

## Commits

| SHA | Message |
|---|---|
| `52e2f77` | `feat(grading-plugin): role catalog with 10 declared subagent roles` |

## Files

- Created: `plugins/grading/config/role_catalog.yaml`
- Created: `plugins/grading/python/tests/test_role_catalog.py`

## Roles declared

`pdf_translator`, `seed_gen`, `seed_validator`, `materialize_seed`, `axis_criterion_drafter`, `judge`, `critic`, `overlay_critic`, `question_workup`, `gold_annotator`.

## Tests

3 passing: `test_catalog_exists`, `test_catalog_has_all_expected_roles`, `test_every_role_has_description`.

## Reviewers

- **Implementer (haiku):** DONE.
- **Spec reviewer (haiku):** ✅ Spec compliant.
- **Code-quality reviewer (haiku):** ✅ Approved. Minor consistency observation on `gold_annotator`'s longer description; left as-is (acceptable).

## Issues encountered

None.
