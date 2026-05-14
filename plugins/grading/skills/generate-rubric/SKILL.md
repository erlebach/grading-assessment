---
name: generate-rubric
description: Stage 3 procedure — for one assessment question, generate synthetic answers + per-question concept overlay + gold coverage against the frozen universal rubric.
---

# generate-rubric (Stage 3)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 3.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.4.

## Inputs read

- `inputs/questions/<course>/<q>.yaml`
- `types/<type>/universal_rubric.yaml` (must be `status: frozen` or `--proceed-on-warning`)
- `sources/<source>/content.md` for the question's `sources`

## Outputs written

- `rubrics/<course>/<q>/rubric.yaml`
- `synthetic_answers/<course>/<q>/{answers.yaml, gold_concept_coverage.yaml}`
- `rubrics/<course>/<q>/iterations/iter_NN/` per overlay refinement iteration
- `traces/generate_rubric/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. Pre-flight: refuse if universal status is `warning_test_marginal` (without override) or `failed_to_converge`.
2. Dispatch one `question_workup` subagent that emits answers + axis perturbations + overlay + gold coverage.
3. Sanity-check via `judge` subagent; if fail, dispatch `overlay_critic` and iterate up to `overlay_refinement_iterations`.
4. On exhaustion, status `degraded` (this question only; run continues for others).

## Failure modes

- Universal rubric not frozen → refuse (unless `--proceed-on-warning`).
- Overlay refinement exhausted → status `degraded`.
