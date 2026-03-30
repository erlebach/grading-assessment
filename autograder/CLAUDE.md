# Claude Code Rules (Project-Local)

## Git Commands

The `.git` directory lives one level above the working directory, at
`/Users/erlebach/src/2026/grading_assessment/`. Running `git` from inside
`autograder/` will fail with path-spec or index-lock errors.

**Always run git commands with an explicit `-C` flag:**

```bash
git -C /Users/erlebach/src/2026/grading_assessment <subcommand> [args]
```

Examples:
- `git -C /Users/erlebach/src/2026/grading_assessment status --short`
- `git -C /Users/erlebach/src/2026/grading_assessment add autograder/grading_pipeline/models.py`
- `git -C /Users/erlebach/src/2026/grading_assessment commit -m "..."`

File paths passed to `git add` must be relative to the repo root, i.e.
prefixed with `autograder/` (e.g. `autograder/grading_pipeline/models.py`).

---

## Session_id

session_id: autograder_2026-01-25

This file defines non-negotiable constraints for Claude Code operating within this repository.

## Authority Hierarchy

1. Rubrics in `rubrics/` are authoritative.
2. Evidence indices and extracted artifacts are authoritative.
3. Grading code applies rubrics deterministically.
4. Feedback explains grades; it never influences them.

## Prohibited Actions

You MUST NOT:

- Change rubric semantics or point allocations.
- Infer grading criteria from student answers.
- Use knowledge outside admissible evidence.
- Generate or modify ratified rubrics.
- Allow feedback or prose to affect scores.
- Persist or reuse internal reasoning as justification.
- Modify `~/.env` or any environment configuration files - user will always do this manually.

## Allowed Actions

You MAY:

- Draft proposed rubrics into `rubrics/drafts/`.
- Refactor grading code without changing behavior.
- Improve feedback phrasing under citation constraints.
- Add validation checks and tests.

## Reasoning Rule

Internal reasoning may be used to **apply** the rubric.
It must be discarded after producing the grading record.

## Transparency and Escalation

- Where information is coming from
- When I'm taking shortcuts vs. using proper automation
- Asking you when I hit blockers instead of improvising workarounds
- Do not hardcode values, infer data, or create workarounds without explicit acknowledgment and user consent.
- Prefer YAML configuration files and commandline arguments

See `AGENT.md` for model-agnostic constraints.

## Use of grade-spec.md

- Always verify code changes against grade-spec.md. 
- If a code change requires a change in grading logic, 
- update grade-spec.md first before writing any code."

## Tasks

- Never overwrite TASK_LIST.md or TASKS.md. Always append new tasks or update existing ones using the Edit tool.
- If I request the creation of TASK_LIST.md or TASKS.md, please ask for confirmation. 
- As new tasks are created, update the TASK_LIST being worked on to reflect any additional work. 
