# Task List: Weighted Checklist Grading System Implementation

**Format:** Each task includes:
- Task ID (e.g., T1.1)
- Title & description
- Deliverables
- Acceptance criteria
- Dependencies
- Estimated effort

---

## PHASE 1: Infrastructure (3-4 days)

### T1.1: Create Configuration Schema
**Title:** Define global configuration for categories and grading parameters

**Description:**
Create YAML configuration files that define:
- Category definitions (names, weights, descriptions)
- Grading parameters (min/max checks, evaluation methods)
- All values are parameterized (no hardcoding)

**Deliverables:**
- `config/grading_categories.yaml`
- `config/grading_config.yaml`
- `config/grading_config_schema.py` (validation rules)

**Acceptance Criteria:**
- [ ] Categories defined with weights and descriptions
- [ ] All weights positive, ratio between them is clear
- [ ] Config can be loaded and validated
- [ ] CLI can override config values
- [ ] Config values used throughout system (not hardcoded)

**Dependencies:** None

**Effort:** 4-6 hours

**Notes:**
- Example categories: semantic (w=1), application (w=2), clarity (w=1)
- Config schema should validate positive weights
- Document how to add new categories

---

### T1.2: Define Data Models & Schemas
**Title:** Create Pydantic models for all data structures

**Description:**
Define all data models used throughout the system:
- Check (with ID, text, category, weights)
- Rubric (with checks list and metadata)
- CheckEvaluation (pass/fail + evidence)
- GradeResult (score + calculation details)
- Appeal (version tracking for grade changes)

**Deliverables:**
- `grading_pipeline/models.py` (Pydantic models)
- `grading_pipeline/schemas.py` (JSON schema exports)
- Type hints for all functions

**Acceptance Criteria:**
- [ ] All models defined with full docstrings
- [ ] Models validate on instantiation
- [ ] Can serialize/deserialize to JSON
- [ ] JSON schemas match models
- [ ] Type hints on all function signatures

**Dependencies:** T1.1

**Effort:** 6-8 hours

**Notes:**
- Use Pydantic for validation
- Include metadata fields (timestamps, versions)
- Check model should reference category, not just store it

---

### T1.3: Set Up Data Storage Structure
**Title:** Organize directory structure for rubrics, grades, appeals

**Description:**
Create and document the directory structure for storing:
- Generated rubrics (raw, extracted, categorized, deduped)
- Student grades (evaluation results, final scores)
- Grade appeals (version history)
- Logs (grading runs, errors)

**Deliverables:**
- Directory structure created and documented
- `data/` directory with subdirectories
- Naming conventions documented
- File naming scheme for versions/appeals

**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] Clear naming convention for all files
- [ ] Can track versions (v1, v2, appeal_v1, etc.)
- [ ] Can retrieve all artifacts for any student/question
- [ ] Documented in README or guide

**Dependencies:** T1.1

**Effort:** 3-4 hours

**Notes:**
- Use ISO timestamps in filenames where applicable
- Version numbers should be sequential
- Consider archiving old appeals

---

## PHASE 2: Rubric Generation (1 week)

### T2.1: Update Rubric Generation Template
**Title:** Modify prompt template for check-based rubric generation

**Description:**
Update the LLM prompt template to generate rubrics suitable for check extraction:
- Emphasize non-overlapping dimensions
- Clear structure that can be parsed
- Generate rubrics that extract cleanly into checks
- Use absolute deductions (not fractions)

**Deliverables:**
- Updated `grading_pipeline/rubric_generator_template.txt`
- Examples of expected rubric output
- Documentation of changes from previous version

**Acceptance Criteria:**
- [ ] Template enforces non-overlapping dimensions
- [ ] Generated rubrics extract into 3-10 checks
- [ ] No fractions in deductions
- [ ] Checks are atomic (single evaluatable item)
- [ ] Tested with 2-3 sample questions

**Dependencies:** T1.1

**Effort:** 4-6 hours

**Notes:**
- Previous template can be reference point
- Include explicit non-overlap instruction
- Provide examples of good check breakdowns

---

### T2.2: Implement Check Extraction
**Title:** Parse rubric and extract discrete checks

