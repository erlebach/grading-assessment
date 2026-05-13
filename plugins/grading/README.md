# grading plugin

Gold-standard preprocessing benchmark for the autograder. See the spec at
`docs/superpowers/specs/2026-05-13-grading-plugin-design.md` for full design.

## Slash commands

| Command | Purpose |
|---|---|
| `/grading:translate <source>` | Stage 0 — translate a PDF or markdown source into canonical form. |
| `/grading:seeds` | Stage 1 — build the cross-topic seed-question pool. |
| `/grading:review-seeds` | Interactive review gate for seed questions. |
| `/grading:calibrate` | Stage 2 — calibrate universal-layer rubrics per question type. |
| `/grading:test-universal` | Ad-hoc test pass against fresh Claude-generated seeds. |
| `/grading:question --course <c> --question <q>` | Stage 3 — generate per-question rubric + synthetic answers. |
| `/grading:gold-grade --course <c> --question <q>` | Stage 4 — Claude judge applies rubric, writes gold reference scores. |
| `/grading:course <course_id>` | Orchestrator — runs Stages 3 + 4 across every question in a course. |
| `/grading:status` | Inspect current run state. |
| `/grading:diff <run_a> <run_b>` | Semantic diff between two runs. |

## MAX quota note

Every LLM operation runs through Claude Code subagents under the user's MAX
subscription. No Anthropic API key is read or required. Roles map to tiers via
`config/tier_dispatch.yaml`.

## Repo layout

See `docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §8.

## Python helpers

`python/` contains deterministic helpers (schema validation, aggregation,
diff, snapshot, run resolution, pdf render). No LLM code. Run tests:

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
```
