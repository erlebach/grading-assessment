# Implementation Plan: Weighted Checklist Grading System

**Date**: 2026-01-25
**Status**: Ready for Implementation
**Estimated Duration**: 2-3 weeks with parallel work

---

## Phase Overview

| Phase | Tasks | Duration | Depends On |
|-------|-------|----------|-----------|
| **Phase 1: Infrastructure** | Config, data structures, schemas | 3-4 days | None |
| **Phase 2: Rubric Generation** | Generate → Extract → Categorize → Deduplicate | 1 week | Phase 1 |
| **Phase 3: Evaluation & Scoring** | LLM evaluation, scoring algorithm | 5-7 days | Phase 2 |
| **Phase 4: Testing & Validation** | Unit tests, integration tests, sample grading | 5-7 days | Phase 3 |
| **Phase 5: Documentation & Deployment** | API docs, user guide, deployment | 3-5 days | Phase 4 |

---

## Phase 1: Infrastructure Setup (3-4 days)

### Task 1.1: Create Configuration Schema
**Objective:** Define configuration structure for category weights and grading parameters
**Deliverables:**
- `config/grading_categories.yaml` - Global category definitions and weights
- `config/grading_config.yaml` - General grading parameters
- Configuration validation schema (JSON Schema or Pydantic)

**Files to Create:**
```
config/
  ├── grading_categories.yaml
  ├── grading_config.yaml
  └── grading_config_schema.py (validation)
```

**Key Parameters:**
```yaml
categories:
  semantic:
    weight: 1
  application:
    weight: 2
  clarity:
    weight: 1

grading:
  min_checks_per_question: 3
  max_checks_per_question: 15
  evaluation_method: "llm"  # or "hybrid", "rubric"
  enable_appeal_tracking: true
```

**CLI Overrides:**
- `--category-weights semantic:1 application:2 clarity:1`
- `--evaluation-method llm`

---

### Task 1.2: Define Data Models & Schemas
**Objective:** Create Pydantic models for all data structures
**Deliverables:**
- Check model (with ID, text, category, base_weight, etc.)
- Rubric model (with checks list)
- Evaluation result model (check pass/fail + evidence)
- Grade result model (final score + calculation details)
- Appeal record model (version tracking)

**Files to Create:**
```
grading_pipeline/
  ├── models.py (Pydantic models)
  └── schemas.py (JSON schema exports)
```

**Models:**
```python
class Check(BaseModel):
    check_id: str
    text: str
    source_dimension: str
    base_weight: float
    category: str  # semantic, application, clarity, etc.

class Rubric(BaseModel):
    question_id: str
    checks: List[Check]
    metadata: dict

class CheckEvaluation(BaseModel):
    check_id: str
    passed: bool
    evidence: str
    evaluation_method: str
    timestamp: datetime

class GradeResult(BaseModel):
    student_id: str
    question_id: str
    evaluation_results: List[CheckEvaluation]
    final_score: float
    calculation_details: dict
    category_weights: dict
    version: int

class Appeal(BaseModel):
    version: int
    timestamp: datetime
    reason: str
    old_weights: dict
    new_weights: dict
    old_score: float
    new_score: float
```

---

### Task 1.3: Set Up Data Storage Structure
**Objective:** Organize where all artifacts are stored
**Deliverables:**
- Directory structure for rubrics, grades, appeals
- Naming conventions for files
- Metadata for tracking versions and changes

**Directory Structure:**
```
data/
├── rubrics/
│   ├── q01/
│   │   ├── raw.json                 (LLM-generated)
│   │   ├── checks.json              (extracted checks)
│   │   ├── categorized.json         (with categories)
│   │   └── deduped.json             (final rubric)
│   ├── q02/
│   └── ...
├── grades/
│   ├── q01/
│   │   ├── student_001/
│   │   │   ├── evaluation.json      (raw check results)
│   │   │   ├── score_v1.json        (final score with weights)
│   │   │   ├── appeal_v2.json       (after first appeal)
│   │   │   └── appeal_v3.json       (after second appeal)
│   │   └── student_002/
│   │       └── ...
│   └── ...
└── logs/
    └── grading_<timestamp>.log
```

---

## Phase 2: Rubric Generation Pipeline (1 week)

### Task 2.1: Update Rubric Generation Template
**Objective:** Modify template to generate standard, clear rubrics
**Depends On:** Phase 1
**Deliverables:**
- Updated `rubric_generator_template.txt`
- Prompt that emphasizes non-overlapping dimensions
- Uses absolute deductions (not fractions)

**Changes:**
- Add constraint: "Each dimension evaluates ONE distinct aspect"
- Add examples of checks extracted from dimensions
- Emphasize that LLM output will be parsed for checks

---

