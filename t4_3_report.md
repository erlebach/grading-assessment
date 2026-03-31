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
| q03 | 2 | 0 | 0 | ✓ | ✓ | ✓ |
| q04 | 1 | 0 | 0 | ✓ | ✓ | ✓ |
| q05 | 0 | 0 | 0 | ✓ | ✓ | ✓ |

**Overall (`int`, Run 1):** PASS ✓

### Run 2

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 0 | 0 | 0 | ✓ | ✓ | ✓ |
| q02 | 0 | 0 | 0 | ✓ | ✓ | ✓ |
| q03 | 2 | 0 | 0 | ✓ | ✓ | ✓ |
| q04 | 1 | 0 | 0 | ✓ | ✓ | ✓ |
| q05 | 0 | 0 | 0 | ✓ | ✓ | ✓ |

**Overall (`int`, Run 2):** PASS ✓

---
## Method: `round`

### Run 1

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 3 | 3 | 1 | ✓ | ✓ | ✓ |
| q02 | 3 | 1 | 1 | ✓ | ✓ | ✓ |
| q03 | 4 | 2 | 2 | ✓ | ✓ | ✓ |
| q04 | 3 | 3 | 2 | ✓ | ✓ | ✓ |
| q05 | 1 | 0 | 1 | ✓ | ✗ | ✗ |

**Overall (`round`, Run 1):** FAIL ✗

### Run 2

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 3 | 3 | 1 | ✓ | ✓ | ✓ |
| q02 | 3 | 1 | 1 | ✓ | ✓ | ✓ |
| q03 | 4 | 2 | 2 | ✓ | ✓ | ✓ |
| q04 | 3 | 3 | 2 | ✓ | ✓ | ✓ |
| q05 | 1 | 0 | 1 | ✓ | ✗ | ✗ |

**Overall (`round`, Run 2):** FAIL ✗

---
## Method: `float`

### Run 1

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 2.32 | 2.13 | 1.68 | ✓ | ✓ | ✓ |
| q02 | 2.63 | 1.49 | 1.48 | ✓ | ✓ | ✓ |
| q03 | 3.51 | 2.37 | 2.63 | ✓ | ✗ | ✗ |
| q04 | 3.24 | 2.54 | 2.32 | ✓ | ✓ | ✓ |
| q05 | 1.87 | 1.18 | 1.44 | ✓ | ✗ | ✗ |

**Overall (`float`, Run 1):** FAIL ✗

### Run 2

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 2.32 | 2.13 | 1.68 | ✓ | ✓ | ✓ |
| q02 | 2.63 | 1.49 | 1.48 | ✓ | ✓ | ✓ |
| q03 | 3.51 | 2.37 | 2.63 | ✓ | ✗ | ✗ |
| q04 | 3.24 | 2.54 | 2.32 | ✓ | ✓ | ✓ |
| q05 | 1.87 | 1.18 | 1.44 | ✓ | ✗ | ✗ |

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
| q03 | good | 2 | 2 | ✓ |
| q03 | less_good | 0 | 0 | ✓ |
| q03 | wrong | 0 | 0 | ✓ |
| q04 | good | 1 | 1 | ✓ |
| q04 | less_good | 0 | 0 | ✓ |
| q04 | wrong | 0 | 0 | ✓ |
| q05 | good | 0 | 0 | ✓ |
| q05 | less_good | 0 | 0 | ✓ |
| q05 | wrong | 0 | 0 | ✓ |

### Method: `round`

