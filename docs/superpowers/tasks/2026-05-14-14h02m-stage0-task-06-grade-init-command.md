# Stage 0 Task 6 — `/grade:init` command file

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 6 — **Status:** Complete — **Date:** 2026-05-14 14:02

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `12f3bd1` | `feat(grading-plugin): /grade:init command` |

## Files

- Created: `plugins/grading/commands/init.md` (+29 — skill-less slash command)
- Modified: `plugins/grading/python/tests/test_command_stubs.py` (+1 — `"init": None` in `EXPECTED`)

## What

- `/grade:init` slash command — directly invokes `python -m plugins.grading.python.run_init [--profile <name>]` (no skill, like `status` / `diff`). Documents the run-folder artifacts and the `--profile` convention.
- Registered in `test_command_stubs.py`'s `EXPECTED` dict as a skill-less command.

## Tests

- `test_command_stubs.py`: 3 passing. Full plugin suite: 116 passing.

## Reviewers

- Spec compliance: ✅ — `init.md` matches the plan's Task 6 Step 3 verbatim; only `"init": None` added to `EXPECTED`; only the two files changed.
- Code quality: ✅ Approved — frontmatter well-formed, documented CLI accurate to `run_init.py`, artifacts list matches `init_run()`. Minor non-blocking notes: the test-only `--runs-dir` flag is undocumented (arguably correct — it is test-only); opening sentence phrasing diverges slightly from `status.md`/`diff.md`.

## Notes

- TDD: `test_all_command_files_present` failed (EXPECTED had `init`, no `init.md`) before the file was created.