### Task 2.2: Implement Check Extraction
**Objective:** Parse rubric and extract discrete checks
**Depends On:** Task 2.1
**Deliverables:**
- Function `extract_checks_from_rubric(rubric: Rubric) → List[Check]`
- Uses LLM to parse dimension descriptions
- Maps checks to source dimensions with base weights

**Function Signature:**
```python
def extract_checks_from_rubric(
    rubric: dict,
    llm: Any,
    verbose: bool = False
) -> List[Check]:
    """
    Parse rubric dimensions and extract discrete checks.

    Args:
        rubric: Generated rubric with dimensions
        llm: LLM instance for parsing
        verbose: Enable verbose output

    Returns:
        List of Check objects with source dimension and base weight
    """
```

**Key Points:**
- Each check extracted from dimension description
- Base weight = source dimension's point value (or subdivided if multiple checks)
- Preserve source dimension for reference
- Store extraction metadata

---

### Task 2.3: Implement Category Assignment
**Objective:** LLM assigns category (semantic/application/clarity) to each check
**Depends On:** Task 2.2
**Deliverables:**
- Function `assign_categories_to_checks(checks: List[Check], categories_config: dict, llm: Any) → List[Check]`
- Uses LLM with category definitions from config
- Returns checks with category field populated

**Function Signature:**
```python
def assign_categories_to_checks(
    checks: List[Check],
    categories_config: dict,
    llm: Any,
    verbose: bool = False
) -> List[Check]:
    """
    Assign category to each check based on LLM analysis.

    Args:
        checks: List of checks to categorize
        categories_config: Category definitions from config
        llm: LLM instance
        verbose: Enable verbose output

    Returns:
        Checks with category field populated
    """
```

**LLM Prompt:**
```
For each check, determine which category it belongs to:

Categories:
{categories from config with descriptions and examples}

Checks to categorize:
{checks}

Respond with JSON:
[
  {"check_id": "...", "category": "semantic"},
  ...
]
```

---

### Task 2.4: Implement Deduplication
**Objective:** Remove duplicate checks from final rubric
**Depends On:** Task 2.3
**Deliverables:**
- Function `deduplicate_checks(checks: List[Check], llm: Any) → List[Check]`
- LLM determines if two checks are duplicates
- Keeps first occurrence, removes duplicates
- Category weight is source of truth (not dimension points)

**Function Signature:**
```python
def deduplicate_checks(
    checks: List[Check],
    llm: Any,
    verbose: bool = False
) -> Tuple[List[Check], dict]:
    """
    Remove duplicate checks from rubric.

    Args:
        checks: List of checks with categories assigned
        llm: LLM instance for duplicate detection
        verbose: Enable verbose output

    Returns:
        (deduped_checks, metadata with duplicate count)
    """
```

**Logic:**
```
For each check pair (i, j) where i < j:
  LLM: "Do these two checks evaluate the same thing?"
       Check i: "Defines object"
       Check j: "Provides object definition"
  → Yes (duplicate) → Remove check j
  → No (distinct) → Keep both

After deduplication, all remaining checks are unique.
Weight now comes from check.category, not source dimension.
```

---

### Task 2.5: Integrate Rubric Generation Pipeline
**Objective:** Chain all steps: Generate → Extract → Categorize → Deduplicate
**Depends On:** Tasks 2.1-2.4
**Deliverables:**
- Function `generate_complete_rubric(question: Question, llm: Any, config: dict) → Rubric`
- Calls each step in sequence
- Stores intermediate artifacts
- Returns final deduplicated rubric

**Workflow:**
```python
def generate_complete_rubric(
    question: Question,
    llm: Any,
    config: dict,
    verbose: bool = False
) -> Rubric:
    # 1. Generate raw rubric
    raw_rubric = generate_rubric_with_llm(...)

    # 2. Extract checks
    checks = extract_checks_from_rubric(raw_rubric, llm)

    # 3. Assign categories
    checks = assign_categories_to_checks(checks, config['categories'], llm)

    # 4. Deduplicate
    checks, dedup_metadata = deduplicate_checks(checks, llm)

    # 5. Store artifacts
    save_rubric_artifacts(raw_rubric, checks, dedup_metadata)

    return Rubric(question_id=..., checks=checks)
```

---

## Phase 3: Evaluation & Scoring (5-7 days)

### Task 3.1: Implement Check Evaluation (LLM-based)
**Objective:** Evaluate each check for a student answer
**Depends On:** Phase 2
**Deliverables:**
- Function `evaluate_check_llm(check: Check, student_answer: str, evidence: str, llm: Any) → CheckEvaluation`
- LLM determines if student passes this check
- Returns pass/fail with evidence

