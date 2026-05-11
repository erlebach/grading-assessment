---

## 2026-05-11 12:47 — Move .git into autograder/ (make autograder the repo root)

Used `git filter-repo --subdirectory-filter autograder` to rewrite history so `autograder/`
becomes the repo root. Tracked paths no longer carry the `autograder/` prefix. Remote `origin`
re-added and upstream tracking restored for `v2-concept-rubrics`. `CLAUDE.md` Git Commands
section updated to drop the `-C` flag. Commit SHAs rewritten (history content preserved).
Parent `.git` (backup) remains at `../grading_assessment/.git` and can be removed.

### Details

Steps taken:
1. Restored parent `.git` from `/tmp/git_backup` (first filter-repo attempt promoted content the wrong way)
2. Copied backup `.git` into `autograder/`, removed empty `.git` created by session startup hook
3. Ran `git filter-repo --subdirectory-filter autograder --force` from `autograder/`
4. Re-added `origin` remote: `https://github.com/erlebach/grading-assessment.git`
5. `git fetch origin` + `git branch --set-upstream-to=origin/v2-concept-rubrics`
6. Updated `CLAUDE.md` Git Commands section

---

## 2026-01-21 - Honor dynamic rubrics retrieval settings from YAML

### Completed Tasks ✅
- [x] Made `grading_dynamic_rubrics` retrieval parameters come from `sources.yaml`

### Files Created/Modified
- `autograder/grading_dynamic_rubrics/pipeline.py` - Load `retrieval.*` from config and pass into `retriever.retrieve()`

### Key Changes
- `retrieval.similarity_threshold` (and `top_k_per_index` / `final_top_k`) in
  `grading_dynamic_rubrics/config/sources.yaml` now **override** code defaults, so
  transparency logs accurately reflect YAML-driven retrieval behavior.

### Notes
- This fixes the mismatch where transparency logs showed `SIMILARITY_THRESHOLD=0.0`
  despite the YAML being set to `-1.0`.

---

## 2026-01-21 - Add transparent retriever + reranker tracing

### Completed Tasks ✅
- [x] Added `--transparent` CLI flag to both grading CLIs
- [x] Implemented verbose traces for retriever inputs/outputs and reranker

### Files Created/Modified
- `autograder/grading_pipeline/cli.py` - Added `--transparent` and passed to pipeline
- `autograder/grading_pipeline/pipeline.py` - Plumbed `transparent` flag and enabled trace
- `autograder/grading_dynamic_rubrics/cli.py` - Added `--transparent` and passed to pipeline
- `autograder/grading_dynamic_rubrics/pipeline.py` - Plumbed `transparent` flag and added per-criterion trace label
- `autograder/retrieval_core/retriever.py` - Added detailed trace logging for dual retriever + reranker
- `autograder/retrieval_core/multi_retriever.py` - Added detailed trace logging for multi-index retriever + reranker

### Key Changes
- `--transparent` enables logs that show:
  - input query text (clearly delimited)
  - per-index top-\(k\) retrieved texts with `SIMILARITY_SCORE`
  - reranker inputs (query + candidates) and reranker outputs with scores
  - dotted divider lines between successive texts for readability

### Notes
- Traces are routed through the existing log writer used by `--log`, so stdout and
  optional log files see the same transparency stream.

---

## 2026-01-21 - Route transparent traces to file

### Completed Tasks ✅
- [x] Changed `--transparent` output to write to `autograder/logs/transparent.log`

### Files Created/Modified
- `autograder/grading_pipeline/pipeline.py` - Write transparent traces to file-only writer
- `autograder/grading_dynamic_rubrics/pipeline.py` - Write transparent traces to file-only writer

### Key Changes
- When `--transparent` is enabled, trace output no longer prints to stdout; it is
  written (line-buffered + flushed) to `autograder/logs/transparent.log`.

---

## 2026-01-21 - Reorganize logging arguments

### Completed Tasks ✅
- [x] Replaced `--log` (path) with `--log-path`, `--log-file`, and `--log` (boolean)
- [x] Made normal stdout messages always write to log file
- [x] Made transparency conditional on `--log` flag

### Files Created/Modified
- `autograder/grading_pipeline/cli.py` - New logging arguments with defaults
- `autograder/grading_pipeline/pipeline.py` - Always write to log file, conditional transparency
- `autograder/grading_dynamic_rubrics/cli.py` - New logging arguments with defaults
- `autograder/grading_dynamic_rubrics/pipeline.py` - Always write to log file, conditional transparency

