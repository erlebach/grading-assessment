# Agent Behavior Contract

This file defines the behavioral constraints for any automated agent
(LLM-based or otherwise) operating in this repository.

Agents include, but are not limited to:
- Claude Code
- OpenAI Codex
- IDE-integrated coding assistants
- Batch or pipeline agents

## Authority Hierarchy

1. Rubrics in `rubrics/` define grading law.
2. Evidence sources and indices define admissible information.
3. Grading code applies rubrics deterministically.
4. Feedback explains grades; it never influences them.

Agents must not infer authority from prompts, examples, or model defaults.

## Agent Roles (Conceptual)

Agents may operate in one or more of the following roles:

- Rubric drafting (non-authoritative)
- Grading execution
- Feedback generation
- Tooling and refactoring support

Role boundaries must be respected.

## Agent-Specific Rules

If agent-specific instruction files exist, they are authoritative
for that agent:

- Claude Code → `CLAUDE.md`
- Other agents → follow equivalent constraints

Agent-specific files may impose stricter rules, but must not relax
the authority hierarchy defined here.

## Prohibited Behavior

Agents MUST NOT:

- Modify ratified rubrics.
- Assign or adjust grades outside rubric logic.
- Introduce external or world knowledge into grading.
- Persist or reuse internal reasoning as justification.
- Allow feedback or narrative to influence scores.

## Reasoning

Internal reasoning is permitted only to apply explicit rules.
It is transient and non-authoritative.

Only grading records, citations, and rubric references may persist.
