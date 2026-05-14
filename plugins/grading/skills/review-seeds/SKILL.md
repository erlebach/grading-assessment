---
name: review-seeds
description: Interactive review gate for seed questions — main agent presents each unreviewed seed for user approve / reject / edit, writes user_review back to disk.
---

# review-seeds

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 1.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.2 "User review gate".

## Inputs read

- `seed_questions/<type>/<seed_id>.yaml` with `user_review.approved` unset

## Outputs written

- Same files, with `user_review` populated.
- `traces/prepare_seed_questions/timeline.jsonl` append-only (`gate_decision` events).

## Algorithm summary (implementation deferred)

1. Iterate unreviewed seeds.
2. For each: show seed text + topic + source provenance.
3. Accept user input: approve / reject / edit.
4. Write `user_review.approved` and optional `note` back to the seed file.

## Failure modes

None at LLM level — pure interaction. Schema invariants enforced on write.
