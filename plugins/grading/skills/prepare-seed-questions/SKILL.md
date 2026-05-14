---
name: prepare-seed-questions
description: Stage 1 procedure — build the cross-topic seed-question pool per type (curated + source-derived + Claude-knowledge).
---

# prepare-seed-questions (Stage 1)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage 1.

## Spec reference

`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.2.

## Inputs read

- `inputs/seed_questions_curated/<type>/*.yaml`
- `inputs/type_catalog.yaml`
- `sources/<source>/content.md` (for source-derived generation)
- `config/pipeline.yaml` (`seeds_per_type` composition + thresholds)

## Outputs written

- `seed_questions/<type>/<seed_id>.yaml` (one file per seed, normalized)
- `traces/prepare_seed_questions/<subagent_id>.json` + `timeline.jsonl`

## Algorithm summary (implementation deferred)

1. For each type in `inputs/type_catalog.yaml`:
   - Load curated seeds verbatim.
   - Dispatch one `role: seed_gen` subagent for the Claude-knowledge share.
   - Dispatch one `role: seed_gen` subagent per relevant translated source for the source-derived share.
   - Optionally dispatch one `role: seed_validator` subagent if `validation_pass_enabled`.
   - Normalize all seeds to the SeedQuestion schema and write to disk.
2. Flag seeds with `user_review.approved: null` for `/grading:review-seeds`.

## Failure modes

- seed_gen subagent returns invalid JSON → one redispatch, then mark batch as `partial`, continue with next type.
- Composition shortfall (curated < requested) → rebalance into Claude-knowledge bucket per spec §4.2.
