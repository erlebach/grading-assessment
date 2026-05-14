# Task 20 — SKILL.md stubs (8 skills)

**Plan:** §Task 20 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `f201815` | `feat(grading-plugin): SKILL.md stubs for all 8 preprocessing skills` |

## Files

- Created (skills, 8 dirs): `plugins/grading/skills/<slug>/SKILL.md` for `translate-sources`, `prepare-seed-questions`, `review-seeds`, `calibrate-types`, `test-universal`, `generate-rubric`, `gold-grade`, `run-course`.
- Created (test): `plugins/grading/python/tests/test_skill_stubs.py`.

## Symbols / Structure

Each SKILL.md is a stub with the shape:

```
---
name: <slug>
description: …
---

# <slug> (Stage N)

**Status: stub.** Full orchestration deferred to the per-stage plan for Stage N.

## Spec reference
## Inputs read
## Outputs written
## Algorithm summary (implementation deferred)
## Failure modes
```

The test module pins the contract that future per-stage plans must keep: the directory set, presence of `SKILL.md`, frontmatter `name:` matching the slug, non-empty `description:`, and the literal `Status: stub` marker in the body. `EXPECTED_SKILLS` is hard-coded — adding a 9th skill is therefore a deliberate two-line change here.

## Tests

5 passing:
- `test_all_skill_dirs_present` — set equality against `EXPECTED_SKILLS`.
- `test_every_skill_has_SKILL_md` — file existence per slug.
- `test_frontmatter_name_matches_dir` — `name:` ↔ slug.
- `test_frontmatter_has_description` — non-empty `description:`.
- `test_body_marks_stub_status` — `"Status: stub"` substring in body.

Full plugin suite: 97 passing.

## Reviewers

- Implementer (haiku): DONE.
- Spec-compliance reviewer (haiku): ✅ — 9 files added, all SKILL.md bodies match plan verbatim, frontmatter slugs match dirs, `Status: stub` present in each, co-author trailer present.
- Code-quality reviewer (haiku): ✅ Approved — `_frontmatter` regex uses `re.DOTALL` and `split(":", 1)` (handles colons in descriptions), `parents[2]` correctly resolves to `plugins/grading/`, template uniformity across all 8 stubs.

## Notes

These are intentionally lean stubs: they pin what each stage **reads** and **writes**, name the relevant subagent roles, and defer the procedural detail to per-stage plans. A future task could lift `EXPECTED_SKILLS` into a config file if the set grows, but for 8 well-known slugs the hard-coded set is faster to reason about and review.
