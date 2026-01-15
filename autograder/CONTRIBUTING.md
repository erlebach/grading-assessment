# Contributing Guidelines

This project prioritizes grading defensibility over convenience.

## General Rules

- Grading behavior must trace directly to rubrics.
- All scores must be explainable via rubric language and evidence.
- Internal reasoning is not an output artifact.

## Rubrics

- Draft rubrics live in `rubrics/drafts/`.
- Only rubrics in `rubrics/` may be used for grading.
- Any rubric change creates a new version.

## Code

- Prefer explicit logic over heuristics.
- Do not merge grading and feedback generation.
- Add tests for any new grading rule or validator.
