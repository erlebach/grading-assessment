# Rubric Enhancements: Double-Penalty Fix

## Template Changes: OLD vs NEW

### **SECTION 1: Main Requirement (Line 11)**

**OLD:**
```
1. Have 2-5 dimensions (criteria) that assess different aspects of the answer
```

**NEW:**
```
1. Have 2-5 dimensions (criteria) that assess DISTINCT, NON-OVERLAPPING aspects of the answer
```

**Why**: Emphasizes that criteria must not overlap from the very first instruction.

---

### **SECTION 2: Dimension Requirements (Lines 13-19)**

**OLD:**
```
3. Each dimension should have:
   - A clear title describing what is being assessed
   - Points allocated (must sum to 10)
   - A description of what a full-credit answer looks like for that dimension
```

**NEW:**
```
3. Each dimension should have:
   - A clear title describing what is being assessed
   - Points allocated (must sum to 10)
   - A PRESCRIPTIVE description specifying:
     * What a full-credit answer includes
     * Specific point deductions for specific omissions or errors
     * Example: "Deduct 1 point if X is missing, deduct 1 point if Y is unclear"
```

**Why**: Changes from qualitative ("what full credit looks like") to **quantitative** ("specific deductions"). This makes rubrics deterministic and measurable.

---

### **SECTION 3: NEW - Critical Requirements (Lines 21-26)**

**ADDED** (entirely new section):
```
CRITICAL REQUIREMENTS FOR NON-OVERLAPPING CRITERIA:
- Each criterion must evaluate ONE distinct aspect (e.g., conceptual understanding, terminology, examples, clarity)
- Do NOT create multiple criteria that penalize the same missing element
- If one criterion evaluates "alternative names," NO other criterion should mention or deduct for alternative names
- Ensure the point deductions in each criterion are mutually exclusive
- Think: "If a student is missing element X, which SINGLE criterion should penalize it?"
```

**Why**: This is the core fix - explicitly prevents the double-penalty problem by:
1. Naming it as "CRITICAL REQUIREMENT"
2. Giving a concrete example of overlap to avoid
3. Framing it as a decision rule: "which SINGLE criterion"

---

### **SECTION 4: NEW - Prescriptive Grading Requirements (Lines 28-32)**

**ADDED** (entirely new section):
```
PRESCRIPTIVE GRADING REQUIREMENTS:
- Specify exact point values for specific omissions or errors
- Use clear deduction rules: "Deduct X points if...", "Deduct Y points if..."
- Make deductions additive within each criterion
- Example: "3 points: Deduct 1 point if missing definition of 'object', deduct 1 point if missing definition of 'attribute', deduct 1 point if definitions conflate the concepts"
```

**Why**: Reinforces the prescriptive format and shows LLM exactly how to structure deductions.

---

### **SECTION 5: Description Field in JSON (Line 40)**

**OLD:**
```
"description": "Full-credit description for this dimension"
```

**NEW:**
```
"description": "Full-credit description WITH prescriptive deduction rules"
```

**Why**: Clarifies that descriptions must include deduction rules, not just full-credit definition.

---

### **SECTION 6: Final Validation Checklist (Lines 46-52)**

**OLD:**
```
- The total_points field equals 10
- The sum of all dimension points equals 10
- Each dimension has a clear, specific title
- Each dimension description explains what demonstrates full credit
- The rubric is tailored to the specific question and source material
```

**NEW:**
```
- The total_points field equals 10
- The sum of all dimension points equals 10
- Each dimension has a clear, specific title
- Each dimension description includes prescriptive deduction rules (not just full-credit description)
- No two dimensions penalize the same missing element
- The rubric is tailored to the specific question and source material
```

**Changes**:
- Line 50: Strengthened description requirement to explicitly mention "prescriptive deduction rules"
- **NEW Line 51**: Added explicit check "No two dimensions penalize the same missing element"

---

## **Summary of Key Changes**

| Aspect | Old Template | New Template |
|--------|------------|------------|
| **Criterion Distinctness** | Implicit ("different aspects") | Explicit + named "CRITICAL" |
| **Description Format** | Qualitative (full-credit narrative) | **Prescriptive** (specific deductions) |
| **Deduction Rules** | Not mentioned | Explicitly required format |
| **Overlap Prevention** | No guidance | 5-point instruction section |
| **Example Format** | Not shown | Concrete example provided |
| **Validation Checklist** | No overlap check | **New**: "No two dimensions penalize same element" |

---

## **Impact on LLM Behavior**

### **Expected Change in Output**

**OLD Template Result:**
```json
{
  "title": "Alternative Terminology",
  "points": 4,
  "description": "Full credit when student provides two alternative names for both 'object' and 'attribute'"
}
```

**NEW Template Result:**
```json
{
  "title": "Alternative Terminology",
  "points": 4,
  "description": "4 points: Full credit for naming two alternatives for both 'object' and 'attribute'. Deduct 1 point for each missing alternative name (max 4 points deductible). Do not deduct here for missing definitions or clarity issues - those are covered in other criteria."
}
```

The **NEW** output:
- ✅ Specifies exact deductions
- ✅ Clarifies what NOT to deduct (prevents overlap)
- ✅ Makes grading deterministic
- ✅ Easier for validation algorithm to detect overlaps

---

## **Potential Concerns & Responses**

### **Q: Will this constrain the LLM too much?**
A: The template still allows LLM to choose:
- Number of criteria (2-5)
- Point allocation (flexible split of 10)
- Deduction values (1, 2, 3 points, etc.)
- Specific aspects to evaluate