**Description:**
Create function to:
- Parse rubric dimension descriptions
- Extract discrete, evaluatable checks
- Assign base weight (from dimension points)
- Map to source dimension
- Use LLM to help parse if needed

**Deliverables:**
- Function `extract_checks_from_rubric()` in `grading_pipeline/check_extraction.py`
- Unit tests with 3+ test cases
- Documentation with examples

**Acceptance Criteria:**
- [ ] Extracts 3-10 checks per rubric
- [ ] Each check is atomic and evaluatable
- [ ] Base weight assigned from source dimension
- [ ] Preserves reference to source dimension
- [ ] Unit tests pass
- [ ] Works with sample rubrics

**Dependencies:** T2.1, T1.2

**Effort:** 8-10 hours

**Notes:**
- Could parse dimension descriptions or use LLM for parsing
- Each check should be 1-2 sentences
- Base weight: divide dimension points by number of checks

---

### T2.3: Implement Category Assignment
**Title:** LLM assigns category to each check

**Description:**
Create function to:
- Use LLM to categorize each check
- Provide category definitions from config
- Return checks with category field
- Handle edge cases (ambiguous checks)

**Deliverables:**
- Function `assign_categories_to_checks()` in `grading_pipeline/categorization.py`
- LLM prompt for categorization
- Unit tests with edge cases
- Documentation

**Acceptance Criteria:**
- [ ] All checks assigned valid categories
- [ ] Category matches config definitions
- [ ] Unit tests with edge cases pass
- [ ] Works with 2+ different category sets
- [ ] LLM prompt is clear and unambiguous
- [ ] Handles ambiguous checks (logs flagged cases)

**Dependencies:** T2.2, T1.1, T1.2

**Effort:** 6-8 hours

**Notes:**
- LLM prompt should give category definitions and examples
- Document any checks that can't be clearly categorized
- Consider storing categorization confidence score

---

### T2.4: Implement Deduplication
**Title:** Remove duplicate checks from rubric

**Description:**
Create function to:
- Detect duplicate checks using LLM
- Remove duplicates, keeping first occurrence
- Weight source of truth is category (not dimension)
- Return deduped list + metadata

**Deliverables:**
- Function `deduplicate_checks()` in `grading_pipeline/deduplication.py`
- LLM prompt for duplicate detection
- Unit tests (including true positives, negatives, edge cases)
- Documentation

**Acceptance Criteria:**
- [ ] Correctly identifies duplicate checks
- [ ] Removes duplicates preserving first occurrence
- [ ] Does not remove similar but distinct checks
- [ ] Unit tests cover: no dupes, obvious dupes, subtle dupes
- [ ] Returns metadata (count of duplicates removed)
- [ ] Works with 10+ check sets

**Dependencies:** T2.3, T1.2

**Effort:** 8-10 hours

**Notes:**
- LLM prompt should be explicit about what "duplicate" means
- Consider confidence threshold (e.g., only remove high-confidence dupes)
- Log borderline cases for human review
- Test with generated rubrics (not just synthetic data)

---

### T2.5: Integrate Rubric Generation Pipeline
**Title:** Chain all steps: Generate → Extract → Categorize → Deduplicate

**Description:**
Create orchestration function that:
- Calls each step in sequence
- Stores intermediate artifacts
- Handles errors gracefully
- Returns final rubric
- Provides detailed logging

**Deliverables:**
- Function `generate_complete_rubric()` in `grading_pipeline/rubric_generator.py`
- Artifact storage (all intermediate outputs saved)
- Integration tests
- Logging and error handling

**Acceptance Criteria:**
- [ ] All steps execute in correct order
- [ ] Intermediate artifacts stored
- [ ] Final rubric is clean (no dupes, all categorized)
- [ ] Integration tests pass with sample questions
- [ ] Error handling graceful (logs + continues)
- [ ] Reproducible (same input → same output)

**Dependencies:** T2.1-T2.4, T1.3

**Effort:** 6-8 hours

