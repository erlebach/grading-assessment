### *Trace the function grade_question_command in @grading_dynamic_rubrics/cli.py . It calls `pipeline.grade_question_batch`, which calls _grade_student_core (which appears to be responsible for generating the grade and works with the rubric, and the RAG indexes and retrievers. Since scoring is yet accurate, I want to manually experiment with the indexes, retrievers, rerankers, etc in a deterministic manner. 
Supplement your analysis with a flowchart.*


## Function Call Trace

### Entry Point: `grade_question_command` (cli.py:26)
- Validates paths and loads rubric config
- Loads all submissions for the question
- Calls `grade_question_batch()` (line 104)

### Batch Processing: `grade_question_batch` (pipeline.py:377)
- Sets up logging and transparency
- Calls `setup_grading_environment()` (line 453-458) to initialize:
    - **Indexes**: Loads/builds in-memory vector indexes
    - **Retriever**: Creates `MultiIndexRetriever` instance
    - **Rubric**: Loads rubric YAML
    - **Retrieval params**: Loads from config (top_k_per_index, final_top_k, similarity_threshold)
- Loops through each submission (questions and answer_types) (line 466)
- For each submission, calls `_grade_student_core()` (line 484)

### Core Grading: `_grade_student_core` (pipeline.py:242)
This function has three main phases:

#### Phase 1: Evidence Retrieval (lines 271-298)
- For each criterion with `evidence_required=True`:
    - Calls `retriever.retrieve()` (line 286) with:
        - `query = student_answer` (only student answer, not criterion description)
            - (TODO: Investigate what context to use)
        - `top_k_per_index` from config
        - `final_top_k` from config
        - `similarity_threshold` from config
            - (TODO: should it be set to 0.5? or 0.25?)
        - `index_subset` (which indexes to query)
    - QUESTION: where is reranking executed?

#### Phase 2: Scoring (lines 300-309)

- QUESTION: How can scoring occur before reranking? 
- Calls `apply_rubric_scoring_dynamic()` (line 306)
- Two-dimensional scoring:
    - QUESTION: why 2-D?
    - **Keyword score**: Extracts keywords from criterion description, checks presence in answer
    - **Semantic score**: Based on number of evidence spans retrieved (not similarity scores)
    - **Combined**: `(keyword_weight × keyword_score + semantic_weight × semantic_score) × max_points`

#### Phase 3: Feedback Generation (lines 311-320)
- Creates `LMQLGrader()` instance
- Calls `lmql_grader.grade_with_feedback()` (line 314) with rubric, answer, evidence, and scores

## Retrieval Flow: `MultiIndexRetriever.retrieve()` (multi_retriever.py:83)

1. **Index Selection** (lines 112-123): Determines which indexes to query (from `index_subset` or all)
2. **Per-Index Retrieval** (lines 137-156):
    - For each active index:
        - Creates retriever: `index.as_retriever(similarity_top_k=top_k_per_index)`
        - Retrieves nodes: `retriever.retrieve(query)`
        - Extracts citations and filters by `similarity_threshold`
        - Adds `index_id` to each result
3. **Deduplication** (line 159): Calls `_union_and_deduplicate()` to remove exact duplicates (same source_id + same text)
4. **Reranking** (lines 161-166):
    - Calls `_rerank()` (line 164)
    - Uses CrossEncoder model to score query-text pairs
    - Sorts by `reranker_score` descending
    - Returns top `final_top_k` results

## Flowchart

