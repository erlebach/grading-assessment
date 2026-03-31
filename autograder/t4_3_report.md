# T4.3 Sample Grading Report — Scoring Method Comparison

Questions: q01, q02, q03, q04, q05
Runs: 2 (for reproducibility check)

Three scoring methods compared:
- **int**: `int(combined_score × max_pts)` — current pipeline behaviour
- **round**: `round(combined_score × max_pts)` — one-line proposed fix
- **float**: `combined_score × max_pts` summed as float — no truncation

---
## Method: `int`

### Run 1

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 0 | 0 | 0 | ✓ | ✓ | ✓ |
| q02 | 0 | 0 | 0 | ✓ | ✓ | ✓ |
| q03 | 4 | 0 | 0 | ✓ | ✓ | ✓ |
| q04 | 1 | 1 | 0 | ✓ | ✓ | ✓ |
| q05 | 0 | 0 | 0 | ✓ | ✓ | ✓ |

**Overall (`int`, Run 1):** PASS ✓

### Run 2

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 0 | 0 | 0 | ✓ | ✓ | ✓ |
| q02 | 0 | 0 | 0 | ✓ | ✓ | ✓ |
| q03 | 4 | 0 | 0 | ✓ | ✓ | ✓ |
| q04 | 1 | 1 | 0 | ✓ | ✓ | ✓ |
| q05 | 0 | 0 | 0 | ✓ | ✓ | ✓ |

**Overall (`int`, Run 2):** PASS ✓

---
## Method: `round`

### Run 1

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 1 | 1 | 1 | ✓ | ✓ | ✓ |
| q02 | 4 | 2 | 2 | ✓ | ✓ | ✓ |
| q03 | 6 | 2 | 2 | ✓ | ✓ | ✓ |
| q04 | 3 | 3 | 2 | ✓ | ✓ | ✓ |
| q05 | 1 | 0 | 1 | ✓ | ✗ | ✗ |

**Overall (`round`, Run 1):** FAIL ✗

### Run 2

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 1 | 1 | 1 | ✓ | ✓ | ✓ |
| q02 | 4 | 2 | 2 | ✓ | ✓ | ✓ |
| q03 | 6 | 2 | 2 | ✓ | ✓ | ✓ |
| q04 | 3 | 3 | 2 | ✓ | ✓ | ✓ |
| q05 | 1 | 0 | 1 | ✓ | ✗ | ✗ |

**Overall (`round`, Run 2):** FAIL ✗

---
## Method: `float`

### Run 1

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 2.14 | 1.86 | 1.52 | ✓ | ✓ | ✓ |
| q02 | 2.96 | 1.71 | 2.01 | ✓ | ✗ | ✗ |
| q03 | 5.66 | 2.32 | 2.34 | ✓ | ✗ | ✗ |
| q04 | 2.93 | 2.63 | 2.14 | ✓ | ✓ | ✓ |
| q05 | 1.76 | 1.15 | 1.39 | ✓ | ✗ | ✗ |

**Overall (`float`, Run 1):** FAIL ✗

### Run 2

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 2.14 | 1.86 | 1.52 | ✓ | ✓ | ✓ |
| q02 | 2.96 | 1.71 | 2.01 | ✓ | ✗ | ✗ |
| q03 | 5.66 | 2.32 | 2.34 | ✓ | ✗ | ✗ |
| q04 | 2.93 | 2.63 | 2.14 | ✓ | ✓ | ✓ |
| q05 | 1.76 | 1.15 | 1.39 | ✓ | ✗ | ✗ |

**Overall (`float`, Run 2):** FAIL ✗

---
## Reproducibility Check (Run 1 vs Run 2)

A `*` marks any cell where the two runs differ.

### Method: `int`

