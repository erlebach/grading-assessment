# Task 6 — TypeName enum + TypeCatalog schema

**Plan:** §Task 6 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `5fbfb7a` | `feat(grading-plugin): TypeName enum and TypeCatalog schema` |

## Files

- Created: `plugins/grading/python/schema.py`
- Created: `plugins/grading/python/tests/test_schema.py`

## Symbols introduced

`schema.py` exports the foundation that Tasks 7–11 will append to:
- `WEIGHT_EPSILON = 1e-6` — used by every weight-sums-to-1.0 invariant.
- `TypeName(str, Enum)` — the 10 spec-fixed type names.
- `_Strict(BaseModel)` — base class with `extra="forbid"` + `frozen=True`. Convention: every grading-plugin schema model extends `_Strict`.
- `TypeCatalogEntry` — `{name, description, candidate_axes}` with axis-uniqueness and non-empty validation.
- `TypeCatalog` — wraps a list of entries; rejects duplicate type names.

## Tests

5 passing: enum size, exact enum value set, round-trip, rejects unknown type, rejects empty axes.

## Reviewers

- Implementer (haiku): DONE.
- Spec reviewer (haiku): ✅
- Code-quality reviewer (haiku): ✅ Approved with one Minor — `Annotated` is imported unused. Plan's claim that Tasks 7–11 use it turned out to be wrong (they don't). Left in for now since impact is nil; will revisit if a later task's reviewer flags it again.

## Notes

This is the first Python helper. The schema module grows in Tasks 7–11; the convention (`_Strict` base, `WEIGHT_EPSILON` for weight-sum tolerance, pydantic v2 `field_validator` `@classmethod`) is locked in here.