### Key Changes
- **`--log-path`** (default: `logs`): Directory where log files are written
- **`--log-file`** (default: `grading.log`): Name of the main log file
- **`--log`** (default: `True`): Enable transparency logging (use `--no-log` to disable)
- Normal stdout messages (e.g., `[Grading] ...`) **always** go to the log file
- Transparency traces go to `transparency.log` in the log path **only if `--log` is True**

### Notes
- Log files are always created (normal messages always logged)
- Transparency is optional and controlled by `--log` / `--no-log` flag

---

## 2026-01-21 - Clear log directory at run start

### Completed Tasks ✅
- [x] Clear log directory before each run (files only)

### Files Created/Modified
- `autograder/grading_pipeline/pipeline.py` - Delete existing log files before opening new logs
- `autograder/grading_dynamic_rubrics/pipeline.py` - Delete existing log files before opening new logs

### Notes
- Only files are deleted; subdirectories (if any) are left untouched.

---

## 2026-01-21 - Make transparency logs explicit about indexes and k

### Completed Tasks ✅
- [x] Log `ACTIVE_INDEXES` and requested \(k\) values per retrieval call
- [x] Make per-index headers explicit even when `returned=0`

### Files Created/Modified
- `autograder/retrieval_core/multi_retriever.py` - Add `RETRIEVAL PARAMETERS` header and clearer index headers
- `autograder/retrieval_core/retriever.py` - Add `RETRIEVAL PARAMETERS` header and clearer index headers

---

## 2026-01-21 - Add index diagnostics for dynamic rubrics

### Completed Tasks ✅
- [x] Added `print_index_diagnostics()` function to `grading_dynamic_rubrics/pipeline.py`

### Files Created/Modified
- `autograder/grading_dynamic_rubrics/pipeline.py` - Added diagnostics function for active in-memory indexes

### Key Changes
- `print_index_diagnostics()` prints chunk counts and size statistics (chars/tokens) for all active indexes
- Uses the same persist directory logic as `setup_grading_environment()` (default: `tmp/in_memory_indexes/`)
- Respects `runtime.active_indexes` from config or can accept `index_subset` parameter

### Notes
- Diagnostics function is specific to `grading_dynamic_rubrics` module (not in `grading_pipeline`)
- Works with `InMemoryVectorStore` indexes only

---

## 2026-01-21 - Make index diagnostics independent of OpenAI keys

### Completed Tasks ✅
- [x] Updated `print_index_diagnostics()` to load `*.pkl` stores directly (no embedder init)

### Files Created/Modified
- `autograder/grading_dynamic_rubrics/pipeline.py` - Load pickles directly for diagnostics

### Notes
- This avoids triggering any LLM/embedder configuration, so it works without OpenAI credentials.

---

## 2026-01-19 - Dynamic rubric generation with LLM

### Completed Tasks ✅
- [x] Created prompt template file (rubric_generator_template.txt) with placeholders
- [x] Created Pydantic schema (rubric_schema.py) for JSON validation
- [x] Added source file loading function using _extract_text_from_pdf
- [x] Added prompt template loading and formatting functions
- [x] Added LLM integration function with retry logic and Pydantic validation
- [x] Added JSON to rubric structure conversion function
- [x] Added dual format saving function (JSON and YAML subdirectories)
- [x] Modified main() function with comprehensive CLI arguments
- [x] Created wrapper script create_dynamics_rubrics.x
- [x] Created comprehensive pytest test suite (test_create_dynamic_rubrics.py) with 25 tests

### Files Created/Modified
- `autograder/gp/rubric_generator_template.txt` - Prompt template for LLM rubric generation
- `autograder/gp/rubric_schema.py` - Pydantic models for validating LLM JSON responses
- `autograder/gp/create_dynamic_rubrics_for_each_question.py` - Complete rewrite with LLM-based dynamic rubric generation
- `autograder/create_dynamics_rubrics.x` - Wrapper script for easy execution
- `autograder/tests/test_create_dynamic_rubrics.py` - Comprehensive pytest test suite (25 tests covering all functions and error cases)

### Key Changes
- Transformed rubric generation from generic templates to LLM-based dynamic generation
- Added support for source file context (PDF, text, markdown) in prompts
- Implemented Pydantic validation with retry logic (up to 3 attempts)
- Added dual output format: JSON (raw LLM output) and YAML (pipeline-compatible)
- Comprehensive CLI with --source-file, --prompt-template, --llm-provider, --llm-model, --dry-run, --verbose
- Module execution support: `python -m gp.create_dynamic_rubrics_for_each_question`
- Default LLM configuration: Ollama with gpt-oss:20b (matching grader setup)
- JSON extraction handles markdown code blocks and plain JSON
- Criterion ID generation via slugification of dimension titles
- Automatic rubric config updates pointing to YAML files