**Function Signature:**
```python
def evaluate_check_llm(
    check: Check,
    student_answer: str,
    evidence: str,
    llm: Any,
    question_text: str = None
) -> CheckEvaluation:
    """
    Evaluate if student answer satisfies a check using LLM.

    Args:
        check: Check definition
        student_answer: Student's answer text
        evidence: Supporting material/evidence
        llm: LLM instance
        question_text: Question asked (for context)

    Returns:
        CheckEvaluation with pass/fail and evidence
    """
```

**LLM Prompt:**
```
Question: {question_text}

Evidence/Source Material: {evidence}

Student Answer: {student_answer}

Check to evaluate: "{check.text}"

Does the student answer satisfy this check?

Criteria for passing:
- Student clearly demonstrates understanding of this specific element
- Evidence in answer directly shows/implies this aspect

Response (JSON):
{
  "passed": true/false,
  "explanation": "Why student passed or failed this check",
  "quote": "Relevant quote from student answer"
}
```

---

### Task 3.2: Implement Check Evaluation (Hybrid with Manual Review)
**Objective:** LLM evaluation with option for manual review on borderline cases
**Depends On:** Task 3.1
**Deliverables:**
- Function `evaluate_check_hybrid(check: Check, student_answer: str, evidence: str, llm: Any, confidence_threshold: float = 0.9) → CheckEvaluation`
- Returns (pass/fail, confidence_score)
- If confidence < threshold, flags for manual review
- Stores both LLM assessment and manual override (if provided)

**Feature:**
```python
evaluation = evaluate_check_hybrid(...)

if evaluation.confidence < 0.9:
    print(f"NEEDS REVIEW: {check.text}")
    print(f"LLM assessment: {evaluation.passed}")
    # Human provides manual override if desired
    evaluation.manual_override = True
    evaluation.manual_result = True/False
```

---

### Task 3.3: Implement Scoring Algorithm
**Objective:** Calculate final score from check results and category weights
**Depends On:** Phase 1
**Deliverables:**
- Function `compute_final_score(evaluation_results: List[CheckEvaluation], rubric: Rubric, category_weights: dict) → GradeResult`
- Applies formula: `(Σ pass_i × weight_i × cat_weight) / (Σ weight_i × cat_weight) × 10`
- Stores calculation details for audit trail

**Function Signature:**
```python
def compute_final_score(
    evaluation_results: List[CheckEvaluation],
    rubric: Rubric,
    category_weights: dict
) -> GradeResult:
    """
    Compute final score from check evaluations.

    Args:
        evaluation_results: Pass/fail for each check
        rubric: Rubric with check definitions and base weights
        category_weights: Global weights for categories

    Returns:
        GradeResult with score and calculation details
    """
```

**Algorithm:**
```python
total_weighted_passed = 0
total_weight = 0

for check in rubric.checks:
    result = find_evaluation(check.id, evaluation_results)

    cat_weight = category_weights[check.category]
    final_weight = check.base_weight * cat_weight

    if result.passed:
        total_weighted_passed += final_weight

    total_weight += final_weight

score = (total_weighted_passed / total_weight) * 10

return GradeResult(
    score=score,
    numerator=total_weighted_passed,
    denominator=total_weight,
    passes=sum(1 for r in results if r.passed),
    total_checks=len(rubric.checks)
)
```

---

### Task 3.4: Implement Grade Storage & Appeal Tracking
**Objective:** Store grades with version history for appeals
**Depends On:** Tasks 3.1-3.3
**Deliverables:**
- Function `store_grade(grade_result: GradeResult, student_id: str, question_id: str, data_dir: str)`
- Function `get_grade_history(student_id: str, question_id: str, data_dir: str) → List[GradeResult]`
- Supports version numbering and appeal records

**Features:**
```python
# Store initial grade
store_grade(grade_result, "student_001", "q01", "/data/grades")
# → Creates: data/grades/q01/student_001/score_v1.json

# Teacher adjusts weights and recomputes
new_grade = compute_final_score_with_new_weights(...)
store_grade_appeal(new_grade, ..., version=2, reason="...")
# → Creates: data/grades/q01/student_001/appeal_v2.json

# Get full history
history = get_grade_history("student_001", "q01", "/data/grades")
# → [score_v1, appeal_v2, appeal_v3]

# Ensure only upward adjustments
for prev, next in zip(history, history[1:]):
    assert next.score >= prev.score, "Grade must not decrease"
```

---

## Phase 4: Testing & Validation (5-7 days)

### Task 4.1: Unit Tests for Individual Functions
**Objective:** Test each function in isolation
**Depends On:** Phase 3
**Deliverables:**
- `tests/test_extraction.py` - Check extraction
- `tests/test_categorization.py` - Category assignment
- `tests/test_deduplication.py` - Deduplication logic
- `tests/test_evaluation.py` - Check evaluation
- `tests/test_scoring.py` - Scoring algorithm

