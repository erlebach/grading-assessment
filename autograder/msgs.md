Reviewing the paper and current system to understand the two-dimensional scoring approach:


[4 tools called]


Checking how evidence similarity scores are currently captured:


[2 tools called]


## Current system analysis

The system retrieves evidence with similarity scores (via `DualIndexRetriever` with cross-encoder reranking), but `apply_rubric_scoring()` only uses keyword matching and ignores the semantic similarity scores from the retrieved evidence.

## Two-dimensional scoring approach

### Dimension 1: Keyword matching
- Extracts keywords from criterion descriptions
- Checks literal presence in student answer
- Current: `keyword_score = (matches / total_keywords) * max_points`

### Dimension 2: Semantic similarity (RAG)
- Retrieves evidence chunks with similarity scores
- Uses cross-encoder reranking scores (0.0 to 1.0+)
- Current: Retrieved but not used in scoring

## Design questions

### 1. Single rubric structure
For a generic rubric that works across all 10 questions, consider criteria like:
- **Correctness**: Does the answer correctly address the question?
- **Completeness**: Are all required elements present?
- **Terminology**: Are domain-specific terms used correctly?
- **Evidence alignment**: Does the answer align with course material?

Question: Should we use all four, or start with 2–3? What point distribution? (e.g., Correctness: 5, Completeness: 3, Terminology: 2)

### 2. Combining keyword and semantic scores
Proposed formula:
```
final_score = (w_keyword * keyword_score) + (w_semantic * semantic_score)
```
Where:
- `keyword_score` = normalized keyword match score (0–1)
- `semantic_score` = average/weighted similarity of retrieved evidence (0–1)
- `w_keyword + w_semantic = 1.0`

Questions:
- How should `semantic_score` be computed? Average of top-k evidence scores? Weighted average? Maximum?
- Initial weights: 50/50, or favor one dimension? (e.g., 40% keyword, 60% semantic)

### 3. Evidence similarity score aggregation
The retriever returns multiple evidence chunks per criterion, each with a similarity score. Options:
- Average: `semantic_score = mean([ev["score"] for ev in evidence])`
- Weighted average: Weight by rank position
- Top-k average: Average of top 3 evidence scores
- Maximum: Use highest similarity score

Question: Which aggregation method should we use initially?

### 4. Normalization
- Keyword scores: Already normalized (0–1) via `matches / total_keywords`
- Semantic scores: Need normalization. Cross-encoder scores can be >1.0. Should we:
  - Use raw scores (may need clipping)
  - Normalize to [0, 1] using min-max
  - Use a sigmoid function

Question: How should we normalize semantic scores?

### 5. Rubric criterion design
For a generic rubric, each criterion needs:
- `description`: Generic enough to apply to any question
- `keywords`: How to extract? From the question text? From the criterion description?
- `evidence_required`: Should all criteria require evidence, or only some?

Example generic criterion:
```yaml
- criterion_id: "correctness"
  description: "Answer correctly addresses the question and demonstrates understanding"
  points: 5
  evidence_required: true
  evaluation_method: "semantic"
```

Question: Should keywords be extracted from the question text, the criterion description, or both?

### 6. Calibration strategy
To adjust weights for fair grading:
- Test on all 30 answers (10 questions × 3 variants)
- Measure: Do "Good" answers score 8–10, "Less good" 4–7, "Wrong" 0–3?
- Iterate: Adjust `w_keyword` and `w_semantic` until distributions match expectations

Question: Should we build a calibration script that tests different weight combinations and reports score distributions?

## Implementation considerations

1. Modify `apply_rubric_scoring()` to:
   - Compute keyword score (current behavior)
   - Compute semantic score from evidence similarity
   - Combine with configurable weights
   - Return both scores for transparency

2. Add weight configuration:
   - In rubric YAML? (per-criterion or global)
   - In config file?
   - As function parameters?

3. Score transparency:
   - Include both keyword_score and semantic_score in results
   - Show which evidence chunks contributed
   - Help with debugging and calibration

## Questions for you

1. Rubric criteria: Which generic criteria should we use? (Correctness, Completeness, Terminology, Evidence alignment, or others?)
2. Point distribution: How should points be allocated across criteria? (e.g., 5/3/2 for 10 total)
3. Semantic score computation: Average, weighted average, top-k average, or maximum?
4. Initial weights: Start with 50/50, or favor one dimension?
5. Normalization: How should we normalize cross-encoder similarity scores?
6. Keyword extraction: Extract from question text, criterion description, or both?

Once we align on these, we can design the two-dimensional scoring system.
