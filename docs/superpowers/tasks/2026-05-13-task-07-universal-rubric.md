# Task 7 — UniversalRubric + validate_universal_rubric

**Plan:** §Task 7 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `ddbc48e` | `feat(grading-plugin): UniversalRubric schema + validate_universal_rubric` |
| `1dd1f8f` | `chore(grading-plugin): drop unused Annotated import from schema.py + plan` |

## Files

- Modified: `plugins/grading/python/schema.py` — appended ScoreLevelEntry, ScoreLevels, AxisDef, Aggregate, UniversalRubricStatus, UniversalRubric, validate_universal_rubric; dropped unused `from typing import Annotated`.
- Modified: `plugins/grading/python/tests/test_schema.py` — appended 3 tests.
- Created: `plugins/grading/python/tests/test_validators.py` — 6 tests for `validate_universal_rubric`.

## Symbols introduced

- **`UniversalRubric`** — the central artifact of spec §3.2(a). Tied to a `TypeName`, status from a 3-value enum (`frozen`, `warning_test_marginal`, `failed_to_converge`), and a list of `AxisDef` weighted axes.
- **`AxisDef`** — `{name, description, weight, score_levels}`. Each axis has explicit `full/partial/none` `ScoreLevels`, each with a `value` and a textual `criterion`.
- **`validate_universal_rubric(raw)`** — applies §3.6 first bullet's three invariants:
  1. Axis names unique within a rubric.
  2. Axis weights sum to 1.0 within `WEIGHT_EPSILON`.
  3. `score_levels` strictly monotone (full > partial > none).
  Pydantic catches schema-shape errors first; this function adds semantic checks on top.

## Tests

14 passing (8 schema + 6 validators): round-trip, status enum, level-constant, accept-good, reject-negative-weight, reject-non-summing weights, reject-non-monotone levels, reject-zero `out_of`, reject-duplicate axes, plus Task 6's original 5.

## Reviewers

- Implementer (sonnet): DONE.
- Spec reviewer (haiku): ✅
- Code-quality reviewer (haiku): ✅ Approved with one Minor about unused `Annotated` — fixed inline in `1dd1f8f`.

## Notes

The `none` field name shadows Python's builtin `None`; pydantic handles it without aliasing. Tests confirm `.none.value` resolves correctly.

`Annotated`-import cleanup also propagated into the plan document so future re-execution stays clean.