**Coverage:**
- Normal cases
- Edge cases (empty checks, all pass/fail, tied weights)
- Error handling (invalid inputs, LLM errors)

---

### Task 4.2: Integration Tests
**Objective:** Test full pipeline end-to-end
**Depends On:** Task 4.1
**Deliverables:**
- `tests/test_rubric_pipeline.py` - Full rubric generation
- `tests/test_grading_pipeline.py` - Full grading pipeline
- `tests/test_appeal_workflow.py` - Grade appeals and recalculation

**Scenarios:**
```python
# Scenario 1: Generate rubric for q01
rubric = generate_complete_rubric(q01, llm, config)
assert len(rubric.checks) >= 3
assert all(check.category in config['categories'] for check in rubric.checks)

# Scenario 2: Grade student answer
evaluation = grade_student_answer(student_001_answer, rubric, llm, ...)
assert 0 <= evaluation.final_score <= 10

# Scenario 3: Appeal with new weights
new_score = compute_final_score(evaluation.results, rubric, new_weights)
assert new_score >= evaluation.final_score
```

---

### Task 4.3: Sample Grading Test
**Objective:** Grade sample student answers, compare with manual assessment
**Depends On:** Phase 3
**Deliverables:**
- Grade 5 sample student answers (q01-q05, 1 per question)
- Compare LLM grades with instructor evaluation
- Document any discrepancies
- Adjust category weights if needed

**Process:**
```
For each question q01-q05:
  1. Generate rubric
  2. Extract, categorize, deduplicate checks
  3. Grade sample student answer
  4. Compare LLM score with instructor's expected score
  5. Review check evaluations for accuracy
  6. Adjust category weights if grade distribution off
```

---

### Task 4.4: Regression Testing
**Objective:** Ensure no functionality breaks with changes
**Depends On:** Task 4.3
**Deliverables:**
- Automated test suite run on each code change
- Benchmark scores (to catch unintended changes)
- Performance tests (scoring should be fast)

---

## Phase 5: Documentation & Deployment (3-5 days)

### Task 5.1: User Documentation
**Objective:** Document how to use the system
**Deliverables:**
- `docs/GRADING_USER_GUIDE.md` - How to grade students
- `docs/CONFIG_GUIDE.md` - How to configure categories and weights
- `docs/APPEAL_PROCEDURE.md` - How to handle grade appeals
- API documentation with docstrings

**Sections:**
- System overview
- Quick start guide
- Configuration reference
- Command-line options
- Troubleshooting

---

### Task 5.2: Administrator Documentation
**Objective:** Document system architecture and maintenance
**Deliverables:**
- `docs/ARCHITECTURE.md` - System design and data flow
- `docs/MAINTENANCE.md` - Adding new categories, changing weights globally
- `docs/DATA_RECOVERY.md` - How to recover from errors

---

### Task 5.3: Deployment Guide
**Objective:** Set up system for production use
**Deliverables:**
- `docs/DEPLOYMENT.md` - How to deploy system
- Setup scripts for initial configuration
- Docker configuration (optional)
- Database setup (if using)

---

## Task Dependencies

```
Phase 1:
  1.1 → 1.2 → 1.3

Phase 2:
  2.1 → 2.2 → 2.3 → 2.4 → 2.5
  (all depend on Phase 1)

Phase 3:
  3.1 → 3.2
  3.1 → 3.3
  3.3 → 3.4
  (all depend on Phase 2)

Phase 4:
  4.1 → 4.2 → 4.3 → 4.4

Phase 5:
  5.1 → 5.2 → 5.3
```

---

## Critical Success Criteria

- [ ] No hardcoded parameters (all from config or CLI)
- [ ] All grades reproducible from stored check results
- [ ] Only upward grade adjustments allowed on appeal
- [ ] Complete audit trail for every grade
- [ ] Category weights are global (same across questions)
- [ ] No double penalties (deduplication verified)
- [ ] LLM calls minimized (cached rubrics)
- [ ] Full test coverage (>80%)
- [ ] Documentation complete and clear

---

## Effort Estimate

| Phase | Tasks | Est. Hours | Notes |
|-------|-------|-----------|-------|
| 1 | 3 | 16-20 | Infrastructure setup |
| 2 | 5 | 40-50 | Rubric generation pipeline |
| 3 | 4 | 32-40 | Evaluation and scoring |
| 4 | 4 | 32-40 | Testing and validation |
| 5 | 3 | 16-20 | Documentation |
| **Total** | **19** | **136-170** | ~4-5 weeks |

---

## Parallelization Opportunities

- Phase 4 (testing) can start as soon as Phase 3 is complete
- Phase 5 (documentation) can start as soon as Phase 2 is stable
- Unit tests (4.1) can be written alongside implementation

---
