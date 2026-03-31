# T4.3 Sample Grading Report

**Date:** 2026-03-30
**Branch:** dynamic_rubrics
**Scoring method:** keyword + semantic (hybrid, pre-LLM stage)
**Note:** All scores are float weighted totals (combined_score × max_points, summed across criteria).
Integer `total_score` (via `int()` truncation) is 0 for nearly all rows — see Root Cause section.

Questions graded: q01, q02, q03, q04, q05

---

## Score Table

| Question | Good | Less-Good | Wrong | Good≥LG | LG≥Wrong | Pass |
|----------|------|-----------|-------|---------|----------|------|
| q01 | 2.14 | 1.86 | 1.52 | ✓ | ✓ | ✓ |
| q02 | 2.96 | 1.71 | 2.01 | ✓ | ✗ | ✗ |
| q03 | 5.66 | 2.32 | 2.34 | ✓ | ✗ | ✗ |
| q04 | 2.93 | 2.63 | 2.14 | ✓ | ✓ | ✓ |
| q05 | 1.76 | 1.15 | 1.39 | ✓ | ✗ | ✗ |

**Overall ordering validation:** FAIL
(good > wrong always holds; good > less_good > wrong fails for q02, q03, q05)

---

## Root Cause Analysis

### 1. `int()` truncation collapses all scores to 0

The pipeline uses `int(combined_score × max_points)` to compute integer criterion scores.
Combined scores are in the range 0.10–0.55, and when multiplied by max_points (2–3) give
values of 0.2–1.5, which `int()` truncates to 0 in almost every case.
Only q03 (good) and q04 (good/less_good) escaped because q03 has a higher-quality rubric
with more specific keywords and better evidence coverage.

**Consequence:** Integer scores are useless for differentiation. All comparisons in this
report use float weighted totals.

**Recommendation:** Replace `int()` with `round()` in `apply_rubric_scoring_dynamic()`.
This alone would fix many ordering violations.

### 2. `extract_keywords` extracts stopwords from criterion descriptions

`extract_keywords(description)` uses a simple tokenizer that includes stopwords ("full",
"credit", "awarded", "when", "student", "provides", etc.) and punctuation-attached tokens
("terms:", "object:", "record/instance/case/entity/sample/point"). The student answer
cannot match these non-content tokens, artificially deflating keyword scores.

**Consequence:** Keyword scores are 10–30% even for correct "good" answers.

**Recommendation:** Filter stopwords in `extract_keywords` and split on punctuation/slash
before matching.

### 3. Semantic score uses evidence count, not similarity quality

The semantic score is `min(1.0, len(evidence_list) / semantic_top_k)`. This means any
answer that retrieves N evidence chunks gets the same semantic score regardless of whether
those chunks actually support the answer. Since all answer types retrieve similar numbers
of chunks (all on the same topic), semantic scores barely differentiate.

**Consequence:** Semantic scores are uniformly 0.20 (1 of 5 chunks) for most criteria.
This does not separate good from wrong answers.

**Recommendation:** Use reranker scores or similarity scores as weights, not just chunk
count. Or use the two-step LLM pipeline (`grade_with_evidence.py`) for final scoring.

### 4. Ordering violations for q02, q03, q05

- **q02** (Δ=0.29): wrong (2.01) > less_good (1.71). The wrong answer states "zip codes
  are integers, differences are meaningful" — accidentally matching rubric keywords
  "meaningful", "differences", "numeric". The less_good answer is shorter with fewer hits.
- **q03** (Δ=0.02): Effectively tied. Both less_good and wrong mention ordinal/interval,
  triggering similar keyword hits. Difference is within noise.
- **q05** (Δ=0.24): The wrong answer contains "ordering", "ordinal", "computations" that
  match rubric keywords better than the vague less_good answer.

---

## Per-Question Criterion Breakdown

### q01 — PASS (good=2.14 > less_good=1.86 > wrong=1.52)

| Criterion | Good kw/sem | LG kw/sem | Wrong kw/sem |
|-----------|------------|-----------|--------------|
| conceptual_definitions (3 pts) | 0.12/0.20 | 0.12/0.20 | 0.03/0.20 |
| distinction_relationship (2 pts) | 0.21/0.20 | 0.26/0.20 | 0.30/0.20 |
| alternative_names (2 pts) | 0.29/0.20 | 0.16/0.20 | 0.05/0.20 |
| clarity_structure_examples (3 pts) | 0.30/0.20 | 0.17/0.20 | 0.09/0.20 |

Good answer differentiated mainly by `alternative_names` keyword coverage (0.29 vs 0.05 wrong).

### q02 — FAIL (good=2.96 > wrong=2.01 > less_good=1.71)