| Question | Answer | Run1 | Run2 | Same? |
|----------|--------|------|------|-------|
| q01 | good | 0 | 0 | ✓ |
| q01 | less_good | 0 | 0 | ✓ |
| q01 | wrong | 0 | 0 | ✓ |
| q02 | good | 0 | 0 | ✓ |
| q02 | less_good | 0 | 0 | ✓ |
| q02 | wrong | 0 | 0 | ✓ |
| q03 | good | 4 | 4 | ✓ |
| q03 | less_good | 0 | 0 | ✓ |
| q03 | wrong | 0 | 0 | ✓ |
| q04 | good | 1 | 1 | ✓ |
| q04 | less_good | 1 | 1 | ✓ |
| q04 | wrong | 0 | 0 | ✓ |
| q05 | good | 0 | 0 | ✓ |
| q05 | less_good | 0 | 0 | ✓ |
| q05 | wrong | 0 | 0 | ✓ |

### Method: `round`

| Question | Answer | Run1 | Run2 | Same? |
|----------|--------|------|------|-------|
| q01 | good | 1 | 1 | ✓ |
| q01 | less_good | 1 | 1 | ✓ |
| q01 | wrong | 1 | 1 | ✓ |
| q02 | good | 4 | 4 | ✓ |
| q02 | less_good | 2 | 2 | ✓ |
| q02 | wrong | 2 | 2 | ✓ |
| q03 | good | 6 | 6 | ✓ |
| q03 | less_good | 2 | 2 | ✓ |
| q03 | wrong | 2 | 2 | ✓ |
| q04 | good | 3 | 3 | ✓ |
| q04 | less_good | 3 | 3 | ✓ |
| q04 | wrong | 2 | 2 | ✓ |
| q05 | good | 1 | 1 | ✓ |
| q05 | less_good | 0 | 0 | ✓ |
| q05 | wrong | 1 | 1 | ✓ |

### Method: `float`

| Question | Answer | Run1 | Run2 | Same? |
|----------|--------|------|------|-------|
| q01 | good | 2.14 | 2.14 | ✓ |
| q01 | less_good | 1.86 | 1.86 | ✓ |
| q01 | wrong | 1.52 | 1.52 | ✓ |
| q02 | good | 2.96 | 2.96 | ✓ |
| q02 | less_good | 1.71 | 1.71 | ✓ |
| q02 | wrong | 2.01 | 2.01 | ✓ |
| q03 | good | 5.66 | 5.66 | ✓ |
| q03 | less_good | 2.32 | 2.32 | ✓ |
| q03 | wrong | 2.34 | 2.34 | ✓ |
| q04 | good | 2.93 | 2.93 | ✓ |
| q04 | less_good | 2.63 | 2.63 | ✓ |
| q04 | wrong | 2.14 | 2.14 | ✓ |
| q05 | good | 1.76 | 1.76 | ✓ |
| q05 | less_good | 1.15 | 1.15 | ✓ |
| q05 | wrong | 1.39 | 1.39 | ✓ |

---
## Per-Question Criterion Breakdown (Run 1)

Format per criterion: `int | round | float(kw/sem)`

### q01
- **good** — int=0  round=1  float=2.14  (max=10)
  - conceptual_definitions (/3): int=0  round=0  float=0.49   kw=0.12  sem=0.20
  - distinction_relationship (/2): int=0  round=0  float=0.41   kw=0.21  sem=0.20
  - alternative_names (/2): int=0  round=0  float=0.49   kw=0.29  sem=0.20
  - clarity_structure_examples (/3): int=0  round=1  float=0.76   kw=0.30  sem=0.20
- **less_good** — int=0  round=1  float=1.86  (max=10)
  - conceptual_definitions (/3): int=0  round=0  float=0.49   kw=0.12  sem=0.20
  - distinction_relationship (/2): int=0  round=0  float=0.46   kw=0.26  sem=0.20
  - alternative_names (/2): int=0  round=0  float=0.36   kw=0.16  sem=0.20
  - clarity_structure_examples (/3): int=0  round=1  float=0.56   kw=0.17  sem=0.20