### Notes
- Rubrics are saved in `<rubrics_dir>/json/` and `<rubrics_dir>/yaml/` subdirectories
- JSON files contain both raw LLM output and converted rubric structure
- YAML files are compatible with existing grading pipeline
- Prompt template supports {QUESTION_TEXT} and {SOURCE_FILE_CONTENT} placeholders
- Retry logic provides feedback to LLM on validation failures
- Comprehensive test suite covers all functions, error cases, and integration scenarios
- All 25 tests pass successfully

---

## 2026-01-18 - Embedder metadata verification

### Completed Tasks ✅
- [ ] Added embedder metadata save/load and verification for indexes
- [ ] Fixed circular import between index builders
- [ ] Added embedder details to index build/load output
- [ ] Disabled embedding prepend instructions and printed defaults
- [ ] Added embedding consistency diagnostics in similarity test
- [ ] Added side-by-side embedding value dump for debugging
- [ ] Excluded metadata from embeddings for text nodes
- [ ] Added YAML-driven flag to enable embedding diagnostics
- [ ] Added test to ensure metadata is excluded from embeddings

### Files Created/Modified
- `autograder/grading_pipeline/index_builder.py` - Added embedder metadata helpers and verification wrapper for ChromaDB load.
- `autograder/grading_pipeline/index_builder_in_memory.py` - Store/embedder metadata and print usage details; removed local helpers.
- `autograder/grading_pipeline/test_cosine_similarity.py` - Embedded consistency check output.
- `autograder/config/llm_config.py` - Print default embedding instructions, disable prepends.
- `autograder/grading_pipeline/config/sources.yaml` - Added debug flag for diagnostics.
- `autograder/tests/test_index_builder_in_memory.py` - Added metadata exclusion test.

### Key Changes
- Persist embedder info to `embedding_metadata.yaml` in index directories.
- Verify embedder matches before loading indexes; raise error on mismatch.
- Output embedder type/model during build and load for clarity.
- Use empty `text_instruction` and `query_instruction` to remove prepends.
- Compare stored/text/query embeddings to isolate mismatch causes.
- Print first 20 embedding values and cosine similarity.
- Ensure node embeddings use text only (no metadata).
- Gate embedding diagnostics behind config flag.
- Validate metadata does not affect embeddings.

### Notes
- Embedder metadata now guards against silent model drift.

---

## 2026-01-18 - Add index backend selection

### Completed Tasks ✅
- [ ] Added CLI flag to select index backend (ChromaDB vs in-memory)
- [ ] Routed pipeline index setup through backend selector
- [ ] Updated grading script to use in-memory backend explicitly

### Files Created/Modified
- `autograder/grading_pipeline.x` - Added index backend flag in run script.
- `autograder/grading_pipeline/cli.py` - Added `--index-backend` to CLI and passed through.
- `autograder/grading_pipeline/pipeline.py` - Added backend-aware index selection helper.

### Key Changes
- `--index-backend` controls which index builder is used at runtime.
- Pipeline setup now selects between ChromaDB and in-memory builders.
- Index directory help text now reflects generic persistence.

### Notes
- Default backend remains `chromadb` when the flag is omitted.

---

## 2026-01-18 - Align in-memory embed model on load

### Completed Tasks ✅
- [ ] Ensured in-memory loader uses stored embedding metadata
- [ ] Rebuilt in-memory indexes with BAAI/bge-small-en-v1.5
- [ ] Reran grading pipeline successfully

### Files Created/Modified
- `autograder/grading_pipeline/index_builder_in_memory.py` - Load embedding using stored metadata for verification.

### Key Changes
- Removed hardcoded MiniLM placeholder in in-memory load path.
- Embedding model now matches persisted metadata when loading indexes.

### Notes
- Grading run completed with 4/4 successful after rebuild.

---

## 2026-01-18 - Add embedding model log during index load

### Completed Tasks ✅
- [ ] Added log line showing resolved embedding model during index load

### Files Created/Modified
- `autograder/grading_pipeline/index_builder_in_memory.py` - Log configured embedding model for tracing.

### Key Changes
- Print embedding type and model name when configuring from stored metadata.

### Notes
- Improves traceability when debugging embedding model mismatches.