| Criterion | Good kw/sem | LG kw/sem | Wrong kw/sem |
|-----------|------------|-----------|--------------|
| attribute_properties_principle (3 pts) | 0.03/0.60 | 0.00/0.40 | 0.03/0.60 |
| zip_code_as_nominal (3 pts) | 0.38/0.20 | 0.22/0.20 | 0.19/0.20 |
| inappropriate_analysis (2 pts) | 0.46/0.20 | 0.09/0.20 | 0.09/0.20 |
| correct_analysis_alternatives (2 pts) | 0.30/0.20 | 0.00/0.20 | 0.00/0.20 |

Wrong ties good on `attribute_properties_principle` semantic score (both 0.60), dragging less_good below wrong.

### q03 — FAIL (good=5.66 >> less_good=2.32 ≈ wrong=2.34)

| Criterion | Good kw/sem | LG kw/sem | Wrong kw/sem |
|-----------|------------|-----------|--------------|
| nominal_operations (2 pts) | 0.42/0.60 | 0.27/0.20 | 0.19/0.20 |
| ordinal_operations (3 pts) | 0.48/0.60 | 0.35/0.20 | 0.35/0.20 |
| interval_operations (3 pts) | 0.44/1.00 | 0.28/0.20 | 0.32/0.20 |
| ratio_operations (2 pts) | 0.26/0.60 | 0.11/0.20 | 0.15/0.20 |

Good answer clearly dominates via higher semantic evidence coverage. The less_good vs wrong
violation is marginal (0.02) — within noise.

### q04 — PASS (good=2.93 > less_good=2.63 > wrong=2.14)

| Criterion | Good kw/sem | LG kw/sem | Wrong kw/sem |
|-----------|------------|-----------|--------------|
| interval_scale_explanation (3 pts) | 0.51/0.20 | 0.31/0.40 | 0.29/0.20 |
| role_of_zero_point (3 pts) | 0.32/0.20 | 0.22/0.20 | 0.17/0.20 |
| ratio_scale_kelvin (2 pts) | 0.46/0.20 | 0.31/0.20 | 0.23/0.20 |
| consequence_for_ratios (2 pts) | 0.22/0.20 | 0.22/0.20 | 0.22/0.20 |

Ordering holds. Good answer wins on `interval_scale_explanation` keyword coverage (0.51 vs 0.29).

### q05 — FAIL (good=1.76 > wrong=1.39 > less_good=1.15)

| Criterion | Good kw/sem | LG kw/sem | Wrong kw/sem |
|-----------|------------|-----------|--------------|
| definition_of_orderingonly_scale (3 pts) | 0.29/0.20 | 0.05/0.20 | 0.17/0.20 |
| distinction_ordering_additive (3 pts) | 0.09/0.20 | 0.02/0.20 | 0.04/0.20 |
| allowed_vs_disallowed (2 pts) | 0.11/0.20 | 0.03/0.20 | 0.06/0.20 |
| practical_consequence_example (2 pts) | 0.08/0.20 | 0.03/0.20 | 0.03/0.20 |

All scores extremely low. The q05 rubric uses Unicode hyphens and compound terms
("ordering‑only", "additive") that don't tokenize cleanly. The wrong answer happens to
include "ordering" and "ordinal" more than the vague less_good answer.

---

## Recommendations (Prioritised)

### P1 — Fix `int()` truncation (pipeline bug — one line)
In `grading_dynamic_rubrics/pipeline.py:apply_rubric_scoring_dynamic()`, change:
```python
final_score = int(combined_score * max_points)
```
to:
```python
final_score = round(combined_score * max_points)
```

### P2 — Filter stopwords in `extract_keywords`
In `grader/grade_question.py:extract_keywords()`, add a stopword list and split
slash-separated/punctuation-attached tokens before matching.

### P3 — Use LLM stage for final scoring
The current keyword+semantic stage is a retrieval pre-filter, not a grader.
For reliable ordering, the `grade_with_evidence.py` LLM path should be the primary
scoring path. This is the intended architecture.

### P4 — Weight semantic score by similarity, not count
Replace `min(1.0, len(evidence_list) / top_k)` with a reranker-weighted score.

### P5 — Rubric text improvements
- **q02:** `attribute_properties_principle` has very few content keywords (kw=0.03).
  Add: "measurement type", "stored format", "data type", "properties determine".
- **q05:** Replace Unicode hyphens and compound terms with simple ASCII tokens.
  Add "ordinal", "interval", "mean", "median", "addition", "subtraction" explicitly.

### Category Weight Adjustments
- Current weights (keyword=0.5, semantic=0.5) give equal weight to two weak signals.
- After P2+P4 fixes, recalibrate. Suggested starting point: keyword=0.3, semantic=0.7.