**Notes:**
- Store all intermediate artifacts for debugging
- Function should be idempotent (can re-run)
- Logging should be detailed enough to debug
- Consider caching rubrics (don't regenerate)

---

## PHASE 3: Evaluation & Scoring (5-7 days)

### T3.1: Implement Check Evaluation (LLM)
**Title:** Evaluate each check for a student answer

**Description:**
Create function to:
- Use LLM to evaluate if student passes a check
- Provide question text, evidence, student answer, check text
- Return pass/fail + evidence/explanation
- Store evaluation method used

**Deliverables:**
- Function `evaluate_check_llm()` in `grading_dynamic_rubrics/check_evaluation.py`
- LLM prompt for check evaluation
- Unit tests with diverse checks
- Documentation

**Acceptance Criteria:**
- [ ] Correctly evaluates diverse checks
- [ ] Returns pass/fail with supporting evidence
- [ ] LLM prompt is clear
- [ ] Unit tests pass with sample answers
- [ ] Handles ambiguous cases (borderline pass/fail)
- [ ] Stores evaluation method and confidence

**Dependencies:** Phase 2 complete, T1.2

**Effort:** 8-10 hours

**Notes:**
- Prompt should ask for explanation, not just binary answer
- Store both binary result and confidence score
- Document cases where evaluation is uncertain
- Consider 3-way evaluation (pass/uncertain/fail) for later phases

---

### T3.2: Implement Check Evaluation (Hybrid)
**Title:** LLM evaluation with manual review option for borderline cases

**Description:**
Create function to:
- Evaluate checks using LLM
- Calculate confidence score
- Flag low-confidence cases for manual review
- Allow human override
- Store both LLM and human assessments

**Deliverables:**
- Function `evaluate_check_hybrid()` in `grading_dynamic_rubrics/check_evaluation.py`
- Confidence scoring logic
- Manual review flag/override mechanism
- Documentation

**Acceptance Criteria:**
- [ ] Returns evaluation + confidence score
- [ ] Flags low-confidence cases (configurable threshold)
- [ ] Supports manual override
- [ ] Stores both LLM and manual assessments
- [ ] Unit tests with edge cases
- [ ] Works with configurable confidence threshold

**Dependencies:** T3.1

**Effort:** 6-8 hours

**Notes:**
- Confidence score: 0-1 based on LLM certainty
- Threshold configurable (default 0.9)
- Manual override persists in evaluation results
- Document cases requiring review

---

### T3.3: Implement Scoring Algorithm
**Title:** Calculate final score from check results and category weights

**Description:**
Create function to:
- Take check evaluation results
- Apply category weights
- Calculate final score using formula
- Store detailed calculation for audit trail
- Ensure score is 0-10

**Deliverables:**
- Function `compute_final_score()` in `grading_dynamic_rubrics/scoring.py`
- Unit tests (including edge cases)
- Calculation details stored
- Documentation

**Acceptance Criteria:**
- [ ] Correctly applies formula: `(Σ pass_i × weight_i × cat_weight_i) / (Σ weight_i × cat_weight_i) × 10`
- [ ] Final score always 0-10
- [ ] Calculation details stored (numerator, denominator, passes count)
- [ ] Unit tests cover: all pass, all fail, mixed, zero weights (error)
- [ ] Works with different weight distributions
- [ ] Mathematically correct

**Dependencies:** T1.2, T3.1

**Effort:** 6-8 hours

**Notes:**
- Calculation must be reproducible (store all components)
- Handle edge case: all checks fail (score = 0)
- Handle edge case: invalid weights (raise error)
- Store numerator, denominator for verification

---

### T3.4: Implement Grade Storage & Appeal Tracking
**Title:** Store grades with version history for appeals

**Description:**
Create functions to:
- Store grade results with version numbering
- Track appeals and weight changes
- Retrieve grade history for a student
- Ensure only upward grade adjustments
- Store appeal justification

**Deliverables:**
- Functions in `grading_dynamic_rubrics/grade_storage.py`:
  - `store_grade()`
  - `store_grade_appeal()`
  - `get_grade_history()`
  - `validate_grade_increase()`
- Unit tests
- Documentation

**Acceptance Criteria:**
- [ ] Grades stored with version numbers (v1, v2, etc.)
- [ ] Appeals stored with version numbers (appeal_v1, etc.)
- [ ] Only upward adjustments allowed
- [ ] Error raised on downward adjustment
- [ ] Full history retrievable
- [ ] All grades reproducible from stored data
- [ ] Unit tests pass

**Dependencies:** T3.3, T1.3

**Effort:** 8-10 hours

**Notes:**
- Version numbering: sequential integers
- Appeal record includes: new weights, reason, timestamp
- Enforce: new_score ≥ old_score (raise error otherwise)
- Store all calculation details for audit trail

---

## PHASE 4: Testing & Validation (5-7 days)

### T4.1: Unit Tests for Individual Functions
**Title:** Test each function in isolation

**Description:**
Create comprehensive unit tests for:
- Check extraction
- Category assignment
- Deduplication
- Check evaluation
- Scoring algorithm

**Deliverables:**
- `tests/test_extraction.py`
- `tests/test_categorization.py`
- `tests/test_deduplication.py`
- `tests/test_evaluation.py`
- `tests/test_scoring.py`
- Unit tests for storage functions

**Acceptance Criteria:**
- [x] >80% code coverage
- [x] All happy path cases tested
- [x] Edge cases tested (empty inputs, invalid data)
- [x] Error cases tested (invalid weights, bad LLM output)
- [x] All tests passing (183 tests, 2026-03-30)
- [x] Tests documented

**Dependencies:** Phase 3 complete

**Effort:** 16-20 hours

**Notes:**
- Mock LLM calls in tests
- Use pytest framework
- Test fixtures for reusable test data
- Document what each test verifies

---

### T4.2: Integration Tests
**Title:** Test full pipeline end-to-end

**Description:**
Create integration tests that:
- Test full rubric generation pipeline
- Test full grading pipeline
- Test grade appeals and recalculation
- Test with realistic data

**Deliverables:**
- `tests/test_rubric_pipeline.py`
- `tests/test_grading_pipeline.py`
- `tests/test_appeal_workflow.py`
- Sample data sets for testing

**Acceptance Criteria:**
- [x] All integration tests passing (223 tests, 2026-03-30)
- [x] Tests cover full happy path
- [x] Tests cover error scenarios
- [x] Uses realistic sample questions/answers
- [x] Tests verifiable (clear assertions)
- [x] Documented

**Dependencies:** T4.1, Phase 3 complete

**Effort:** 12-16 hours

**Notes:**
- Consider using sample questions (q01, q02, etc.)
- Include edge cases (all pass, all fail, tied weights)
- Document expected outcomes for each scenario

---

### T4.3: Sample Grading Test
**Title:** Grade sample student answers, compare with manual assessment

**Description:**
Manually:
1. Generate rubrics for 5 questions (q01-q05)
2. Grade 1 sample student answer per question
3. Compare LLM scores with instructor evaluation
4. Review check evaluations for accuracy
5. Document discrepancies

**Deliverables:**
- 5 generated rubrics (stored)
- 5 graded sample answers (stored)
- Comparison report (LLM scores vs instructor)
- Discrepancy analysis
- Category weight adjustment recommendations (if needed)

**Acceptance Criteria:**
- [x] All 5 rubrics generated (q01, q05 from LLM; q02-q04 manually authored in rubrics_dynamic/yaml/)
- [x] All 5 answers graded (3 types each: good, less_good, wrong) via t4_3_grading_sample.py
- [x] Scores compared: good > wrong holds for all 5; good > less_good > wrong holds for q01, q04
- [x] Discrepancies documented: q02 (Δ=0.29), q03 (Δ=0.02 noise), q05 (Δ=0.24) in t4_3_report.md
- [x] Root cause analysis: int() truncation, stopword keywords, evidence-count semantic scoring
- [x] Recommendations in t4_3_report.md (P1-P5 priorities)
**Completed:** 2026-03-30 (synthetic answers; instructor comparison deferred to future revision)

**Dependencies:** T4.2, Phase 3 complete

**Effort:** 12-16 hours

**Notes:**
- Use real student answers (not synthetic)
- Involve instructor in comparison
- Document reasoning for any weight adjustments
- Use results to validate category weights are reasonable

---

### T4.4: Regression Testing
**Title:** Ensure no functionality breaks with changes

**Description:**
Create automated test suite that:
- Runs on every code change
- Catches unintended regressions
- Benchmarks performance
- Verifies reproducibility

**Deliverables:**
- CI/CD pipeline (GitHub Actions or similar)
- Performance benchmarks
- Regression test suite
- Documentation

**Acceptance Criteria:**
- [ ] CI/CD pipeline set up
- [ ] All tests run automatically
- [ ] Performance benchmarks established
- [ ] Alerts on regressions
- [ ] Can identify which commit broke something

**Dependencies:** T4.1-T4.3

**Effort:** 8-10 hours

**Notes:**
- Use GitHub Actions or similar CI/CD
- Set performance baselines
- Track test execution time
- Document how to investigate regressions

---

## PHASE 5: Documentation & Deployment (3-5 days)

### T5.1: User Documentation
**Title:** Document how to use the system

**Description:**
Create user guides covering:
- System overview
- Quick start guide
- Configuration reference
- Command-line options
- Common tasks
- Troubleshooting

**Deliverables:**
- `docs/GRADING_USER_GUIDE.md`
- `docs/CONFIG_GUIDE.md`
- `docs/APPEAL_PROCEDURE.md`
- Inline code documentation (docstrings)

**Acceptance Criteria:**
- [ ] All major features documented
- [ ] Quick start guide works
- [ ] Configuration options explained
- [ ] CLI usage documented
- [ ] Screenshots/examples provided (if applicable)
- [ ] Troubleshooting section included

**Dependencies:** Phase 3 complete

**Effort:** 8-10 hours

**Notes:**
- Include examples of common tasks
- Document configuration options with defaults
- Include troubleshooting for common errors

---

### T5.2: Administrator Documentation
**Title:** Document system architecture and maintenance

**Description:**
Create admin guides covering:
- System architecture overview
- Data flow diagrams
- Adding new categories globally
- Changing weights globally
- Monitoring and logging
- Data recovery procedures

**Deliverables:**
- `docs/ARCHITECTURE.md`
- `docs/MAINTENANCE.md`
- `docs/DATA_RECOVERY.md`
- Deployment checklist

**Acceptance Criteria:**
- [ ] Architecture clearly explained
- [ ] Data flow documented with diagrams
- [ ] Admin tasks documented
- [ ] Recovery procedures documented
- [ ] Deployment checklist provided
- [ ] Logging and monitoring explained

**Dependencies:** Phase 3 complete

**Effort:** 6-8 hours

**Notes:**
- Include system diagrams
- Document how to monitor system health
- Include recovery procedures for common errors

---

### T5.3: Deployment Guide
**Title:** Set up system for production use

**Description:**
Create deployment guide covering:
- System requirements
- Installation steps
- Initial configuration
- Running the system
- Monitoring
- Updating/upgrading

**Deliverables:**
- `docs/DEPLOYMENT.md`
- Setup scripts (bash/Python)
- Docker configuration (optional)
- Configuration templates

**Acceptance Criteria:**
- [ ] Installation steps are clear
- [ ] Can deploy from scratch
- [ ] All configuration options documented
- [ ] Can monitor system
- [ ] Update procedures documented
- [ ] Rollback procedures documented

**Dependencies:** T5.1, T5.2

**Effort:** 6-8 hours

**Notes:**
- Provide setup scripts to automate installation
- Document all environment variables
- Include Docker setup (optional but recommended)
- Document backup/restore procedures

---

## Summary by Phase

| Phase | Tasks | Hours | Duration |
|-------|-------|-------|----------|
| 1: Infrastructure | T1.1-T1.3 | 13-18 | 2-3 days |
| 2: Rubric Generation | T2.1-T2.5 | 36-48 | 1 week |
| 3: Evaluation & Scoring | T3.1-T3.4 | 36-48 | 1 week |
| 4: Testing & Validation | T4.1-T4.4 | 48-62 | 1.5 weeks |
| 5: Documentation | T5.1-T5.3 | 20-26 | 4-5 days |
| **TOTAL** | **19 tasks** | **153-202 hours** | **4-5 weeks** |

---

## Task Dependencies Graph

```
T1.1 → T1.2 → T1.3
       ↓        ↓
T2.1 ─────────┐
  ↓           ↓
T2.2 → T2.3 → T2.4 → T2.5
              ↓       ↓
              T3.1 ─→ T3.2
                ↓       ↓
              T3.3 ────→ T3.4
                         ↓
                  T4.1 ← T4.2 ← T4.3
                   ↓
                  T4.4

T5.1 → T5.2 → T5.3
(can start after Phase 3 is mostly complete)
```

---

## Parallelization

These tasks can be done in parallel:
- T1.1 and T1.2 (mostly independent)
- T1.3 (can be done during T1.1-T1.2)
- T4 tasks (once Phase 3 is complete, can test in parallel)
- T5 documentation (can be started early, finalized after Phase 4)

Suggested timeline:
- Week 1: Phase 1 + start Phase 2
- Week 2: Complete Phase 2, start Phase 3
- Week 3: Complete Phase 3, start Phase 4
- Week 4: Complete Phase 4, start Phase 5
- Week 5: Complete Phase 5, buffer/polish

---

## PHASE 6: LLM Provider Migration (1-2 days)

### T6.1: Add llama.cpp Provider Support ✅ CLOSED
**Status:** Implemented but superseded. Decision: Use Ollama. See `llamacpp_ollama/TASK_LIST.md`.
**Title:** Implement llama.cpp as an LLM provider option

**Description:**
Add llama.cpp (llama-cpp-python) as a supported provider in the LLM configuration system:
- Add llama.cpp import and configuration in `config/llm_config.py`
- Update `configure_llm()` function to handle "llamacpp" provider
- Add environment variables for llama.cpp configuration (model path, context size, etc.)
- Update `load_env_config()` to include llama.cpp settings
- Maintain compatibility with existing providers (openai, anthropic, gemini, ollama)

**Deliverables:**
- Updated `config/llm_config.py` with llama.cpp support
- Environment variable documentation for llama.cpp settings
- Updated configuration loading logic
- Example `.env` entries for llama.cpp

**Acceptance Criteria:**
- [ ] llama.cpp can be selected as provider via `configure_llm("llamacpp")`
- [ ] Configuration loads model path and parameters from environment
- [ ] Existing providers remain functional
- [ ] Error handling for missing model files
- [ ] Documentation of required environment variables
- [ ] Compatible with llama-cpp-python package

**Dependencies:** None

**Effort:** 4-6 hours

**Notes:**
- llama.cpp requires local model file path (GGUF format)
- Consider parameters: n_ctx (context size), n_gpu_layers, temperature
- Environment variables: LLAMACPP_MODEL_PATH, LLAMACPP_N_CTX, etc.
- llama-cpp-python is already installed via pip

---

### T6.2: Create llama.cpp Integration Tests ❌ CANCELLED
**Status:** Cancelled — investigation concluded, Ollama chosen instead.
**Title:** Test llama.cpp provider integration

**Description:**
Create comprehensive tests for llama.cpp provider:
- Unit tests for configuration loading
- Integration tests for basic inference
- Error handling tests (missing model, invalid parameters)
- Performance/smoke tests to verify model loads and generates responses
- Comparison tests with existing providers (if applicable)

**Deliverables:**
- `tests/test_llama_cpp.py` with comprehensive test suite
- Test fixtures for model configuration
- Documentation of test requirements (model file needed for tests)
- Mock tests for cases where model is unavailable

**Acceptance Criteria:**
- [ ] Tests verify llama.cpp provider initializes correctly
- [ ] Tests verify basic text generation works
- [ ] Tests handle missing model file gracefully
- [ ] Tests verify configuration parameter passing
- [ ] Tests can run with or without actual model file (mocked)
- [ ] All tests passing with >80% coverage of llama.cpp code paths
- [ ] Documentation explains how to run tests with real models

**Dependencies:** T6.1

**Effort:** 4-6 hours

**Notes:**
- Consider using pytest fixtures for model setup
- Mock the llama.cpp model for CI/CD (large model files)
- Include end-to-end test with small test model if available
- Document how to obtain and configure test models
- Test both successful and error scenarios

---
