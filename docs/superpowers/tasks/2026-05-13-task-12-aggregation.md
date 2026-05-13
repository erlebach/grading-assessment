# Task 12 — Aggregation formula §3.3

**Plan:** §Task 12 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `c2725a9` | `feat(grading-plugin): aggregation formula (§3.3) with Q03 worked-example test` |

## Files

- Created: `plugins/grading/python/aggregation.py`
- Created: `plugins/grading/python/tests/test_aggregation.py`

## Symbols introduced

- `LEVEL_VALUES = {"full": 1.0, "partial": 0.5, "none": 0.0}` — the canonical mapping. Same string values as the schema's `Level` enum, but distinct so the compute-time code doesn't import from `schema`.
- `JudgeVote(concept_id, axis, level)` — frozen dataclass; the input to aggregation.
- `AggregateResult(per_concept_score, aggregate, aggregate_x10)` — frozen dataclass; the output.
- `compute_aggregate(*, axis_weights, concept_weights, concept_relevant_axes, votes) -> AggregateResult`:
  - Step 1: `score(c) = Σ over a∈relevant(c): w(a)·level_value(vote(c,a)) / Σ w(a)`.
  - Step 2: `aggregate = Σ w(c)·score(c) / Σ w(c)`.
  - `aggregate_x10 = aggregate * 10.0`.
  - Raises `KeyError` if a declared (concept, axis) pair has no matching vote — natural Python behavior, not wrapped.

## Tests

5 passing: spec-constant check, Q03 worked example (8.9479 within 1e-2 of spec's 8.95), all-full → 1.0, all-none → 0.0, missing-vote raises.

## Reviewers

- Implementer (sonnet): DONE.
- Combined spec + code-quality reviewer (haiku): ✅ Approved (no issues).

## Notes

Per-concept and final aggregate both normalize by Σ(weights) defensively — handles unnormalized inputs gracefully without affecting correctness for the validated `Σ=1.0` case used in production.

Module-level `LEVEL_VALUES` is duplicated in spirit with the schema's `Level` enum string values; keeping them separate so `aggregation.py` has no schema dependency (it operates on plain dataclasses for fast compute).
