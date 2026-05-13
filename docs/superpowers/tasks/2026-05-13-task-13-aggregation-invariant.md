# Task 13 — Aggregation property tests (hypothesis)

**Plan:** §Task 13 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `6c895b9` | `test(grading-plugin): property-based invariants for aggregation` |

## Files

- Created: `plugins/grading/python/tests/test_aggregation_invariant.py`

## What's exercised

A custom hypothesis composite strategy `rubric_strategy()` generates random rubrics:
- 1–5 axes with positive normalized weights.
- 1–5 concepts with positive normalized weights.
- Per concept, a unique non-empty subset of axes as `relevant_axes`.
- One judge vote per declared (concept, axis) pair, label drawn from `{full, partial, none}`.

3 properties, each with `max_examples=200, deadline=None` → 600 randomized aggregations:
1. `aggregate ∈ [0, 1]`.
2. `aggregate_x10 ≈ aggregate * 10` within `1e-9` AND `aggregate_x10 ∈ [0, 10]`.
3. No NaN in `aggregate` or `per_concept_score`.

## Tests

3 hypothesis tests passing, no health-check warnings.

## Reviewers

- Implementer (haiku): DONE.
- Combined spec + code-quality reviewer (haiku): ✅ Approved (no issues).

## Notes

`min_value=0.01` for the random weights deliberately avoids exercising the `den == 0` defensive fallback in `compute_aggregate` — the property tests focus on the typical normalized case. That fallback is still covered by the unit tests in Task 12.
