# Task 5 — pipeline.yaml

**Plan:** §Task 5 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `ae2910e` | `feat(grading-plugin): pipeline.yaml knobs (seeds, calibration, bands, parallelism)` |

## Files

- Created: `plugins/grading/config/pipeline.yaml`
- Created: `plugins/grading/python/tests/test_pipeline_config.py`

## Knobs encoded

- `seeds_per_type`: default 8, topical_domains_min 6, composition {curated=2, source=2, claude_knowledge=4}, validation_pass_enabled true.
- `calibration`: max_iterations 6, split {train=0.60, val=0.20, test=0.20}, three threshold mins (0.85, 0.90, 0.25), proceed_on_warning false.
- `score_bands`: good=[0.85,1.00], less_good=[0.40,0.70], wrong=[0.00,0.30] — gaps at (0.30,0.40) and (0.70,0.85) for genuine discrimination.
- `generate_rubric`: 3+3+3 quality answers, 1 perturbation per axis, 3 overlay-refinement iters.
- `parallelism`: max_parallel_questions=3, max_parallel_seeds=4.
- `retries`: max_redispatches=2.

## Tests

5 passing: `test_pipeline_exists`, `test_seeds_per_type_composition_sums_to_total`, `test_score_bands_present_and_ordered`, `test_calibration_thresholds_present`, `test_parallelism_knobs_present`. All check invariants (arithmetic, ordering, ranges), not just key presence.

## Reviewers

- Implementer (haiku): DONE.
- Spec reviewer (haiku): ✅
- Code-quality reviewer (haiku): ✅

## Notes

5 of 24 tasks complete. All Task 1–5 config + scaffold work done; Tasks 6–11 begin the Python schema models. Suite stands at 16 plugin tests passing.
