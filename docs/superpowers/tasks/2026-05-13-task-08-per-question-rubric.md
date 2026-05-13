# Task 8 — PerQuestionRubric + validate_per_question_rubric

**Plan:** §Task 8 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `fe29590` | `feat(grading-plugin): PerQuestionRubric schema + validate_per_question_rubric` |

## Files

- Modified: `plugins/grading/python/schema.py` — appended `ConceptOverlayEntry`, `PerQuestionRubricStatus`, `PerQuestionRubric`, `validate_per_question_rubric`.
- Modified: `plugins/grading/python/tests/test_validators.py` — appended 6 PQR tests.

## Symbols introduced

- `ConceptOverlayEntry` — `{id, text, weight, relevant_axes}`. `relevant_axes` must be non-empty (Pydantic Field min_length=1).
- `PerQuestionRubricStatus` — enum: `frozen`, `degraded`. No `warning_test_marginal` here; degraded covers the Stage-3 exhaustion case.
- `PerQuestionRubric` — per-question overlay referencing a universal rubric by relative path.
- `validate_per_question_rubric(raw, *, universal: UniversalRubric)` — keyword-only `universal` arg makes the cross-rubric dependency obvious. Enforces:
  1. Type-name parity with the universal rubric.
  2. Unique concept ids.
  3. Concept weights sum to 1.0 ± WEIGHT_EPSILON.
  4. Every `relevant_axes` is a non-empty subset of the universal rubric's axis names.

## Tests

12 passing in `test_validators.py` (6 universal + 6 per-question). Full plugin suite at 26 tests.

## Reviewers

- Implementer (sonnet): DONE.
- Spec reviewer (haiku): ✅
- Code-quality reviewer (haiku): ✅. Minor observation: the `if not c.relevant_axes` guard inside the validator is defense-in-depth — pydantic's `min_length=1` already catches the empty case. Left as-is; the explicit semantic check makes the invariant readable in the function body.

## Notes

Keyword-only `*, universal` argument is the API convention for cross-artifact validators — `validate_grade` (Task 9) will use the same pattern.
