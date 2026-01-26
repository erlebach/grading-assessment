# Weighted Checklist Grading System: Complete Design

**Date**: 2026-01-25
**Status**: ✅ DESIGN COMPLETE - Ready for Implementation

---

## Executive Summary

A **two-phase grading system** that separates **evaluation** (which checks pass) from **weighting** (how much each check matters). This enables:
- ✅ Elimination of double penalties via deduplication
- ✅ Objective, configurable category-based weights
- ✅ **Reproducible scoring without LLM re-invocation**
- ✅ Grade appeals and recomputation with new weights
- ✅ Audit trail and transparency
- ✅ Only upward grade adjustments (instructor responsibility)

---

## Architecture Overview

### **Phase 1: Rubric Generation & Check Extraction (One-time)**

```
Question Text
    ↓
[LLM] Generate Rubric with Dimensions
    ↓
[LLM] Extract Checks from Rubric
    ↓
[LLM] Assign Category to Each Check
    ↓
[Deduplication] Remove Duplicate Checks
    ↓
Store: Deduped Checks + Categories
```

**Output:** Permanent rubric with deduplicated checks and assigned categories

### **Phase 2: Student Evaluation & Scoring (Per student, reproducible)**

```
Student Answer
    ↓
[Evaluation] Score Each Check (0 or 1)
    ↓
Store: Check Results + Timestamp
    ↓
[Load] Category Weights from Config
    ↓
[Compute] final_score = Σ(pass_i × weight_i × category_weight_i) / Σ(weight_i × category_weight_i) × 10
    ↓
Store: Final Score + Metadata
```

**Output:** Score + complete audit trail (can be reproduced with different weights)

---

## Detailed Process

### **Step 1: Generate Rubric**

**Input:**
- Question text
- Source material
- Rubric generation prompt

**Process:**
```
LLM generates rubric with:
- 2-5 dimensions (e.g., Conceptual Understanding, Application, Clarity)
- Each dimension has description + associated points
- Dimensions are non-overlapping (enforced by prompt)
```

**Output:** `rubric_q01_raw.json`
```json
{
  "question_id": "q01",
  "dimensions": [
    {
      "dimension_id": "conceptual_understanding",
      "title": "Conceptual Understanding",
      "points": 4,
      "description": "Student correctly defines object and attribute..."
    },
    {
      "dimension_id": "alternative_terminology",
      "title": "Alternative Terminology",
      "points": 3,
      "description": "Student provides alternative names..."
    },
    ...
  ]
}
```

---

### **Step 2: Extract Checks from Rubric**

**Input:** `rubric_q01_raw.json` (dimension descriptions)

**Process:**
```
LLM parses each dimension description and extracts discrete checks:

From "Student correctly defines object and attribute with clear distinction":
  - Check: "Defines object"
  - Check: "Defines attribute"
  - Check: "Distinguishes object from attribute"

From "Student provides two alternative names for each":
  - Check: "Provides alternative names for object"
  - Check: "Provides alternative names for attribute"
```

**Output:** `rubric_q01_checks.json`
```json
{
  "question_id": "q01",
  "checks": [
    {
      "check_id": "check_001",
      "text": "Defines object",
      "source_dimension": "conceptual_understanding",
      "base_weight": 4
    },
    {
      "check_id": "check_002",
      "text": "Defines attribute",
      "source_dimension": "conceptual_understanding",
      "base_weight": 4
    },
    {
      "check_id": "check_003",
      "text": "Distinguishes object from attribute",
      "source_dimension": "conceptual_understanding",
      "base_weight": 4
    },
    {
      "check_id": "check_004",
      "text": "Provides alternative names for object",
      "source_dimension": "alternative_terminology",
      "base_weight": 3
    },
    ...
  ]
}
```

---

### **Step 3: Assign Categories to Checks**

**Input:** `rubric_q01_checks.json` (check descriptions)

**Process:**
```
LLM categorizes each check:
  "Defines object" → Semantic
  "Provides alternative names" → Semantic
  "Provides example" → Application
  "Explains usage clearly" → Clarity

Category definitions come from global config:
  Semantic (weight=1): Conceptual understanding, definitions, distinctions
  Application (weight=2): Examples, usage, practical application
  Clarity (weight=1): Presentation, clarity, structure
```