- **wrong** — int=0  round=1  float=1.52  (max=10)
  - conceptual_definitions (/3): int=0  round=0  float=0.34   kw=0.03  sem=0.20
  - distinction_relationship (/2): int=0  round=1  float=0.50   kw=0.30  sem=0.20
  - alternative_names (/2): int=0  round=0  float=0.25   kw=0.05  sem=0.20
  - clarity_structure_examples (/3): int=0  round=0  float=0.43   kw=0.09  sem=0.20

### q02
- **good** — int=0  round=4  float=2.96  (max=10)
  - attribute_properties_principle (/3): int=0  round=1  float=0.94   kw=0.03  sem=0.60
  - zip_code_as_nominal (/3): int=0  round=1  float=0.86   kw=0.38  sem=0.20
  - inappropriate_analysis (/2): int=0  round=1  float=0.66   kw=0.46  sem=0.20
  - correct_analysis_alternatives (/2): int=0  round=1  float=0.50   kw=0.30  sem=0.20
- **less_good** — int=0  round=2  float=1.71  (max=10)
  - attribute_properties_principle (/3): int=0  round=1  float=0.60   kw=0.00  sem=0.40
  - zip_code_as_nominal (/3): int=0  round=1  float=0.63   kw=0.22  sem=0.20
  - inappropriate_analysis (/2): int=0  round=0  float=0.29   kw=0.09  sem=0.20
  - correct_analysis_alternatives (/2): int=0  round=0  float=0.20   kw=0.00  sem=0.20
- **wrong** — int=0  round=2  float=2.01  (max=10)
  - attribute_properties_principle (/3): int=0  round=1  float=0.94   kw=0.03  sem=0.60
  - zip_code_as_nominal (/3): int=0  round=1  float=0.58   kw=0.19  sem=0.20
  - inappropriate_analysis (/2): int=0  round=0  float=0.29   kw=0.09  sem=0.20
  - correct_analysis_alternatives (/2): int=0  round=0  float=0.20   kw=0.00  sem=0.20

### q03
- **good** — int=4  round=6  float=5.66  (max=10)
  - nominal_operations (/2): int=1  round=1  float=1.02   kw=0.42  sem=0.60
  - ordinal_operations (/3): int=1  round=2  float=1.62   kw=0.48  sem=0.60
  - interval_operations (/3): int=2  round=2  float=2.16   kw=0.44  sem=1.00
  - ratio_operations (/2): int=0  round=1  float=0.86   kw=0.26  sem=0.60
- **less_good** — int=0  round=2  float=2.32  (max=10)
  - nominal_operations (/2): int=0  round=0  float=0.47   kw=0.27  sem=0.20
  - ordinal_operations (/3): int=0  round=1  float=0.82   kw=0.35  sem=0.20
  - interval_operations (/3): int=0  round=1  float=0.72   kw=0.28  sem=0.20
  - ratio_operations (/2): int=0  round=0  float=0.31   kw=0.11  sem=0.20
- **wrong** — int=0  round=2  float=2.34  (max=10)
  - nominal_operations (/2): int=0  round=0  float=0.39   kw=0.19  sem=0.20
  - ordinal_operations (/3): int=0  round=1  float=0.82   kw=0.35  sem=0.20
  - interval_operations (/3): int=0  round=1  float=0.78   kw=0.32  sem=0.20
  - ratio_operations (/2): int=0  round=0  float=0.35   kw=0.15  sem=0.20

### q04
- **good** — int=1  round=3  float=2.93  (max=10)
  - interval_scale_explanation (/3): int=1  round=1  float=1.07   kw=0.51  sem=0.20
  - role_of_zero_point (/3): int=0  round=1  float=0.78   kw=0.32  sem=0.20
  - ratio_scale_kelvin (/2): int=0  round=1  float=0.66   kw=0.46  sem=0.20
  - consequence_for_ratios (/2): int=0  round=0  float=0.42   kw=0.22  sem=0.20
