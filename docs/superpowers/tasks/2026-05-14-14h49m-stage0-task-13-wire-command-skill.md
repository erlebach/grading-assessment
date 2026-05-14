# Stage 0 Task 13 — wire `/grade:translate` command + rewrite `translate-sources` skill

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 13 — **Status:** Complete — **Date:** 2026-05-14 14:49

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `40e0985` | `feat(grading-plugin): wire /grade:translate command + real translate-sources skill` |
| `cff8e25` | `docs(grading-plugin): correct Stage 0 skill/command doc inaccuracies` (review fix) |

## Files

- Modified: `plugins/grading/skills/translate-sources/SKILL.md` — stub → real skill (marker_single procedure, inputs/outputs, failure modes).
- Modified: `plugins/grading/commands/translate.md` — stub → real command (args `<source_path>`/`--name`/`--run`/`--force`, prerequisites).
- Modified: `plugins/grading/python/tests/test_skill_stubs.py` — `test_body_marks_stub_status` now iterates `EXPECTED_SKILLS - {"translate-sources"}` (the skill is no longer a stub).

## What

- `/grade:translate` command and the `translate-sources` skill are now wired to the real `translate_sources.py` CLI built in Tasks 7-12.
- The skill-stub test no longer expects `translate-sources` to carry "Status: stub"; `test_frontmatter_name_matches_dir` / `test_frontmatter_has_description` still cover its frontmatter.

## Tests

- `test_command_stubs.py` + `test_skill_stubs.py`: 8 passing. Full plugin suite: 139 passing.

## Reviewers

- Spec compliance: ✅ — all three files match the plan's Task 13 contents; only those files changed.
- Code quality: **Changes needed (minor)** → fix `cff8e25` → resolved.
  - Fixed doc inaccuracies (carried from the plan text): SKILL.md wrongly claimed the run folder is "left untouched" on `marker_single` failure (an empty `sources/<name>/` dir is in fact created first); `--name` is an unconditional override (dropped "on collision"); `--run` is a plain prefix match (dropped "git-style"); `sources_raw/` softened to a convention, not enforced.

## Notes

- Step ordering matters: the test exclusion (Step 1) was committed-in before the SKILL.md rewrite, so the suite stayed green throughout.