**Output:** Updated `rubric_q01_checks.json`
```json
{
  "checks": [
    {
      "check_id": "check_001",
      "text": "Defines object",
      "source_dimension": "conceptual_understanding",
      "base_weight": 4,
      "category": "semantic"
    },
    {
      "check_id": "check_002",
      "text": "Defines attribute",
      "source_dimension": "conceptual_understanding",
      "base_weight": 4,
      "category": "semantic"
    },
    ...
  ]
}
```

---

### **Step 4: Deduplicate Checks**

**Input:** `rubric_q01_checks.json` (all checks with categories)

**Process:**
```
LLM compares all pairs of checks:
  "Defines object" vs "Defines attribute" → Different checks
  "Provides alternative names for object" vs "Provides examples" → Different

If duplicate found (rare after step 3 deduplication):
  Remove the second occurrence (category weight is now deterministic)

Example of duplicate that might exist:
  "Provides alternative terminology" (from alt_terminology dimension)
  "Provides alternative names" (from conceptual dimension)
  → Duplicates, keep only one with weight from category (not dimension)
```

**Output:** `rubric_q01_deduped.json`
```json
{
  "question_id": "q01",
  "checks": [
    {
      "check_id": "check_001",
      "text": "Defines object",
      "category": "semantic",
      "base_weight": 4,
      "final_weight": null  // Will be computed during grading
    },
    ...
  ],
  "metadata": {
    "total_checks_before_dedup": 10,
    "duplicates_removed": 2,
    "total_checks_after_dedup": 8
  }
}
```

---

### **Step 5: Grade Student Answer**

**Input:**
- Student answer
- `rubric_q01_deduped.json`
- Evidence/source material

**Process:**
```
For each check, evaluate: Does student answer satisfy this check?

Evaluation method (configurable):
  Option A: LLM evaluation
    Prompt: "Does the student answer satisfy this check: [check_text]?"
    Response: Yes (1) or No (0)

  Option B: Hybrid (LLM + human review for borderline cases)

  Option C: Rubric-based (simple keyword matching)

Store result with timestamp and method used.
```

**Output:** `grade_q01_student_001.json`
```json
{
  "student_id": "student_001",
  "question_id": "q01",
  "answer_type": "less_good",
  "evaluation_results": [
    {
      "check_id": "check_001",
      "check_text": "Defines object",
      "passed": true,
      "evaluation_method": "llm",
      "evidence": "Student clearly states: 'An object is...'"
    },
    {
      "check_id": "check_002",
      "check_text": "Defines attribute",
      "passed": false,
      "evaluation_method": "llm",
      "evidence": "Student does not provide definition of attribute"
    },
    ...
  ],
  "timestamp": "2026-01-25T10:30:00Z"
}
```

**Critical:** This stores the RAW evaluation data - can be used to compute scores with any weights.

---

### **Step 6: Compute Final Score**

**Input:**
- `grade_q01_student_001.json` (check results)
- `rubric_q01_deduped.json` (check metadata)
- `category_weights.yaml` (global configuration)

**Process:**
```
Load category weights from config:
  semantic: 1
  application: 2
  clarity: 1

For each check:
  final_weight = base_weight × category_weight[check.category]

Calculate score:
  numerator = Σ (passed_i × final_weight_i)
  denominator = Σ (final_weight_i)
  score = (numerator / denominator) × 10
```

**Example:**
```
Checks with base_weight, category, and pass status:
1. "Defines object" [base:4, category:semantic(1), pass:1] → 4×1×1 = 4
2. "Defines attribute" [base:4, category:semantic(1), pass:0] → 4×1×0 = 0
3. "Distinguish object/attr" [base:4, category:semantic(1), pass:1] → 4×1×1 = 4
4. "Alt names object" [base:3, category:semantic(1), pass:0] → 3×1×0 = 0
5. "Alt names attribute" [base:3, category:semantic(1), pass:0] → 3×1×0 = 0
6. "Examples" [base:2, category:application(2), pass:1] → 2×2×1 = 4
7. "Clear explanation" [base:1, category:clarity(1), pass:1] → 1×1×1 = 1

numerator = 4 + 0 + 4 + 0 + 0 + 4 + 1 = 13
denominator = 4 + 4 + 4 + 3 + 3 + 4 + 1 = 23

score = (13 / 23) × 10 = 5.65/10
```

