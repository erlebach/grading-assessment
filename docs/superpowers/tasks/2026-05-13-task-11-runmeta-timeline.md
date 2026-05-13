# Task 11 — RunMeta + Config + Calibration + Answers + Coverage + Timeline

**Plan:** §Task 11 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `8217627` | `feat(grading-plugin): RunMeta/Config/Calibration/Answers/Coverage/Timeline schemas` |

## Files

- Modified: `plugins/grading/python/schema.py` — appended 11 new symbols (see below).
- Modified: `plugins/grading/python/tests/test_schema.py` — appended 6 tests.

## Symbols introduced

- `RunStatus(str, Enum)` — `success | partial | failed`.
- `RunMeta` — top-level `runs/<id>/run_meta.yaml`: run id + timestamps + git state + worst-stage status.
- `RunConfig` — mirror of `config/pipeline.yaml`. Field types are loose `dict` on purpose — pipeline.yaml knob additions shouldn't break run replay.
- `CalibrationMeta` — Stage 2 audit log: train/val/test seed lists, per-iteration history, final criterion outcomes.
- `AnswerQuality(str, Enum)` — `good | less_good | wrong | axis_perturbation`.
- `SyntheticAnswer` — per-answer record. Field validator on `target_axis` enforces the invariant: axis_perturbation answers MUST set `target_axis`; other qualities MUST NOT.
- `SyntheticAnswerSet` — list wrapper.
- `GoldConceptCoverage` — `answer_id → concept_id → axis → Level` 3-level nested dict.
- `TimelineEventType` — 6 event types from spec §5.6.
- `TimelineEventPhase` — `start | end`.
- `TimelineEvent` — single row of `traces/<stage>/timeline.jsonl`.

## Tests

18 in `test_schema.py` (12 prior + 6 new). Full plugin suite: 41 passing.

## Reviewers

- Implementer (haiku): DONE.
- Combined spec + code-quality reviewer (haiku): ✅ Approved (no issues).

## Notes

- The `SyntheticAnswer` field validator on `target_axis` runs only AFTER `quality` is parsed (pydantic v2 field-validators see prior fields via `info.data`). Declaration order in the class body (`quality` before `target_axis`) is therefore load-bearing — don't reorder.
- `RunConfig`'s deliberately loose `dict` fields trade compile-time type safety for forward compatibility. Acceptable because RunConfig is reconstructive (a record of what was used), not prescriptive.

This closes the schema work. Tasks 12+ move to deterministic helpers (aggregation, snapshot, diff, pdf_render, run_resolution).