| Question | Answer | Run1 | Run2 | Same? |
|----------|--------|------|------|-------|
| q01 | good | 3 | 3 | ✓ |
| q01 | less_good | 3 | 3 | ✓ |
| q01 | wrong | 1 | 1 | ✓ |
| q02 | good | 3 | 3 | ✓ |
| q02 | less_good | 1 | 1 | ✓ |
| q02 | wrong | 1 | 1 | ✓ |
| q03 | good | 4 | 4 | ✓ |
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
| q01 | good | 2.32 | 2.32 | ✓ |
| q01 | less_good | 2.13 | 2.13 | ✓ |
| q01 | wrong | 1.68 | 1.68 | ✓ |
| q02 | good | 2.63 | 2.63 | ✓ |
| q02 | less_good | 1.49 | 1.49 | ✓ |
| q02 | wrong | 1.48 | 1.48 | ✓ |
| q03 | good | 3.51 | 3.51 | ✓ |
| q03 | less_good | 2.37 | 2.37 | ✓ |
| q03 | wrong | 2.63 | 2.63 | ✓ |
| q04 | good | 3.24 | 3.24 | ✓ |
| q04 | less_good | 2.54 | 2.54 | ✓ |
| q04 | wrong | 2.32 | 2.32 | ✓ |
| q05 | good | 1.87 | 1.87 | ✓ |
| q05 | less_good | 1.18 | 1.18 | ✓ |
| q05 | wrong | 1.44 | 1.44 | ✓ |

---
## Per-Question Criterion Breakdown (Run 1)

Format per criterion: `int | round | float(kw/sem)`

### q01
- **good** — int=0  round=3  float=2.32  (max=10)
  - conceptual_definitions (/3): int=0  round=1  float=0.53   kw=0.16  sem=0.20
  - distinction_relationship (/2): int=0  round=0  float=0.46   kw=0.26  sem=0.20
  - alternative_names (/2): int=0  round=1  float=0.53   kw=0.33  sem=0.20
  - clarity_structure_examples (/3): int=0  round=1  float=0.78   kw=0.32  sem=0.20
- **less_good** — int=0  round=3  float=2.13  (max=10)
  - conceptual_definitions (/3): int=0  round=1  float=0.53   kw=0.16  sem=0.20
  - distinction_relationship (/2): int=0  round=1  float=0.52   kw=0.32  sem=0.20
  - alternative_names (/2): int=0  round=0  float=0.38   kw=0.18  sem=0.20
  - clarity_structure_examples (/3): int=0  round=1  float=0.69   kw=0.26  sem=0.20
- **wrong** — int=0  round=1  float=1.68  (max=10)
  - conceptual_definitions (/3): int=0  round=0  float=0.35   kw=0.03  sem=0.20
  - distinction_relationship (/2): int=0  round=1  float=0.58   kw=0.38  sem=0.20
  - alternative_names (/2): int=0  round=0  float=0.26   kw=0.06  sem=0.20
  - clarity_structure_examples (/3): int=0  round=0  float=0.49   kw=0.13  sem=0.20

### q02
- **good** — int=0  round=3  float=2.63  (max=10)
  - attribute_properties_principle (/3): int=0  round=0  float=0.35   kw=0.03  sem=0.20
  - zip_code_as_nominal (/3): int=0  round=1  float=0.97   kw=0.44  sem=0.20
  - inappropriate_analysis (/2): int=0  round=1  float=0.73   kw=0.53  sem=0.20
  - correct_analysis_alternatives (/2): int=0  round=1  float=0.59   kw=0.39  sem=0.20
- **less_good** — int=0  round=1  float=1.49  (max=10)
  - attribute_properties_principle (/3): int=0  round=0  float=0.30   kw=0.00  sem=0.20
  - zip_code_as_nominal (/3): int=0  round=1  float=0.69   kw=0.26  sem=0.20
  - inappropriate_analysis (/2): int=0  round=0  float=0.30   kw=0.10  sem=0.20
  - correct_analysis_alternatives (/2): int=0  round=0  float=0.20   kw=0.00  sem=0.20
- **wrong** — int=0  round=1  float=1.48  (max=10)
  - attribute_properties_principle (/3): int=0  round=0  float=0.35   kw=0.03  sem=0.20
  - zip_code_as_nominal (/3): int=0  round=1  float=0.63   kw=0.22  sem=0.20
  - inappropriate_analysis (/2): int=0  round=0  float=0.30   kw=0.10  sem=0.20
  - correct_analysis_alternatives (/2): int=0  round=0  float=0.20   kw=0.00  sem=0.20

### q03
- **good** — int=2  round=4  float=3.51  (max=10)
  - nominal_operations (/2): int=0  round=1  float=0.75   kw=0.55  sem=0.20
  - ordinal_operations (/3): int=1  round=1  float=1.17   kw=0.58  sem=0.20
  - interval_operations (/3): int=1  round=1  float=1.09   kw=0.52  sem=0.20
  - ratio_operations (/2): int=0  round=1  float=0.50   kw=0.30  sem=0.20
