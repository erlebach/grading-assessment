---
name: test-universal
description: Ad-hoc Stage 2 test pass — dispatches fresh seed_gen + materialize_seed + judge against the frozen universal rubric for sanity-checking.
---

# test-universal

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 2.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.3 step 8.

## Inputs read

- `types/<type>/universal_rubric.yaml` (frozen)

## Outputs written

- `types/<type>/adhoc_test_<timestamp>.yaml`
- `traces/calibrate_types/<subagent_id>.json` for the ad-hoc dispatches

## Algorithm summary (implementation deferred)

Fresh `seed_gen` (N seeds) → `materialize_seed` per seed → `judge` per seed → criterion check. Does **not** modify the frozen `status`.
