# Claude Code Rules (Project-Local)

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

## Allowed Actions

You MAY:

- Draft proposed rubrics into `rubrics/drafts/`.
- Refactor grading code without changing behavior.
- Improve feedback phrasing under citation constraints.
- Add validation checks and tests.

## Reasoning Rule

Internal reasoning may be used to **apply** the rubric.  
It must be discarded after producing the grading record.

See `AGENT.md` for model-agnostic constraints.