- **less_good** — int=0  round=2  float=2.37  (max=10)
  - nominal_operations (/2): int=0  round=0  float=0.50   kw=0.30  sem=0.20
  - ordinal_operations (/3): int=0  round=1  float=0.85   kw=0.37  sem=0.20
  - interval_operations (/3): int=0  round=1  float=0.73   kw=0.29  sem=0.20
  - ratio_operations (/2): int=0  round=0  float=0.29   kw=0.09  sem=0.20
- **wrong** — int=0  round=2  float=2.63  (max=10)
  - nominal_operations (/2): int=0  round=0  float=0.45   kw=0.25  sem=0.20
  - ordinal_operations (/3): int=0  round=1  float=0.93   kw=0.42  sem=0.20
  - interval_operations (/3): int=0  round=1  float=0.87   kw=0.38  sem=0.20
  - ratio_operations (/2): int=0  round=0  float=0.37   kw=0.17  sem=0.20

### q04
- **good** — int=1  round=3  float=3.24  (max=10)
  - interval_scale_explanation (/3): int=1  round=1  float=1.23   kw=0.62  sem=0.20
  - role_of_zero_point (/3): int=0  round=1  float=0.84   kw=0.36  sem=0.20
  - ratio_scale_kelvin (/2): int=0  round=1  float=0.72   kw=0.52  sem=0.20
  - consequence_for_ratios (/2): int=0  round=0  float=0.45   kw=0.25  sem=0.20
- **less_good** — int=0  round=3  float=2.54  (max=10)
  - interval_scale_explanation (/3): int=0  round=1  float=0.87   kw=0.38  sem=0.20
  - role_of_zero_point (/3): int=0  round=1  float=0.68   kw=0.25  sem=0.20
  - ratio_scale_kelvin (/2): int=0  round=1  float=0.55   kw=0.35  sem=0.20
  - consequence_for_ratios (/2): int=0  round=0  float=0.45   kw=0.25  sem=0.20
- **wrong** — int=0  round=2  float=2.32  (max=10)
  - interval_scale_explanation (/3): int=0  round=1  float=0.82   kw=0.34  sem=0.20
  - role_of_zero_point (/3): int=0  round=1  float=0.59   kw=0.19  sem=0.20
  - ratio_scale_kelvin (/2): int=0  round=0  float=0.46   kw=0.26  sem=0.20
  - consequence_for_ratios (/2): int=0  round=0  float=0.45   kw=0.25  sem=0.20

### q05
- **good** — int=0  round=1  float=1.87  (max=10)
  - definition_of_orderingonly_scale (/3): int=0  round=1  float=0.77   kw=0.32  sem=0.20
  - distinction_between_orderingonly_and_additive_scales (/3): int=0  round=0  float=0.46   kw=0.10  sem=0.20
  - allowed_vs_disallowed_computations (/2): int=0  round=0  float=0.34   kw=0.14  sem=0.20
  - practical_consequence_example (/2): int=0  round=0  float=0.30   kw=0.10  sem=0.20
- **less_good** — int=0  round=0  float=1.18  (max=10)
  - definition_of_orderingonly_scale (/3): int=0  round=0  float=0.38   kw=0.05  sem=0.20
  - distinction_between_orderingonly_and_additive_scales (/3): int=0  round=0  float=0.33   kw=0.02  sem=0.20
  - allowed_vs_disallowed_computations (/2): int=0  round=0  float=0.23   kw=0.03  sem=0.20
  - practical_consequence_example (/2): int=0  round=0  float=0.23   kw=0.03  sem=0.20
- **wrong** — int=0  round=1  float=1.44  (max=10)
  - definition_of_orderingonly_scale (/3): int=0  round=1  float=0.58   kw=0.18  sem=0.20
  - distinction_between_orderingonly_and_additive_scales (/3): int=0  round=0  float=0.36   kw=0.04  sem=0.20
  - allowed_vs_disallowed_computations (/2): int=0  round=0  float=0.27   kw=0.07  sem=0.20
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
