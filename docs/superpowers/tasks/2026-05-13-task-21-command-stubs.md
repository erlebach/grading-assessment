# Task 21 — Slash-command stubs (10 commands)

**Plan:** §Task 21 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `49591ad` | `feat(grading-plugin): slash-command stubs for /grading:* (10 commands)` |

## Files

- Created (commands, 10): `plugins/grading/commands/{translate,seeds,review-seeds,calibrate,test-universal,question,gold-grade,course,status,diff}.md`
- Created (test): `plugins/grading/python/tests/test_command_stubs.py`

## Command → backend mapping

| Command | Backing skill | Notes |
|---|---|---|
| translate | translate-sources | Stage 0 |
| seeds | prepare-seed-questions | Stage 1 |
| review-seeds | review-seeds | Stage 1 (interactive gate) |
| calibrate | calibrate-types | Stage 2 |
| test-universal | test-universal | Stage 2 ad-hoc check |
| question | generate-rubric | Stage 3 |
| gold-grade | gold-grade | Stage 4 |
| course | run-course | Orchestrator |
| status | — (calls `validate_run` python helper directly) | Inline `bash` block in body |
| diff | — (calls `diff_runs` python helper directly) | Inline `bash` block in body |

## Tests

3 passing:
- `test_all_command_files_present` — file-stem set equality against the EXPECTED map.
- `test_each_command_has_description` — frontmatter `description:` non-empty.
- `test_each_command_references_its_skill_or_helper` — body contains `grading:<skill>` for the 8 skill-backed commands; body contains `plugins/grading/python/` for the two helper-direct commands.

Full plugin suite: 100 passing.

## Reviewers

- Implementer (haiku): DONE.
- Spec-compliance reviewer (haiku): ✅ — 11 files in commit, every body verbatim per plan, mapping intact, frontmatter descriptions quoted, co-author trailer present.
- Code-quality reviewer (haiku): ✅ Approved — uniform stub structure, frontmatter parser handles quoted descriptions, EXPECTED map exhaustively tested, no unnecessary imports.

## Notes

The `status` and `diff` commands bypass the skill indirection because they correspond to deterministic, no-LLM python helpers (`validate_run.py` and `diff.py`) that are already implemented. Their bodies inline the exact bash invocation rather than gesturing at a future skill — that's the closure of "this command is already real" vs. "this command is a stub for a future stage". The test enforces the distinction via the `EXPECTED` map (a `None` value means "must reference `plugins/grading/python/` instead").
