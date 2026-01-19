⏺ Here are the new files created during the implementation:

  Core Infrastructure (5 files)

  1. grading_pipeline/config/index_schema.py (~60 lines)
    - Pydantic models for index configuration validation
    - IndexTypeConfig, RuntimeConfig, IndexesConfig classes
  2. grading_pipeline/index_registry.py (~350 lines)
    - IndexBuilder protocol and 3 concrete builders
    - CharacterIndexBuilder, SentenceIndexBuilder, ParagraphIndexBuilder
    - IndexRegistry for builder registration and lookup
  3. grading_pipeline/index_factory.py (~250 lines)
    - IndexFactory class for creating/loading indexes
    - Smart build-or-update logic with config change detection
    - Runtime subset selection support
  4. retrieval_core/multi_retriever.py (~200 lines)
    - MultiIndexRetriever for N-index retrieval
    - Deduplication and cross-encoder reranking
    - Runtime index_subset parameter support
  5. retrieval_core/dual_retriever_compat.py (~60 lines)
    - DualIndexRetriever backward-compatible wrapper
    - Extends MultiIndexRetriever with familiar API

  Testing (1 file)

  6. tests/test_multi_index_integration.py (~350 lines)
    - 19 comprehensive integration tests
    - Configuration validation, registry, factory, building, retrieval, compatibility tests
    - All tests passing ✓

  Documentation (1 file)

  7. MULTI_INDEX_IMPLEMENTATION.md (~350 lines)
    - Complete implementation guide
    - Architecture overview, usage examples, configuration schema
    - Migration path and future extensions

  Total: 7 new files, ~1,600 lines of code

  You can view all files with:
  ls -la grading_pipeline/{config/index_schema.py,index_registry.py,index_factory.py}
  ls -la retrieval_core/{multi_retriever.py,dual_retriever_compat.py}
  ls -la tests/test_multi_index_integration.py
  ls -la MULTI_INDEX_IMPLEMENTATION.md
