# Task 23 — Update CLAUDE.md test pipeline

**Plan:** §Task 23 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `e96beef` | `docs: extend Test Pipeline to include grading-plugin foundation tests` |

## Files

- Modified: `autograder/CLAUDE.md` (committed in `autograder/.git`).
- Modified: `/Users/erlebach/src/2026/grading_assessment/CLAUDE.md` (parent-repo file — left **untracked** locally; see note below).

## Edit

Inserted, immediately after the existing `**Run the full new-pipeline test suite:**` fenced block:

```
**Run the grading-plugin foundation test suite:**

```bash
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
```

Both suites must be green before any commit that touches `grading_pipeline/`, `grading_dynamic_rubrics/`, or `plugins/grading/`.
```

## Tests

Sanity-run of the plugin suite: 103 passing.

## Reviewers

Done inline by the controller (small docs edit; no implementer subagent dispatched). No reviewer dispatched — change is trivial and verifiable by reading the diff.

## Notes — parent-repo file

The plan asks for the same insertion in `/Users/erlebach/src/2026/grading_assessment/CLAUDE.md` (the parent repo's root). On inspection:
- The parent repo's working tree shows this file as **untracked** (`?? CLAUDE.md` in `git -C … status`), so my edit just modified a never-tracked file. No parent-repo commit is needed (and one is not possible without first `git add`-ing it, which is outside the autograder scope).
- The parent repo already had many unrelated in-flight changes (pyproject.toml, STATE.md, __pycache__, etc.) that would have polluted any cross-repo commit.
- User confirmed (via AskUserQuestion) the intended action was: edit both files, commit only the autograder repo. The parent-repo file edit sits in the working tree for the user to commit (or `git add` for the first time) themselves.

The same physical edit therefore lives at both paths, which keeps the documentation consistent for any developer inspecting either file.
