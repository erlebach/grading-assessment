# MWE Implementation Plan: LlamaIndex + LMQL Integration

## Overview

This document outlines the staged MWE (Minimum Working Example) approach for integrating LlamaIndex (RAG) and LMQL into the autograder system. Each MWE is self-contained and testable, reducing error likelihood through incremental development.

## Vector Database Strategy

### Phase 1: In-Memory (MWE Development)
- Use LlamaIndex's `SimpleVectorStore` for all MWEs
- Sufficient for development and testing with 96GB RAM available
- No external dependencies required
- Fast iteration and testing

### Phase 2: Production Options
- **Qdrant**: Persistent vector database, good for production
- **Chroma**: Lightweight, easy to set up, good for medium-scale deployments
- Configuration-driven switching via `evidence/index_config.yaml`
- Abstracted through LlamaIndex's vector store interface

### Configuration
```yaml
# evidence/index_config.yaml
index_config:
  vector_store:
    type: "in_memory"  # or "qdrant", "chroma"
    # Qdrant options
    qdrant:
      url: "http://localhost:6333"
      collection_name: "evidence_index"
    # Chroma options
    chroma:
      persist_directory: "./evidence/chroma_db"
```

## LLM Provider Configuration

### Supported Providers
1. **OpenAI** (default)
   - Models: GPT-4, GPT-3.5-turbo
   - Embeddings: text-embedding-3-small, text-embedding-3-large
2. **Anthropic**
   - Models: Claude 3 Opus, Sonnet, Haiku
   - Embeddings: Via OpenAI (Anthropic doesn't provide embeddings API)
3. **Local** (future)
   - Ollama, LM Studio
   - Local embedding models

### Environment Configuration
API keys loaded from `$HOME/.env`:
```bash
# $HOME/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LMQL_BACKEND=openai  # or "anthropic"
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

## MWE Structure

### MWE 1: Basic LlamaIndex RAG Setup
**Purpose**: Validate LlamaIndex integration and basic retrieval

**Components**:
- LLM configuration loading
- In-memory vector index creation
- Document ingestion and chunking
- Basic similarity search

**Output**: Retrieved evidence chunks with similarity scores

**Files**:
- `config/llm_config.py` - Provider abstraction
- `evidence/llamaindex_setup.py` - LlamaIndex initialization
- `mwe/mwe1_rag_basic.py` - Standalone demonstration
- `tests/test_mwe1.py` - Unit tests

### MWE 2: Evidence Retrieval with Citations
**Purpose**: Integrate evidence retrieval with citation generation

**Components**:
- Load evidence sources from config
- Build index with source metadata (file paths, line numbers)
- Retrieve evidence for specific rubric criteria
- Generate formatted citations

**Output**: Evidence chunks with properly formatted citations

**Files**:
- `evidence/index_builder.py` - Enhanced index building
- `evidence/retriever.py` - Evidence retrieval interface
- `grader/evidence_retriever.py` - Grading-specific retrieval
- `mwe/mwe2_evidence_citations.py` - Standalone demonstration
- `tests/test_mwe2.py` - Integration tests

### MWE 3: LMQL Integration for Structured Grading
**Purpose**: Demonstrate LMQL-constrained feedback with citation enforcement

**Components**:
- LMQL program with citation constraints
- Structured output schema (scores, feedback, citations)
- Integration with evidence from MWE 2
- Validation of citation completeness

**Output**: Structured grading result with enforced citations

**Files**:
- `prompts/grading_lmql.py` - LMQL program definition
- `grader/lmql_grading.py` - LMQL grading interface
- `mwe/mwe3_lmql_grading.py` - Standalone demonstration
- `tests/test_mwe3.py` - Constraint validation tests

### MWE 4: Full Pipeline Integration
**Purpose**: Complete end-to-end grading pipeline

**Components**:
- Full rubric loading and parsing
- Evidence retrieval for all criteria
- LMQL-based structured grading
- Citation-linked feedback generation
- Result aggregation

**Output**: Complete grading record matching existing schema

**Files**:
- `grader/grade_question.py` - Full implementation (replaces TODO)
- `evidence/build_index.py` - LlamaIndex-based index building
- `mwe/mwe4_full_pipeline.py` - End-to-end demonstration
- `tests/test_mwe4.py` - Full integration tests

## Dependencies

### Required Packages
```toml
dependencies = [
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "llama-index-core>=0.10.0",
    "llama-index-embeddings-openai>=0.1.0",
    "llama-index-llms-openai>=0.1.0",
    "llama-index-llms-anthropic>=0.1.0",
    "lmql>=0.7.0",
]

[project.optional-dependencies]
vector_stores = [
    "llama-index-vector-stores-qdrant>=0.1.0",
    "chromadb>=0.4.0",
]
```

## Implementation Order

1. **Setup Phase**
   - Create `config/llm_config.py` with provider abstraction
   - Update `pyproject.toml` with dependencies
   - Create `mwe/` directory structure

2. **MWE 1: Basic RAG**
   - Implement LlamaIndex setup
   - Create in-memory vector store
   - Test basic retrieval

3. **MWE 2: Evidence + Citations**
   - Enhance index building with metadata
   - Integrate citation generation
   - Test evidence retrieval for rubric criteria

4. **MWE 3: LMQL Grading**
   - Create LMQL program
   - Implement citation enforcement
   - Test structured output generation

5. **MWE 4: Full Integration**
   - Replace TODOs in existing code
   - Integrate all components
   - End-to-end testing

## Testing Strategy

Each MWE includes:
- **Unit tests**: Individual component validation
- **Integration tests**: Component interaction validation
- **Example data**: Sample rubrics, submissions, evidence
- **Documentation**: Clear explanation of what it demonstrates

## Success Criteria

- ✅ Each MWE runs independently
- ✅ All tests pass for each MWE
- ✅ LLM provider switching works without code changes
- ✅ Vector store can switch between in-memory, Qdrant, Chroma
- ✅ Evidence retrieval produces citable chunks
- ✅ LMQL enforces citation completeness
- ✅ Full pipeline maintains rubric-first philosophy
- ✅ No breaking changes to existing APIs

## Future Enhancements

- Qdrant/Chroma integration for production
- Local embedding models (sentence-transformers)
- Reranking for improved evidence quality
- Batch processing optimizations
- Hybrid search (vector + BM25)