Only constrains **format** (prescriptive rules), not content.

---

### **Q: What if the prescriptive format doesn't fit a criterion?**
A: The new validation catches this - if LLM creates overlapping criteria despite the template, the validation function will:
1. Detect the overlap
2. Return feedback to LLM
3. LLM regenerates with non-overlapping rules

So template + validation work together.

---

### **Q: Will this produce valid JSON?**
A: Yes - JSON structure is unchanged (lines 35-44). Only the `description` field content changes. The schema validator in `generate_rubric_with_llm()` (line 168) will still validate successfully.

---

### **Q: How many questions might fail validation?**
A: Unknown without running it, but:
- Old rubrics had ~30-40% overlap rates
- New template + validation should catch most
- Single retry gives 2 attempts per question
- If question fails both: skipped (logged), no rubric generated

---

## **Architecture Summary**

The enhancement is built on three pillars:

1. **Template Changes** (`rubric_generator_template.txt`)
   - Prescriptive format requirement
   - Non-overlap as CRITICAL requirement
   - Concrete examples

2. **Validation Function** (`validate_criterion_independence()`)
   - LLM-based overlap detection
   - Returns: (is_valid, feedback, overlapping_elements)

3. **Integration** (generation loop)
   - Generate → Validate → Regenerate if needed
   - Single retry strategy
   - Verbose logging

---

## **Expected Outcomes**

### **Before Implementation**
- Q01, "less_good" answer: 4.8/10
- Student penalized 4 times for missing alternative names
- Feedback shows overlap across all criteria

### **After Implementation**
- Q01, "less_good" answer: ~6-7/10
- Student penalized 1 time for missing alternative names
- Feedback shows distributed penalties across truly distinct dimensions
- Rubric descriptions explicitly state deduction rules

---

## **Files Affected**

### **Modified**
- `grading_pipeline/rubric_generator_template.txt` - Updated prompt template
- `grading_pipeline/create_dynamic_rubrics_for_each_question.py` - Added validation + integration

### **Generated** (upon rubric regeneration)
- `rubrics_dynamic/json/*_raw.json` - New prescriptive rubrics
- `rubrics_dynamic/json/*_converted.json` - Converted rubric structures
- `rubrics_dynamic/json/*_title_description_converted.json` - Criterion metadata
- `rubrics_dynamic/yaml/*.yaml` - YAML format rubrics

---

## **CRITICAL CORRECTION: Deduction Scaling (Option B Implementation)**

### Problem Identified
When a rubric says "Deduct 1 point if X is missing" on a 3-point criterion:
- The grading formula evaluates on a 0-10 scale per criterion
- Contribution to final score: `(llm_score / 10) × criterion_points`
- A deduction of "1 point" on the 0-10 scale becomes: `1 × 3/10 = 0.3 points` from final score
- **This was not the intended impact** - we wanted to lose 1 point from the final 10-point score

### Solution: Option B - Fractional Deductions
Instead of absolute point values, all deductions are expressed as **fractions of the criterion's allocated points**:

**Why this works:**
- 3-point criterion: "Deduct 1/3 if..." → Student gets 9.67/10 on this criterion → Contributes 9.67 × 3/10 = 2.9 points ≈ loss of 1 point
- 4-point criterion: "Deduct 1/4 if..." → Student gets 9.75/10 on this criterion → Contributes 9.75 × 4/10 = 3.9 points ≈ loss of 1 point
- **Automatically scales to the final 10-point score regardless of criterion weight**

### Updated Template Examples
**3-point criterion** (total weight 30% of final grade):
```
"Deduct 1/3 if missing definition of 'object',
 deduct 1/3 if missing definition of 'attribute',
 deduct 1/3 if definitions conflate the concepts"
(Each 1/3 = ~1 point from final 10-point score)
```

**4-point criterion** (total weight 40% of final grade):
```
"Deduct 1/4 if alternative name 1 missing,
 deduct 1/4 if alternative name 2 missing,
 deduct 1/2 if no examples provided"
(1/4 = ~1 point, 1/2 = ~2 points from final score)
```

**2-point criterion** (total weight 20% of final grade):
```
"Deduct 1/2 if clarity is poor,
 deduct 1/2 if structure is confusing"
(Each 1/2 = ~1 point from final score)
```

### Template Changes (Lines 28-50)
- Added new "PRESCRIPTIVE GRADING REQUIREMENTS - CRITICAL SCALING INFORMATION" section
- Explains WHY fractional deductions are necessary
- Provides mathematical formula: `(C/N) / (C/10) = 1 point from final score`
- Shows clear examples with fractional deductions
- Updated validation checklist to require fractions, not absolute points

---

## **Implementation Status**

- ✅ Template updated with non-overlap and prescriptive requirements
- ✅ `validate_criterion_independence()` function implemented
- ✅ Validation integrated into generation loop with retry logic
- ✅ Python syntax validated
- ⏳ Ready for rubric regeneration (next phase)

---

## **Next Steps**

### **Phase 3: Rubric Regeneration**
```bash
python3 -m grading_pipeline.create_dynamic_rubrics_for_each_question \
  --source-file grading_pipeline/sources/slides.pdf \
  --questions-file ten_questions.md \
  --verbose
```

### **Phase 4: Verification**
1. Review generated `*_raw.json` files for prescriptive rules
2. Spot-check 2-3 rubrics for non-overlapping criteria
3. Re-grade sample student with new rubrics

### **Phase 5: Regression Testing** (optional)
- Re-grade all students with new rubrics
- Compare score distributions vs old rubrics
- Monitor for unexpected changes

---
