# Project Tasks - LLM-Based Grading with Preprocessed Evidence

**Last Updated:** 2026-01-25

---

## Summary

- **Total Tasks:** 5
- **Completed:** 2
- **In Progress:** 0
- **Pending:** 3
- **Blocked:** 1

---

## Task List

### ✅ Completed Tasks

- [x] **#1: Create pytest test suite for grade_with_evidence module**
  - File: `tests/test_grade_with_evidence.py`
  - Coverage: Evidence formatting, prompt construction, criterion grading, student grading, integration tests
  - Status: **COMPLETED**
  - Dependencies: None

- [x] **#2: Create pytest test suite for grade_from_evidence CLI script**
  - File: `tests/test_grade_from_evidence.py`
  - Coverage: Evidence loading, submission loading, CLI arguments, output files, error handling
  - Status: **COMPLETED**
  - Dependencies: Requires #1 (unblocked)

---

## Task List (Continued)

### ⏳ Pending Tasks - Ready to Start

- [ ] **#3: Generate evidence preprocessing for q01 and q03-q10**
  - Files: `reranker_results/q01_results.json`, `q03_results.json` ... `q10_results.json`
  - Description: Create evidence context JSON files in reranker_results/ for remaining questions (9 files total)
  - Details:
    - Each file follows structure of `q02_results.json`
    - Contains question_id, question_text, grading_context array
    - Each criterion includes: criterion_id, criterion_description, max_score, evidence[]
    - Evidence array: source_id, texts, reranker_scores, similarity_scores, indexes
  - Status: **PENDING**
  - Dependencies: None (can start immediately)
  - Unblocks: #5

- [ ] **#4: Create documentation for LLM-based grading approach**
  - Files: `grading_dynamic_rubrics/README.md` (recommended)
  - Description: Document the new semantic-only LLM-based grading approach
  - Details:
    - Explain differences from previous keyword+semantic scoring
    - Usage examples for grade_from_evidence.py
    - Per-criterion prompt structure explanation
    - How evidence context is used
    - Expected output format with examples
    - Comparison table: LLM-decides-scores vs keyword-based
    - Running tests and validation
  - Status: **PENDING**
  - Dependencies: None (can start immediately)
  - Notes: `grade-spec.md` already created as architectural specification

---

### ⏸️ Pending Tasks - Blocked

- [ ] **#5: Implement batch grading across multiple students**
  - Files: Extend `grading_dynamic_rubrics/grade_with_evidence.py` and `grade_from_evidence.py`
  - Description: Create batch grading functionality for multiple students
  - Details:
    - Add `batch_grade_students()` function to grade_with_evidence.py
    - Accepts list of student submissions and evidence context
    - Returns aggregated results
    - Handle errors per-student without stopping batch
    - Extend CLI to support --batch flag
    - Add pattern matching for submissions (e.g., student_*_q02_*.yaml)
    - Progress reporting and summary statistics
  - Status: **PENDING** (BLOCKED BY #3)
  - Dependencies: Requires #3 (Generate evidence preprocessing)
  - Notes: Will be unblocked when #3 completes

---

## Dependency Graph

```
#1: Test grade_with_evidence
      ↓
#2: Test grade_from_evidence [COMPLETED - depends on #1]

#3: Generate evidence preprocessing
      ↓
#5: Implement batch grading [BLOCKED - depends on #3]

#4: Documentation [INDEPENDENT]
```

---

## Quick Status Check

| Task | Status | Blocked By | Progress |
|------|--------|-----------|----------|
| #1 | ✅ Complete | — | 100% |
| #2 | ✅ Complete | — | 100% |
| #3 | ⏳ Pending | — | 0% |
| #4 | ⏳ Pending | — | 0% |
| #5 | ⏸️ Blocked | #3 | 0% |

---

## Next Steps

### Immediate Actions (Pick One)

1. **Start #3 (Evidence Preprocessing)**
   - Generate q01_results.json and q03-q10_results.json
   - Expected time: High effort (9 files with structured evidence)
   - Unblocks: #5

2. **Start #4 (Documentation)**
   - Write README for LLM-based approach
   - Expected time: Medium effort
   - Independent task

### Then

3. **After #3 → Start #5 (Batch Grading)**
   - Implement batch functionality
   - Expected time: High effort
   - Will work with preprocessed evidence from #3

---

## Task Tracking Notes

- **#1, #2**: Test suites created with comprehensive coverage
  - `tests/test_grade_with_evidence.py` - 70+ test cases
  - `tests/test_grade_from_evidence.py` - 30+ test cases

- **#3**: Requires creating evidence JSON files following q02_results.json structure
  - Best approach: Use existing reranking/retrieval logic or manually create from source material
  - Needed for grading q01, q03-q10 with new approach

- **#4**: Documentation should reference grade-spec.md and explain practical usage

- **#5**: Will enable grading multiple students in single run with shared evidence context

---

## Related Files

- `grade-spec.md` - Architectural specification (created)
- `CLAUDE.md` - Agent constraints
- `AGENT.md` - General behavioral rules
- `grading_dynamic_rubrics/grade_with_evidence.py` - Core grading function
- `grading_dynamic_rubrics/grade_from_evidence.py` - CLI interface
- `reranker_results/q02_results.json` - Example evidence context (model for #3)