```
┌─────────────────────────────────────────────────────────────┐
│ grade_question_command (cli.py:26)                          │
│ - Validate paths                                             │
│ - Load rubric config                                         │
│ - Load submissions                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ grade_question_batch (pipeline.py:377)                       │
│ - Setup logging/transparency                                 │
│ - Call setup_grading_environment()                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ setup_grading_environment (pipeline.py:171)                  │
│                                                              │
│ 1. Load/Build Indexes:                                       │
│    - load_multi_indexes_in_memory() or                       │
│    - build_multi_indexes_in_memory()                         │
│    - Returns: dict[str, VectorStoreIndex]                  │
│                                                              │
│ 2. Create Retriever:                                         │
│    - MultiIndexRetriever(indexes)                            │
│    - Initializes CrossEncoder reranker                       │
│                                                              │
│ 3. Load Rubric:                                              │
│    - load_rubric(rubric_path)                                │
│                                                              │
│ 4. Load Config:                                              │
│    - index_subset (which indexes to use)                     │
│    - retrieval_params (top_k_per_index, final_top_k, etc.)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Returns: (retriever, rubric, timing, 
                       │          index_subset, retrieval_params)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ FOR EACH SUBMISSION (pipeline.py:466)                        │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐ │
│   │ _grade_student_core (pipeline.py:242)                 │ │
│   │                                                        │ │
│   │ PHASE 1: Evidence Retrieval (lines 271-298)          │ │
│   │   FOR EACH CRITERION (evidence_required=True):       │ │
│   │     ┌──────────────────────────────────────────────┐ │ │
│   │     │ retriever.retrieve() (multi_retriever.py:83)│ │ │
│   │     │                                              │ │ │
│   │     │ 1. Determine active_indexes                  │ │ │
│   │     │ 2. FOR EACH INDEX:                            │ │ │
│   │     │    - index.as_retriever(top_k_per_index)      │ │ │
│   │     │    - retriever.retrieve(query=student_answer)│ │ │
│   │     │    - Extract citations                        │ │ │
│   │     │    - Filter by similarity_threshold           │ │ │
│   │     │                                              │ │ │
│   │     │ 3. _union_and_deduplicate()                  │ │ │
│   │     │    - Remove exact duplicates                  │ │ │
│   │     │    - (source_id, text) pairs                 │ │ │
│   │     │                                              │ │ │
│   │     │ 4. _rerank() (multi_retriever.py:204)        │ │ │
│   │     │    - CrossEncoder.predict(query, text)       │ │ │
│   │     │    - Sort by reranker_score                  │ │ │
│   │     │    - Return top final_top_k                  │ │ │
│   │     └──────────────────────────────────────────────┘ │ │
│   │     evidence_by_criterion[criterion_id] = evidence  │ │
│   │                                                        │ │
│   │ PHASE 2: Scoring (lines 300-309)                     │ │
│   │   ┌──────────────────────────────────────────────┐   │ │
│   │   │ apply_rubric_scoring_dynamic()               │   │ │
│   │   │                                              │   │ │
│   │   │ FOR EACH CRITERION:                          │   │ │
│   │   │   1. Keyword Scoring:                        │   │ │
│   │   │      - extract_keywords(description)          │   │ │
│   │   │      - Check presence in student_answer       │   │ │
│   │   │      - keyword_score = found/total            │   │ │
│   │   │                                              │   │ │
│   │   │   2. Semantic Scoring:                       │   │ │
│   │   │      - Count evidence spans                   │   │ │
│   │   │      - semantic_score = min(1.0,              │   │ │
│   │   │        len(evidence) / semantic_top_k)        │   │ │
│   │   │                                              │   │ │
│   │   │   3. Combined Score:                          │   │ │
│   │   │      combined = (keyword_weight × keyword +   │   │ │
│   │   │                   semantic_weight × semantic) │   │ │
│   │   │      final_score = int(combined × max_points)│   │ │
│   │   └──────────────────────────────────────────────┘   │ │
│   │                                                        │ │
│   │ PHASE 3: Feedback Generation (lines 311-320)           │ │
│   │   ┌──────────────────────────────────────────────┐   │ │
│   │   │ LMQLGrader.grade_with_feedback()              │   │ │
│   │   │                                              │   │ │
│   │   │ 1. Flatten evidence_by_criterion              │   │ │
│   │   │ 2. Remove duplicates by source_id              │   │ │
│   │   │ 3. generate_explanation()                     │   │ │
│   │   │    - LMQL-constrained feedback                │   │ │
│   │   │    - Citation enforcement                      │   │ │
│   │   │ 4. Build grading_result dict                   │   │ │
│   │   └──────────────────────────────────────────────┘   │ │
│   │                                                        │ │
│   │ 5. Format result (lines 324-373)                      │ │
│   │    - Build rubric_items                               │ │
│   │    - Include keyword/semantic scores                  │ │
│   │    - Return complete result dict                      │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                              │
│   Append result to results list                              │
│   Write incrementally to output_path (if provided)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ write_results() - Final output                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Components for Manual Experimentation

1. **Indexes**: `dict[str, VectorStoreIndex]` - Multiple vector indexes (word-level, sentence-level, etc.)
2. **MultiIndexRetriever**: Queries multiple indexes, deduplicates, reranks
3. **CrossEncoder Reranker**: `sentence_transformers.CrossEncoder` - Reranks candidates
4. **Retrieval Parameters** (from `sources.yaml`):
    - `top_k_per_index`: Results per index before reranking
    - `final_top_k`: Final results after reranking
    - `similarity_threshold`: Minimum similarity score to include
5. **Index Subset**: `runtime.active_indexes` in config - Which indexes to query
6. **Scoring Weights**: In rubric - `scoring_weights[criterion_id]` with `keyword` and `semantic` weights

## Deterministic Experimentation Points

1. **Index Selection**: Modify `index_subset` to test different index combinations
2. **Retrieval Parameters**: Adjust `top_k_per_index`, `final_top_k`, `similarity_threshold`
3. **Reranker Model**: Change `RERANKER_MODEL` environment variable
4. **Query Construction**: Currently uses only `student_answer`; could include criterion description
5. **Scoring Weights**: Adjust `keyword_weight` vs `semantic_weight` in rubric
6. **Deduplication Logic**: Modify `_union_and_deduplicate()` to change deduplication strategy

This trace shows the flow from CLI entry through index setup, retrieval, scoring, and feedback generation. The retrieval system uses multiple indexes, deduplication, and cross-encoder reranking before evidence reaches the scoring function.
