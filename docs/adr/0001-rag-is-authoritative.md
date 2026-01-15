# ADR 0001: RAG is Authoritative for Evidence Retrieval

## Status

Accepted

## Context

When grading student submissions, we need to retrieve relevant evidence to support grading decisions. This evidence could come from:
- Course materials
- Documentation
- Reference implementations
- Previous examples

We need a reliable, scalable way to retrieve this evidence.

## Decision

We will use RAG (Retrieval-Augmented Generation) as the authoritative method for evidence retrieval in the autograder system.

## Consequences

### Positive
- **Scalable**: Can handle large evidence corpora
- **Semantic search**: Finds relevant evidence even with different wording
- **Configurable**: Supports multiple index types and embedding models
- **Traceable**: Citations can be generated for all retrieved evidence

### Negative
- **Setup required**: Index must be built before use
- **Dependency**: Requires embedding models (API or local)
- **Latency**: Retrieval adds some processing time

### Mitigations
- Provide clear documentation for index building
- Support both API and local embedding models
- Cache index to reduce rebuild time
- Make evidence retrieval optional per rubric criterion

## Alternatives Considered

1. **Keyword search**: Too brittle, misses semantic matches
2. **Manual evidence**: Not scalable, difficult to maintain
3. **Rule-based matching**: Inflexible, doesn't handle variations

## Implementation Notes

- Evidence index configuration in `evidence/index_config.yaml`
- Index building script in `evidence/build_index.py`
- Citations generated via `grader/cite.py`
- Evidence retrieval integrated into `grader/grade_question.py`
