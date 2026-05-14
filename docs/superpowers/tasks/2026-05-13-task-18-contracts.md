# Task 18 — Subagent output contract schemas

**Plan:** §Task 18 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `0946f29` | `feat(grading-plugin): subagent output contract schemas (judge/critic/materialize_seed/seed_gen)` |

## Files

- Created: `plugins/grading/python/contracts.py`
- Created: `plugins/grading/python/tests/contracts/test_judge_output_schema.py`
- Created: `plugins/grading/python/tests/contracts/test_critic_output_schema.py`
- Created: `plugins/grading/python/tests/contracts/test_materialize_seed_output_schema.py`
- Created: `plugins/grading/python/tests/contracts/test_seed_gen_output_schema.py`

(`tests/contracts/__init__.py` predated this task and was not touched.)

## Symbols introduced

- `_Strict(BaseModel)` — common base with `extra="forbid"` and `frozen=True`. All output models inherit it.
- **Judge:** `JudgeRow`, `JudgeOutput`.
- **Critic:** `CriticRevisionKind` (`WEIGHT`, `CRITERION`), `CriticWeightRevision`, `CriticCriterionRevision`, the union alias `CriticRevision`, and `CriticOutput`.
- **Materialize-seed:** `MaterializeSeedAnswer` (with optional `target_axis`), `MaterializeSeedOutput` — uses `model_post_init` to enforce **both directions** of the rule "axis_perturbation iff target_axis is set".
- **Seed-gen:** `SeedGenSeed`, `SeedGenOutput`.

Re-uses `Level`, `AnswerQuality`, and `ConceptOverlayEntry` from `schema.py` rather than duplicating their definitions.

## Tests

10 passing across 4 files:
- Judge: well-formed accept; bad `level` reject; missing `rationale` reject.
- Critic: weight revision accept; criterion revision accept; unknown `kind` reject.
- Materialize-seed: good fixture accept; axis_perturbation without `target_axis` reject.
- Seed-gen: good fixture accept; missing `topic` reject.

Full plugin suite: 85 passing.

## Reviewers

- Implementer (haiku): DONE.
- Spec-compliance reviewer (haiku): ✅ — verbatim match against plan, both directions of the `target_axis` invariant present, only 5 files in diff, `__init__.py` not touched.
- Code-quality reviewer (haiku): ✅ Approved — discriminated union via `Literal[kind]` defaults, `extra="forbid"` + `frozen=True` consistent, errors include the offending `answer_id`.

## Notes

`CriticRevision` is a Python `|`-union of two strict models, each pinned to a `Literal[CriticRevisionKind.X]` default for `kind`. Pydantic resolves the discriminator by matching against the literal at validation time. The `Field(min_length=1)` constraints across strings and lists are the cheap way to forbid empty payloads without writing per-field validators.
