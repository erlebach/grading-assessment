---
name: run-course
description: Orchestrator skill — runs generate-rubric + gold-grade for every question in a course, in parallel up to max_parallel_questions, after verifying Stages 0–2 prerequisites.
---

# run-course

**Status: stub.** Full orchestration deferred to the per-stage plan for the orchestrator.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.6.

## Inputs read

- `inputs/questions/<course>/*.yaml`
- All prerequisite Stage-0/1/2 artifacts in the active run folder

## Outputs written

- All Stage-3 and Stage-4 artifacts per question.
- `runs/<id>/summary_<course>.yaml`

## Algorithm summary (implementation deferred)

1. Verify prerequisites: refuse if `sources/`, `seed_questions/`, or `types/` is missing for any required type.
2. Dispatch per-question subagents in parallel (cap: `max_parallel_questions`). Each runs Stage 3 then Stage 4 sequentially.
3. After all complete: write `summary_<course>.yaml` (per-question status, aggregate-by-quality, dispatch counts, elapsed times).

## Failure modes

- Missing prerequisite → refuse with explicit message naming the missing artifact.
- Per-question failure → record `degraded` in summary; run continues.