**Output:** `grade_q01_student_001_final.json`
```json
{
  "student_id": "student_001",
  "question_id": "q01",
  "final_score": 5.65,
  "max_score": 10,
  "calculation": {
    "numerator": 13,
    "denominator": 23,
    "passes": 4,
    "total_checks": 7
  },
  "category_weights": {
    "semantic": 1,
    "application": 2,
    "clarity": 1
  }
}
```

---

## Grade Appeals & Recalculation

### **Scenario: Student Disputes Grade**

**Step 1:** Instructor reviews evaluation results
```
Stored in: grade_q01_student_001.json

"Student says they DID define attribute. Let me check..."
→ Check stored evidence and re-evaluate
→ Agree or disagree with original evaluation
```

**Step 2:** If evaluation stands but student disputes weight allocation
```
"OK, they didn't define attribute. But that should be worth less.
Maybe 'clarity' is more important than I thought."

Change weights in config:
  semantic: 1
  application: 1.5  (reduced from 2)
  clarity: 2        (increased from 1)
```

**Step 3:** Recompute score
```
Re-run scoring algorithm with new weights:
  New score = (13 / 19.5) × 10 = 6.67/10

NEW SCORE IS HIGHER ✓ (student happy, no complaint)
```

**Step 4:** Store new calculation
```
grade_q01_student_001_appeal_v2.json
(stores new weights and new score)
```

### **Constraint: Only Upward Adjustments**

```
Original score: 5.65
After weight adjustment: 6.67 ✓ (increase allowed)
After weight adjustment: 4.20 ✗ (FORBIDDEN - would require instructor explanation)

This prevents:
- Grade inflation on appeal
- Unfair comparison with other students
- Instructor accountability
```

---

## Configuration: Category Weights

**File:** `config/grading_categories.yaml`

```yaml
# Global category weights for all questions
# These apply to ALL checks categorized with these categories
# Only the ratio matters; absolute values are normalized during scoring

categories:
  semantic:
    weight: 1
    description: >
      Conceptual understanding, definitions, distinctions.
      "Does student understand the core concepts?"
    examples:
      - "Defines object"
      - "Distinguishes object from attribute"
      - "Explains relationship"

  application:
    weight: 2
    description: >
      Practical application, examples, usage.
      "Can student apply knowledge in context?"
    examples:
      - "Provides example"
      - "Applies concept to data"
      - "Shows practical usage"

  clarity:
    weight: 1
    description: >
      Presentation, clarity, organization.
      "Is the answer clear and well-structured?"
    examples:
      - "Explains clearly"
      - "Organized structure"
      - "Uses appropriate terminology"

# Constraints on rubric generation
checks:
  min_checks_per_question: 3
  max_checks_per_question: 15
  max_checks_per_dimension: 4
```

**CLI Override:**
```bash
python grader.py \
  --question-id q01 \
  --student-id student_001 \
  --category-weights semantic:1 application:3 clarity:1

(This overrides config values for this run)
```

---

## Data Storage & Auditability

### **Stored Artifacts (Never Delete)**

```
Per question:
  rubric_q01_raw.json           (LLM-generated rubric)
  rubric_q01_checks.json        (extracted checks)
  rubric_q01_deduped.json       (after deduplication)

Per student answer:
  grade_q01_student_001.json    (evaluation results - RAW)
  grade_q01_student_001_final.json (final score - COMPUTED)
  grade_q01_student_001_appeal_v2.json (appeal v2, if applicable)
```

### **Why This Matters**

```
Audit trail:
  Q: "Why did student get 5.65?"
  A: "Because category weights were (S:1, A:2, C:1) and student passed 4/7 checks"

Reproducibility:
  Q: "Can you change weights and recalculate?"
  A: "Yes, re-run scorer with new weights, all grades recompute in seconds"

Transparency:
  Q: "What did the student get wrong?"
  A: "Here's the check they failed: [check_text] with evidence: [evidence]"
```

