---
name: Grading Pipeline Grading Pipeline Integration
overview: Build the complete grading pipeline for grading_pipeline by integrating the incremental indexing system with the grading logic, creating a production-ready autograder that uses PDF sources and dual-index retrieval.
todos:
  - id: pipeline-core
    content: Create grading_pipeline/pipeline.py with setup_grading_environment() and _grade_student_core() functions that integrate grading_pipeline indexes with DualIndexRetriever
    status: pending
  - id: pipeline-execution-modes
    content: Implement run_sequential_mode(), run_batched_mode(), and run_async_mode() in grading_pipeline/pipeline.py
    status: pending
  - id: pipeline-tests
    content: Create grading_pipeline/test_pipeline.py with comprehensive tests for index loading, evidence retrieval, and end-to-end grading
    status: pending
  - id: cli-interface
    content: Create grading_pipeline/cli.py with commands for building indexes and grading submissions (or extend existing CLI)
    status: pending
  - id: documentation
    content: Update grading_pipeline/README.md and create EXAMPLES.md with usage examples and workflows
    status: pending
  - id: integration-tests
    content: Create end-to-end integration tests that verify the complete workflow from indexing to grading
    status: pending
---

# Version 2 Grading Pipeline Integration Plan

## Current State

### ✅ Completed Components

- **grading_pipeline/index_builder.py**: Incremental indexing with PDF support, dual indexes (word + sentence)
- **grading_pipeline/manifest.py**: Source tracking and change detection
- **grading_pipeline/test_incremental_indexing.py**: Comprehensive indexing tests
- **retrieval_core/retriever.py**: `DualIndexRetriever` with cross-encoder reranking
- **retrieval_core/pipeline.py**: Full grading pipeline (but uses different index setup)
- **grader/grade_question.py**: Core grading logic
- **grader/lmql_grading.py**: LMQL feedback generation

### 🔄 Integration Gap

Grading Pipeline has the indexing infrastructure but lacks a grading pipeline that uses it. The retrieval_core pipeline exists but needs adaptation to work with grading_pipeline's incremental indexing system.

## Implementation Plan

### Phase 1: Core Grading Pipeline (`grading_pipeline/pipeline.py`)

Create a new grading pipeline that integrates grading_pipeline's incremental indexing with the grading logic:

**Key Functions:**

- `setup_grading_environment()`: 
  - Load or build dual indexes using `build_or_update_dual_indexes()`
  - Create `DualIndexRetriever` from the indexes
  - Load rubric and student data
  - Return retriever, rubric, students, and timing dict

- `_grade_student_core()`:
  - Reuse logic from `retrieval_core/pipeline.py` but adapt to grading_pipeline's index loading
  - Use `DualIndexRetriever.retrieve_for_criterion()` for evidence retrieval
  - Apply rubric scoring
  - Generate LMQL feedback
  - Return formatted results with timing

- `grade_student_sync()` / `grade_student_async()`:
  - Wrapper functions for synchronous and asynchronous grading
  - Reuse from retrieval_core with grading_pipeline index setup

- `run_sequential_mode()` / `run_batched_mode()` / `run_async_mode()`:
  - Execution modes for different performance requirements
  - Reuse patterns from retrieval_core

**Key Integration Points:**

- Import `build_or_update_dual_indexes` from `grading_pipeline.index_builder`
- Import `DualIndexRetriever` from `retrieval_core.retriever` (reuse as-is)
- Import grading functions from `grader.grade_question` and `grader.lmql_grading`
- Use `grading_pipeline/config/sources.yaml` for evidence sources
- Use `grading_pipeline/tmp/chroma_db` for persistent indexes

### Phase 2: Testing (`grading_pipeline/test_pipeline.py`)

Create comprehensive tests for the grading pipeline:

**Test Cases:**

1. **Test index loading**: Verify indexes load correctly from persistent storage
2. **Test evidence retrieval**: Verify `DualIndexRetriever` works with grading_pipeline indexes
3. **Test single student grading**: End-to-end grading for one student
4. **Test batch grading**: Multiple students in sequential mode
5. **Test async grading**: Multiple students in async mode
6. **Test with real PDF sources**: Use actual PDF files from `grading_pipeline/sources/`
7. **Test incremental updates**: Verify grading works after adding new sources

