# Task 10 — SeedQuestion, Question, SourceMeta

**Plan:** §Task 10 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `11be348` | `feat(grading-plugin): SeedQuestion, Question, SourceMeta schemas` |

## Files

- Modified: `plugins/grading/python/schema.py` — appended `UserReview`, `SeedQuestion`, `Question`, `SourceFormat`, `ExtractionMeta`, `SourceMeta`.
- Modified: `plugins/grading/python/tests/test_schema.py` — appended 4 tests.

## Symbols introduced

These are leaf data classes — no semantic validators (spec §3.5 lists them as "mechanical").

- `UserReview` — `{approved, note?}`.
- `SeedQuestion` — `{seed_id, type, topic, source, text, generated_by, user_review}`.
- `Question` — `{question_id, course, type, text, sources, notes?}` with `sources` defaulting to `[]`.
- `SourceFormat` — enum `pdf` / `markdown`.
- `ExtractionMeta` — `{role, tier, ts}` for PDF translation provenance.
- `SourceMeta` — top-level `sources/<source>/meta.yaml` model; `extraction` is `None` for markdown inputs.

## Tests

12 passing in `test_schema.py` (8 prior + 4 new). Full plugin suite: 35 tests.

## Reviewers

- Implementer (haiku): DONE.
- Spec reviewer (haiku): ✅
- Code-quality reviewer (haiku): ✅ Approved (no issues).

## Notes

`content_sha: str = Field(min_length=8)` is deliberately not pinned to a specific hash length — the spec doesn't mandate one, and different source classes may produce different digest formats.