---

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ SETUP (One-time per question)                                   │
├─────────────────────────────────────────────────────────────────┤
│ 1. Generate rubric (LLM)                                         │
│ 2. Extract checks (LLM)                                          │
│ 3. Assign categories (LLM)                                       │
│ 4. Deduplicate (LLM)                                             │
│ 5. Store rubric + checks permanently                             │
│ 6. Manual review of checks (human, optional)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ GRADING (Per student, reproducible)                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Evaluate each check (LLM or human)                            │
│ 2. Store evaluation results (with evidence)                      │
│ 3. Load category weights from config                             │
│ 4. Compute final score (simple math)                             │
│ 5. Store final score + calculation details                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ APPEALS & RECALCULATION (On demand)                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Review stored evaluation results                              │
│ 2. If needed: adjust category weights in config                  │
│ 3. Re-run scoring algorithm (uses stored evaluation data)        │
│ 4. New score can only increase or stay same                      │
│ 5. Store new calculation with version number                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Strengths of This Approach

✅ **Eliminates double penalties:** Deduplication is more reliable than overlap validation
✅ **Objective weighting:** Category weights are explicit and global
✅ **Reproducible:** All scores can be recomputed without LLM using stored data
✅ **Auditable:** Complete audit trail of decisions and evidence
✅ **Fair:** Only upward grade adjustments prevent grade inflation
✅ **Flexible:** Weights can be adjusted per appeal without re-evaluating
✅ **Instructor accountability:** If rubric/weights were wrong, that's on the instructor
✅ **Transparent:** Check pass/fail and evidence stored explicitly
✅ **Configurable:** No hardcoded parameters, everything from config or CLI

---

## Remaining Risks & Mitigations

### **Risk 1: Check Extraction Inconsistency**
- **Issue:** LLM might extract different granularity across questions
- **Mitigation:** Provide examples in prompt; manually review checks; standardize via category definitions
- **Severity:** Low (affects readability, not scoring)

### **Risk 2: Category Assignment Ambiguity**
- **Issue:** "Provides example" - is that Application or Clarity?
- **Mitigation:** Clear category definitions with examples in config; LLM given definitions
- **Severity:** Medium (affects weighting, but bounded by weight ratio)

### **Risk 3: Binary Pass/Fail Loses Nuance**
- **Issue:** "Mostly correct" answer marked as fail
- **Mitigation:** Define pass criteria carefully in grading prompt; use rubric-based checks
- **Severity:** Medium (but acceptable for objective grading)

### **Risk 4: Check Evaluation Reliability**
- **Issue:** LLM might incorrectly evaluate checks
- **Mitigation:** Use hybrid (LLM + human review for edge cases); store evidence for audit
- **Severity:** Medium (same as traditional rubric-based grading)

### **Risk 5: Category Weight Arbitrariness**
- **Issue:** No principled way to choose 1:2 vs 2:3 ratio
- **Mitigation:** Instructor chooses; can adjust on appeal if students agree ratio was wrong
- **Severity:** Low (only affects grade magnitude, not consistency)

---

## Advantages Over Traditional Approaches

| Aspect | Traditional | Weighted Checklist |
|--------|-------------|-------------------|
| **Double penalties** | Can occur | Eliminated by deduplication |
| **Reproducibility** | Hard (LLM involved) | Easy (stored check results + math) |
| **Auditability** | Limited | Complete audit trail |
| **Recalculation** | Must re-grade | Use stored results, just reweight |
| **Grade appeals** | Subjective | Objective (weight adjustment) |
| **Weight changes** | Requires re-grading | Instant recalculation |
| **Transparency** | Implicit in rubric | Explicit check results |
| **Fairness** | Subjective | Objective criteria |
| **Instructor accountability** | Limited | High (weights are explicit) |

---

## Summary

This system provides **objective, auditable, reproducible grading** that:
1. Eliminates double penalties via explicit deduplication
2. Separates evaluation (checks) from weighting (category importance)
3. Enables grade recalculation without LLM re-invocation
4. Provides complete audit trails for any grade
5. Allows fair grade appeals with upward-only adjustments
6. Puts responsibility on instructor for weight selection
7. Is fully configurable with no hardcoded values

The key insight: **Store the raw evaluation data (which checks passed), not just the final score.** This enables auditability, reproducibility, and fairness.

---
