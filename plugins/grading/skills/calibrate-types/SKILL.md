---
name: calibrate-types
description: Stage 2 procedure — calibrate per-type universal rubric via materialize_seed + judge + critic loop until concept-vote / score-band / axis-discrimination criteria all pass on val, then test on the held-out test set.
---

# calibrate-types (Stage 2)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 2.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.3.

## Inputs read

- `seed_questions/<type>/*.yaml` where `user_review.approved == true`
- `inputs/type_catalog.yaml`
- `config/pipeline.yaml` (`calibration.*`)

## Outputs written

- `types/<type>/universal_rubric.yaml` (frozen or warning)
- `types/<type>/calibration_meta.yaml`
- `types/<type>/test_results.yaml`
- `types/<type>/seed_artifacts/<seed_id>/{concept_overlay.yaml, synthetic_answers.yaml, gold_concept_coverage.yaml}`
- `types/<type>/iterations/iter_NN/{candidate_rubric.yaml, val_judge_outputs.yaml, val_criterion_outcomes.yaml, critic_proposal.yaml}`
- `traces/calibrate_types/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. Initialize: load candidate axes, uniform weights; dispatch `axis_criterion_drafter` per type.
2. For each seed: dispatch `materialize_seed` (parallel up to `max_parallel_seeds`).
3. Split train / val / test deterministically by `SHA(seed_id)`.
4. Iterate up to `max_iterations`:
   - Dispatch `judge` per val seed.
   - Aggregate via `plugins/grading/python/aggregation.py`.
   - Check the three criteria.
   - If all pass: break.
   - Else: dispatch `critic` with train-set failures; apply revisions; persist `iter_NN/`.
5. Held-out test pass with frozen-candidate rubric.
6. Status tag: `frozen` (all pass), `warning_test_marginal` (val pass, test fail), or `failed_to_converge` (max_iterations hit).

## Failure modes

- judge / critic subagent malformed output → one redispatch, then hard fail on critic, soft fail on judge (mark val outcome `partial`).
- max_iterations without val pass → status `failed_to_converge`, halt run.
- val pass + test fail → status `warning_test_marginal`, halt at universal layer unless `--proceed-on-warning`.