**Test Data:**

- Create sample rubric YAML file
- Create sample student answers
- Use existing PDF in `grading_pipeline/sources/`

### Phase 3: CLI Interface (`grading_pipeline/cli.py` or extend existing CLI)

Create command-line interface for running the autograder:

**Commands:**

- `build-index`: Build or update indexes from sources.yaml
- `grade-single`: Grade a single student submission
- `grade-batch`: Grade multiple submissions
- `grade-dir`: Grade all submissions in a directory

**Arguments:**

- `--sources-config`: Path to sources.yaml (default: grading_pipeline/config/sources.yaml)
- `--index-dir`: Path to ChromaDB directory (default: grading_pipeline/tmp/chroma_db)
- `--rubric`: Path to rubric YAML file
- `--submission`: Path to student submission file
- `--submissions-dir`: Directory containing student submissions
- `--mode`: Execution mode (sequential, batched, async)
- `--output`: Output file for results (JSON or YAML)

### Phase 4: Documentation and Examples

**Files to Create/Update:**

- `grading_pipeline/README.md`: Update with pipeline usage examples
- `grading_pipeline/EXAMPLES.md`: Usage examples and sample workflows
- `grading_pipeline/USAGE.md`: Detailed usage guide

**Documentation Sections:**

- Quick start guide
- Index building workflow
- Grading workflow
- Configuration options
- Performance considerations
- Troubleshooting

### Phase 5: Integration Testing

End-to-end integration tests:

1. **Full workflow test**:

   - Build indexes from PDF sources
   - Grade multiple students
   - Verify results format
   - Check timing performance

2. **Incremental workflow test**:

   - Build initial indexes
   - Add new PDF source
   - Verify incremental update works
   - Grade students with updated indexes

3. **Performance benchmarks**:

   - Compare indexing times (fresh vs incremental)
   - Compare grading times (sequential vs async)
   - Document performance characteristics

## File Structure

```
grading_pipeline/
├── pipeline.py              # NEW: Grading pipeline
├── test_pipeline.py         # NEW: Pipeline tests
├── cli.py                   # NEW: Command-line interface (optional)
├── index_builder.py         # EXISTS: Incremental indexing
├── manifest.py              # EXISTS: Source tracking
├── test_incremental_indexing.py  # EXISTS: Indexing tests
├── README.md                # UPDATE: Add pipeline docs
├── EXAMPLES.md              # NEW: Usage examples
└── config/
    └── sources.yaml         # EXISTS: Source configuration
```

## Dependencies

All dependencies already exist:

- `retrieval_core.retriever.DualIndexRetriever` - Reuse as-is
- `grader.grade_question.apply_rubric_scoring` - Reuse as-is
- `grader.lmql_grading.LMQLGrader` - Reuse as-is
- `grading_pipeline.index_builder.build_or_update_dual_indexes` - Already implemented

## Key Design Decisions

1. **Reuse retrieval_core components**: Don't duplicate `DualIndexRetriever` or grading logic
2. **Lazy embedding loading**: Leverage grading_pipeline's lazy loading for faster startup
3. **Persistent indexes**: Use grading_pipeline's incremental indexing for production efficiency
4. **Multiple execution modes**: Support sequential, batched, and async modes like retrieval_core
5. **Clear separation**: Keep indexing logic separate from grading logic

## Success Criteria

- ✅ Can build indexes from PDF sources using incremental indexing
- ✅ Can grade single student submission end-to-end
- ✅ Can grade batch of students in multiple execution modes
- ✅ Tests pass for all pipeline components
- ✅ CLI interface works for common workflows
- ✅ Documentation is complete and clear
- ✅ Performance is acceptable (indexing <2s when unchanged, grading <5s per student)

## Next Steps After This Plan

1. **Production hardening**: Error handling, logging, validation
2. **Performance optimization**: Caching, parallel processing
3. **Advanced features**: Custom reranking, multi-question support
4. **Deployment**: Docker container, cloud deployment options