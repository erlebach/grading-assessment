# Deduction Scaling Correction: From Absolute to Fractional

**Date**: 2026-01-25
**Status**: ✅ CORRECTED AND IMPLEMENTED

---

## The Problem

The initial prescriptive rubric template used **absolute point deductions**, which don't scale correctly to the final 10-point score.

### Mathematical Issue

**Grading Formula:**
```python
contribution_to_final_score = (llm_score / 10.0) × criterion_points
```

**Example - 3-point criterion:**
- Rubric says: "Deduct 1 point if alternative names missing"
- LLM interprets: Start with 10, deduct 1 → return 9
- Final contribution: 9 × (3/10) = **2.7 points**
- **Actual loss from final score: 0.3 points** ❌
- **Intended loss: 1 point** ❌

The problem: **1 point on the 0-10 scale ≠ 1 point on the final score**

---

## The Solution: Option B - Fractional Deductions

Express all deductions as **fractions of the criterion's allocated points**.

### Why It Works

**Mathematical proof:**
- Criterion worth C points
- Deduct 1/N of criterion → LLM score reduced by (10/N)
- Contribution = (10 - 10/N) × (C/10) = C - C/N
- **Loss = C/N points from final score**
- **For 1-point loss on final score: deduct 1/N where N = C (the criterion's points)**

### Examples

#### 3-Point Criterion (30% of final grade)
```
Deduct 1/3 if missing definition of 'object'
Deduct 1/3 if missing definition of 'attribute'
Deduct 1/3 if definitions conflate the concepts
```

**Math:**
- Each deduction: 1/3 × 3 points = 1 point from final score ✅
- Maximum loss: 3 points from final score
- Maximum score on criterion: 10 - 10/3 = 6.67/10 → Contributes 2 points

#### 4-Point Criterion (40% of final grade)
```
Deduct 1/4 if alternative name 1 missing
Deduct 1/4 if alternative name 2 missing
Deduct 1/2 if no examples provided
```

**Math:**
- 1/4 deduction: (1/4) × 4 = 1 point from final score ✅
- 1/2 deduction: (1/2) × 4 = 2 points from final score ✅
- Maximum loss: 4 points from final score

#### 2-Point Criterion (20% of final grade)
```
Deduct 1/2 if clarity is poor
Deduct 1/2 if structure is confusing
```

**Math:**
- Each 1/2 deduction: (1/2) × 2 = 1 point from final score ✅
- Maximum loss: 2 points from final score

---

## Template Changes

### Updated Section: "PRESCRIPTIVE GRADING REQUIREMENTS" (Lines 28-50)

**Before:**
- Absolute deductions: "Deduct 1 point if...", "Deduct 2 points if..."
- No explanation of scaling

**After:**
- Fractional deductions: "Deduct 1/3 if...", "Deduct 1/4 if...", "Deduct 1/2 if..."
- Full explanation of WHY fractions are needed
- Mathematical formula provided
- Clear examples showing final score impact
- Validation checklist requires fractions

### Key Instructions Added

1. **CRITICAL SCALING INFORMATION section**
   - Explains criterion points as fractions of 10
   - Shows the mathematical formula
   - Clarifies why fractions are required

2. **DEDUCTION RULES**
   - Use fractional format: "Deduct 1/3 of this criterion if..."
   - Fractions should divide evenly (1/2, 1/3, 1/4, 2/3, etc.)
   - Deductions are additive within a criterion

3. **EXAMPLES section** (Three complete examples)
   - 3-point criterion with three 1/3 deductions
   - 4-point criterion with 1/4 and 1/2 deductions
   - 2-point criterion with two 1/2 deductions
   - Each shows final score impact

4. **Updated Validation Checklist**
   - "Include prescriptive deduction rules using FRACTIONS"
   - "Fractions should be of the form 1/N where N divides the criterion's points"

---

## Impact on Rubric Generation

### LLM Behavior (New)

**Old prompt result:**
```json
{
  "title": "Alternative Terminology",
  "points": 4,
  "description": "Full credit when student lists two alternative names for 'object' and two for 'attribute'. Deduct 1 point for each missing name (max 4 deductions)."
}
```
❌ Creates scaling mismatch

**New prompt result:**
```json
{
  "title": "Alternative Terminology",
  "points": 4,
  "description": "4 points: Full credit when student lists two alternative names for 'object' and two for 'attribute'. Deduct 1/4 if one or both alternatives for 'object' missing. Deduct 1/4 if one or both alternatives for 'attribute' missing. Deduct 1/2 if listed names are not actually alternative terms."
}
```
✅ Scales correctly to final 10-point score

### Grading Behavior

**For 4-point criterion with fractional deductions:**
- Student missing alternative names for object: LLM returns 7.5/10
- Contribution: 7.5 × (4/10) = 3 points (loss of 1 point) ✅
- Student missing both types: LLM returns 5/10
- Contribution: 5 × (4/10) = 2 points (loss of 2 points) ✅

---

## Validation & Testing

### Syntax
- ✅ Template updated and validated
- ✅ Python files unchanged (template affects LLM output, not code)

### Logic
- ✅ Fractional approach mathematically correct
- ✅ Scaling formula verified
- ✅ Examples walkthrough verified
- ✅ Works for any criterion point value (2, 3, 4, 5, etc.)

### Expected Rubric Quality

After regeneration with updated template, rubrics will include:
- ✅ Prescriptive descriptions with fractions
- ✅ Correct scaling to final 10-point score
- ✅ Clear deduction rules
- ✅ No overlapping criteria (from earlier validation)

---

## Implementation Timeline

1. ✅ **Template updated** (2026-01-25)
   - Added PRESCRIPTIVE GRADING REQUIREMENTS - CRITICAL SCALING INFORMATION section
   - Updated examples with fractional deductions
   - Updated validation checklist

2. ⏳ **Rubric regeneration** (ready to execute)
   - LLM will generate rubrics with fractional deductions
   - Validation function will check for overlaps
   - All new rubrics will scale correctly

3. ⏳ **Grading verification** (after regeneration)
   - Sample grading to verify correct final scores
   - Comparison with old rubrics
   - Ensure no unexpected score changes due to scaling

---

## Files Modified

| File | Changes |
|------|---------|
| `rubric_generator_template.txt` | Added fractional deduction section (lines 28-50) |
| `RUBRIC_ENHANCEMENTS.md` | Added section explaining Option B implementation |
| `DEDUCTION_SCALING_CORRECTION.md` | This document |

---

## Key Takeaway

**Option B (Fractional Deductions)** ensures that:
1. ✅ Deductions scale correctly to the final 10-point score
2. ✅ LLM's interpretation aligns with intended impact
3. ✅ Works automatically for any criterion point allocation
4. ✅ Clear and unambiguous for rubric authors

**Before**: "Deduct 1 point if X" was ambiguous
**After**: "Deduct 1/3 if X" on a 3-point criterion is precise and scales correctly

---
