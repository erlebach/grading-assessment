---
name: gold-grade
description: Stage 4 procedure — apply Claude judge to all synthetic answers for one question, batched in one subagent dispatch, producing the gold reference scores.
---

# gold-grade (Stage 4)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 4.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.5.

## Inputs read

- `rubrics/<course>/<q>/rubric.yaml`
- `synthetic_answers/<course>/<q>/answers.yaml`
- `types/<type>/universal_rubric.yaml`

## Outputs written

- `grades/<course>/<q>/grades.yaml`
- `traces/gold_grade/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. Dispatch one `judge` subagent per question, batching all answers × (concept, axis) pairs.
2. `plugins/grading/python/aggregation.py:compute_aggregate` per answer.
3. Emit per-question summary (`mean_by_quality`, `ordering_preserved`, `bands_satisfied`, `axis_discrimination_passed`).
4. Flag `degraded` if bands or ordering fail.

## Failure modes

- judge output malformed → one redispatch, then hard fail (this is the gold standard).
- bands_satisfied == false or ordering_preserved == false → question flagged `degraded`; run continues.