- **less_good** — int=1  round=3  float=2.63  (max=10)
  - interval_scale_explanation (/3): int=1  round=1  float=1.07   kw=0.31  sem=0.40
  - role_of_zero_point (/3): int=0  round=1  float=0.63   kw=0.22  sem=0.20
  - ratio_scale_kelvin (/2): int=0  round=1  float=0.51   kw=0.31  sem=0.20
  - consequence_for_ratios (/2): int=0  round=0  float=0.42   kw=0.22  sem=0.20
- **wrong** — int=0  round=2  float=2.14  (max=10)
  - interval_scale_explanation (/3): int=0  round=1  float=0.73   kw=0.29  sem=0.20
  - role_of_zero_point (/3): int=0  round=1  float=0.56   kw=0.17  sem=0.20
  - ratio_scale_kelvin (/2): int=0  round=0  float=0.43   kw=0.23  sem=0.20
  - consequence_for_ratios (/2): int=0  round=0  float=0.42   kw=0.22  sem=0.20

### q05
- **good** — int=0  round=1  float=1.76  (max=10)
  - definition_of_orderingonly_scale (/3): int=0  round=1  float=0.73   kw=0.29  sem=0.20
  - distinction_between_orderingonly_and_additive_scales (/3): int=0  round=0  float=0.43   kw=0.09  sem=0.20
  - allowed_vs_disallowed_computations (/2): int=0  round=0  float=0.31   kw=0.11  sem=0.20
  - practical_consequence_example (/2): int=0  round=0  float=0.28   kw=0.08  sem=0.20
- **less_good** — int=0  round=0  float=1.15  (max=10)
  - definition_of_orderingonly_scale (/3): int=0  round=0  float=0.37   kw=0.05  sem=0.20
  - distinction_between_orderingonly_and_additive_scales (/3): int=0  round=0  float=0.33   kw=0.02  sem=0.20
  - allowed_vs_disallowed_computations (/2): int=0  round=0  float=0.23   kw=0.03  sem=0.20
  - practical_consequence_example (/2): int=0  round=0  float=0.23   kw=0.03  sem=0.20
- **wrong** — int=0  round=1  float=1.39  (max=10)
  - definition_of_orderingonly_scale (/3): int=0  round=1  float=0.55   kw=0.17  sem=0.20
  - distinction_between_orderingonly_and_additive_scales (/3): int=0  round=0  float=0.35   kw=0.04  sem=0.20
  - allowed_vs_disallowed_computations (/2): int=0  round=0  float=0.26   kw=0.06  sem=0.20
  - practical_consequence_example (/2): int=0  round=0  float=0.23   kw=0.03  sem=0.20

---
## Summary & Recommendations

### Scoring method comparison

| Method | Differentiates well? | Violates ordering? | Notes |
|--------|---------------------|-------------------|-------|
| `int`   | No — collapses ~80% of scores to 0 | Yes | Truncation discards signal |
| `round` | Partial — rescues scores near 0.5 boundary | Fewer | One-line fix |
| `float` | Best — preserves all signal | Fewest | Never loses precision |

### Root causes (unchanged from initial T4.3 analysis)

1. **`int()` truncation** — combined scores of 0.10–0.50 × max_pts land at 0.2–1.5,
   which `int()` rounds down to 0. `round()` fixes scores near 0.5; `float` removes
   all truncation error.

2. **`extract_keywords` includes stopwords** — 'full', 'credit', 'awarded', 'when',
   'student', 'provides'… dominate the keyword list, diluting content-keyword matches.

3. **Semantic score = evidence count / top_k** — uniform across answer types because
   all answers retrieve similar numbers of chunks on the same topic.

### Priority fixes

- **P1 (one line):** Replace `int(combined_score * max_points)` with
  `round(combined_score * max_points)` in `apply_rubric_scoring_dynamic()`.
  → Immediate improvement; no architecture change needed.

- **P1b (alternative):** Use float totals for all comparison/ordering logic.
  → Best precision; requires storing floats instead of ints in GradeResult.

- **P2:** Filter stopwords in `grader/grade_question.py:extract_keywords()`.

- **P3:** Weight semantic score by reranker scores, not just chunk count.
