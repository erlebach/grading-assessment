# Design Rationale

This system separates **evaluation**, **decision**, and **explanation**.

- Rubrics define what is evaluated.
- Evidence constrains what may be used.
- Grades are assigned before prose exists.
- Feedback is a pure explanation of assigned grades.

LLMs are used as constrained assistants:
- to match answers to evidence,
- to structure feedback text,
- never to decide grading policy.

This design ensures bounded variance, auditability, and appeal resolution.

## Key Design Decisions

- Rubric-first scoring ensures bounded variance.
- Evidence anchoring enables appeal resolution.
- LMQL (when used) enforces citation completeness at generation time.
- CLI-based batch execution ensures reproducibility.

## Rejected Alternatives

- Free-form prompt-based grading.
- End-to-end LLM scoring without explicit rubrics.
- Regenerating grading policy from code or data.

See `docs/adr/0001-rag-is-authoritative.md` for detailed decision records.

The system follows a multi-dimensional grading model similar to those proposed in prior work (see `docs/REFERENCES.md`), but all grading semantics are explicitly encoded in rubrics.
