# Minimum Working Examples (MWEs)

This directory contains standalone demonstrations of the autograder system's key components. Each MWE is self-contained, testable, and builds incrementally toward the full grading pipeline.

## Prerequisites

### Environment Setup

Create a `$HOME/.env` file with the following variables:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # Optional
LMQL_BACKEND=openai  # or "anthropic"
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

### Dependencies

Install dependencies using uv:

```bash
cd autograder
uv sync
```

## MWE 1: Basic LlamaIndex RAG Setup

**Purpose**: Validate LlamaIndex integration and basic retrieval

**Key Components**:
- LLM provider configuration
- In-memory vector store
- Document ingestion and chunking
- Similarity search

**Run**:
```bash
python -m mwe.mwe1_rag_basic
```

**What it demonstrates**:
- Loading configuration from environment variables
- Creating a vector index from text documents
- Performing semantic similarity search
- Retrieving relevant evidence chunks with scores

**Files**:
- `mwe1_rag_basic.py` - Demonstration script
- `../config/llm_config.py` - Provider abstraction
- `../evidence/llamaindex_setup.py` - LlamaIndex initialization
- `../tests/test_mwe1.py` - Unit tests

## MWE 2: Evidence Retrieval with Citations

**Purpose**: Integrate evidence retrieval with citation generation

**Key Components**:
- Index building with source metadata
- Citation-ready evidence retrieval
- Rubric-specific evidence filtering
- Formatted citations

**Run**:
```bash
python -m mwe.mwe2_evidence_citations
```

**What it demonstrates**:
- Building index with citation metadata (source IDs, page numbers)
- Retrieving evidence for specific rubric criteria
- Generating properly formatted citations
- Integration with the grading workflow

**Files**:
- `mwe2_evidence_citations.py` - Demonstration script
- `../evidence/index_builder.py` - Enhanced index building
- `../evidence/retriever.py` - Evidence retrieval interface
- `../grader/evidence_retriever.py` - Grading-specific retrieval
- `../tests/test_mwe2.py` - Integration tests

## MWE 3: LMQL Integration for Structured Grading

**Purpose**: Demonstrate LMQL-constrained feedback with citation enforcement

**Key Components**:
- LMQL program with citation constraints
- Structured output schema
- Citation completeness validation
- Retry logic for failed validation

**Run**:
```bash
python -m mwe.mwe3_lmql_grading
```

**What it demonstrates**:
- Generating feedback with LMQL constraints
- Enforcing citation completeness (every sentence must cite evidence)
- Validating that all citations reference known evidence IDs
- Structured output with sentences and citations

**Files**:
- `mwe3_lmql_grading.py` - Demonstration script
- `../prompts/grading_lmql.py` - LMQL program definition
- `../grader/lmql_grading.py` - LMQL grading interface
- `../tests/test_mwe3.py` - Constraint validation tests

## MWE 4: Full Pipeline Integration

**Purpose**: Complete end-to-end grading pipeline

**Key Components**:
- Rubric loading and parsing
- Evidence index building and loading
- Rubric-driven deterministic scoring
- LMQL-constrained feedback generation
- Complete grading record

**Run**:
```bash
python -m mwe.mwe4_full_pipeline
```

**What it demonstrates**:
- Full grading workflow from start to finish
- Integration of all previous MWE components
- Deterministic scoring before feedback generation
- Citation-enforced explanations
- Complete grading record matching schema

**Files**:
- `mwe4_full_pipeline.py` - Demonstration script
- `../grader/grade_question.py` - Complete implementation (TODOs replaced)
- `../evidence/build_index.py` - Complete implementation (TODOs replaced)
- `../tests/test_mwe4.py` - Full integration tests

## Architecture Principles

All MWEs follow these core principles:

1. **Rubric-first**: Rubrics define grading law, not LLMs
2. **Evidence-constrained**: All evidence comes from admissible sources
3. **Grades before feedback**: Scores assigned deterministically first
4. **Citation-enforced**: Every explanation sentence must cite evidence
5. **Bounded variance**: Deterministic outcomes with auditability

## Testing

Each MWE has corresponding tests in `../tests/`:

```bash
# Test individual MWE
pytest tests/test_mwe1.py -v
pytest tests/test_mwe2.py -v
pytest tests/test_mwe3.py -v
pytest tests/test_mwe4.py -v

# Test all MWEs
pytest tests/test_mwe*.py -v
```

## Implementation Order

The MWEs should be explored in order:

1. **MWE 1** - Establishes basic RAG functionality
2. **MWE 2** - Adds citation metadata and rubric integration
3. **MWE 3** - Adds LMQL constraints for citation enforcement
4. **MWE 4** - Integrates everything into the full pipeline

## Next Steps

After completing all MWEs:

1. **Production Index Building**: Replace in-memory vector store with Qdrant or Chroma
2. **Enhanced Scoring**: Implement more sophisticated rubric application logic
3. **Batch Processing**: Add parallel processing for multiple submissions
4. **Evaluation**: Test on real student submissions and rubrics
5. **Monitoring**: Add logging and metrics for production deployment

## Troubleshooting

### "OpenAI API key not found"
- Ensure `$HOME/.env` exists and contains `OPENAI_API_KEY`
- Check that the key is valid and has sufficient credits

### "Failed to parse LMQL response"
- The LLM may not have returned valid JSON
- Try increasing `max_retries` in the LMQL grader
- Check that the prompt is clear and well-formatted

### "No evidence retrieved"
- Check that the evidence index was built successfully
- Verify that document metadata includes source IDs
- Try lowering the similarity threshold

### Import errors
- Ensure all dependencies are installed: `uv sync`
- Run from the autograder root directory
- Use `python -m mwe.mweX_...` format for running scripts

## Additional Resources

- [Architecture Design](../docs/DESIGN.md)
- [ADR: RAG is Authoritative](../docs/adr/0001-rag-is-authoritative.md)
- [Original MWE Plan](../docs/MWE_PLAN.md)
- [Main README](../README.md)
