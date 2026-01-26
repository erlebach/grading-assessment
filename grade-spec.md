# Grading Architecture Specification

## Authority Hierarchy

This document defines the architectural rules for LLM-based grading in this project.

**Authoritative order (highest to lowest):**

1. **Rubrics** (`rubrics/`, `rubrics_dynamic/`) - Define grading law
   - Criteria, points, descriptions are immutable for any given question
   - Scoring rules are binding (e.g., max_score per criterion)
   - Only source of truth for grading requirements

2. **Evidence** (indexed sources, preprocessed context)
   - Indexed PDFs, documents, and materials are admissible information
   - Preprocessed evidence context (reranker results) is factual input
   - LLM decisions must be justified by provided evidence
   - No external knowledge beyond provided evidence is admissible

3. **Grading Code** (pipeline, scoring functions)
   - Applies rubrics deterministically
   - Executes LLM calls with evidence
   - Aggregates scores according to point allocation
   - No discretion beyond what rubric specifies

4. **Feedback** (student-facing explanations)
   - Explains grades; never influences them
   - Must cite evidence and rubric criteria
   - Generated after scores are determined
   - Non-authoritative (for explanation only)

## Grading Architecture Overview

### Design Philosophy: Semantic-Only with Preprocessed Evidence

The system uses a **semantic-only, evidence-driven** approach:

- **No keyword matching** - Scoring is semantic, not lexical
- **LLM decides scores** - Each criterion graded by LLM, not pre-computed
- **Preprocessed evidence** - Evidence retrieved and reranked once per question, reused across all students
- **Per-criterion isolation** - Each criterion graded independently by one LLM call
- **Transparent weighting** - Scores weighted by max_score values defined in rubric

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Preprocessing Phase                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Question Text                Evidence Sources (PDFs)            │
│        │                                 │                       │
│        └────────────────┬────────────────┘                       │
│                         │                                         │
│                    Index + Retrieve                              │
│                    (by criterion)                                │
│                         │                                         │
│                    Rerank Results                                │
│                    (cross-encoder)                               │
│                         │                                         │
│             ┌───────────▼──────────────┐                        │
│             │  Evidence Context JSON   │                        │
│             │  (reranker_results/)     │                        │
│             │  - question_id           │                        │
│             │  - grading_context[]     │                        │
│             │    - criterion_id        │                        │
│             │    - evidence[]          │                        │
│             │    - max_score           │                        │
│             └───────────┬──────────────┘                        │
│                         │                                         │
└─────────────────────────┼────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────┐
│                      Grading Phase                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Student Answer     Evidence Context                            │
│        │                    │                                     │
│        └──────────┬──────────┘                                    │
│                   │                                               │
│              For each criterion:                                 │
│              1. Format prompt (criterion + evidence)             │
│              2. Call LLM                                         │
│              3. Parse score (0-10 scale)                         │
│              4. Weight by max_score                              │
│                   │                                               │
│        ┌──────────▼──────────┐                                   │
│        │  Per-Criterion      │                                   │
│        │  Grades             │                                   │
│        │  - llm_score        │                                   │
│        │  - weighted_score   │                                   │
│        │  - feedback         │                                   │
│        └──────────┬──────────┘                                   │
│                   │                                               │
│        Sum weighted scores → Total Score                         │
│                   │                                               │
│             ┌─────▼─────┐                                        │
│             │   Result  │                                        │
│             │  - score  │                                        │
│             │  - max    │                                        │
│             │  - per-   │                                        │
│             │    crit   │                                        │
│             └───────────┘                                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Evidence Preprocessing (`reranker_results/`)

**Input:** Question text, source documents, rubric criteria

**Output:** JSON files with structure:
```json
{
  "question_id": "q02",
  "question_text": "...",
  "grading_context": [
    {
      "criterion_id": "criterion_name",
      "criterion_description": "...",
      "max_score": 3,
      "evidence": [
        {
          "source_id": "file_name",
          "texts": ["..."],
          "reranker_scores": [1.041],
          "similarity_scores": [0.699],
          "indexes": ["sentence_index"]
        }
      ]
    }
  ]
}
```

**Rules:**
- Generated once per question
- Reused across all students for that question
- Evidence selected by relevance to criterion description
- Reranker scores indicate relevance quality

### 2. Student Grading (`grade_with_evidence.py`)

**Input:**
- Student answer
- Evidence context
- (Optional) rubric (not required for this approach)

**Process:**
1. For each criterion in evidence context:
   - Format prompt with criterion description + evidence
   - Call LLM with student answer context
   - Parse LLM response: `{"score": 0-10, "feedback": "..."}`
   - Validate score in range [0, 10]
   - Weight: `weighted_score = (llm_score / 10.0) × max_score`

2. Aggregate:
   - Sum all weighted scores
   - Total = sum of max_scores (usually 10 for full rubric)

**Rules:**
- One LLM call per criterion (isolation)
- LLM decides score; no pre-computation
- Each criterion graded independently
- Error handling: if LLM fails, criterion gets 0
- No keyword matching; purely semantic

### 3. CLI Interface (`grade_from_evidence.py`)

**Responsibilities:**
- Load evidence context from JSON
- Load student submission from YAML
- Call `grade_student_with_evidence()`
- Write results to JSON
- Provide verbose output for debugging

**Arguments:**
- `--question`: Question ID (e.g., q02)
- `--student`: Student ID (default: student_001)
- `--answer_type`: good | less_good | wrong
- `--output`: Output file path (default: results/)
- `--verbose`: Detailed logging

## Architectural Rules

### Rule 1: Evidence is Authoritative

- Only evidence provided in `reranker_results/` is admissible
- LLM cannot use external knowledge
- Prompts must include full evidence context
- If evidence is insufficient, LLM should note this in feedback

**Implementation:**
```python
def _format_criterion_grading_prompt(
    criterion_description: str,
    max_score: int,
    evidence: list[dict],
    student_answer: str,
) -> str:
    # Prompts MUST include formatted_evidence
    # Evidence formatting is mandatory, not optional
```

### Rule 2: LLM Scores are Deterministic

- LLM returns 0-10 score for each criterion
- Score is immediately weighted by max_score
- No post-hoc adjustment of scores
- Weighted score is the grade for that criterion

**Implementation:**
```python
llm_score = int(max(0, min(result["score"], 10)))  # Validate bounds
weighted_score = (llm_score / 10.0) * max_score      # Apply weight
```

### Rule 3: Per-Criterion Isolation

- Each criterion is graded in a separate LLM call
- Criterion decisions do not influence each other
- Evidence for one criterion is not shown for another
- Aggregation happens after all criteria are graded

**Rationale:** Prevents holistic biases; ensures each criterion is fairly evaluated.

### Rule 4: Scores are Additive

- Total score = sum of weighted criterion scores
- Weighting by max_score handles unequal point allocations
- No curve, curve, scaling, or post-hoc adjustment
- Final score may be fractional (e.g., 7.5 / 10)

**Example:**
```
Criterion 1 (max 3):  LLM score 8/10 → (8/10) × 3 = 2.4 points
Criterion 2 (max 2):  LLM score 9/10 → (9/10) × 2 = 1.8 points
Criterion 3 (max 5):  LLM score 7/10 → (7/10) × 5 = 3.5 points
─────────────────────────────────────────────────────────────
Total: 2.4 + 1.8 + 3.5 = 7.7 / 10 points
```

### Rule 5: Feedback Does Not Affect Scores

- Feedback is generated AFTER scores are determined
- Feedback explains the score; it does not create it
- If feedback suggests a higher score, score does not change
- Feedback is for student understanding, not grading input

**Implementation:**
```python
# Score calculated first
llm_score = int(max(0, min(result["score"], 10)))

# Feedback is extracted from same response but not used for scoring
feedback = str(result.get("feedback", ""))
```

### Rule 6: Error Handling is Deterministic

- LLM failures → criterion score = 0
- JSON parsing errors → retry up to 3 times
- Invalid fields → default to 0, log error
- Failed criterion does not stop other criteria from grading

**Implementation:**
```python
if error_msg:
    feedback = f"Grading error: {error_msg}. Defaulting to 0 points."
    llm_score = 0  # Deterministic default
```

### Rule 7: Evidence Preprocessing is One-Time

- Evidence context is computed once per question
- Same evidence used for all students
- Students cannot influence evidence selection
- Evidence is static input to grading

**Rationale:** Ensures fairness and efficiency; all students evaluated with same reference material.

## Component Responsibilities

### `grade_with_evidence.py`

**Must:**
- Accept student answer + evidence context
- Call LLM for each criterion
- Validate and weight scores
- Return structured result with all criteria

**Must NOT:**
- Access external knowledge
- Modify evidence
- Adjust scores post-LLM
- Persist internal reasoning

### `grade_from_evidence.py`

**Must:**
- Load evidence context from JSON
- Load student submission from YAML
- Call grading function
- Write results to file

**Must NOT:**
- Modify evidence or student answer
- Pre-process scores
- Filter or sanitize LLM output

### `reranker_results/` (Evidence Artifacts)

**Must:**
- Contain one JSON file per question
- Include all criteria for that question
- Include top-ranked evidence per criterion
- Be regenerated when sources change

**Must NOT:**
- Be edited manually
- Contain subjective assessments
- Serve any purpose other than evidence retrieval

## Testing Principles

### Unit Tests (`test_grade_with_evidence.py`)

- Mock LLM to test scoring logic
- Test evidence formatting
- Test prompt construction
- Test error handling
- Test weighted score calculation

**Mock LLM behavior:**
```python
# Test valid response
mock_response.message.content = '{"score": 8, "feedback": "Good."}'

# Test error handling
mock_response.message.content = "invalid json"

# Test boundary cases
mock_response.message.content = '{"score": 15, ...}'  # Clamped to 10
```

### Integration Tests (`test_grade_from_evidence.py`)

- Test end-to-end CLI workflow
- Test evidence loading
- Test submission loading
- Test output file creation
- Test verbose mode

### Behavioral Tests

- Grade all answer types (good, less_good, wrong)
- Verify score distribution (good > less_good > wrong)
- Verify feedback quality (cited evidence)

## Differences from Previous Approaches

| Aspect | Previous (Keyword + Semantic) | Current (LLM-Decides) |
|--------|------------------------------|----------------------|
| **Scoring** | Pre-computed formula | LLM decides |
| **Keywords** | Required, explicit matching | Not used |
| **Semantic** | Formula-based with decay | LLM judges directly |
| **LLM role** | Explain decisions | Make decisions |
| **Calls per student** | 1 (feedback) | 4 (one per criterion) |
| **Evidence use** | Scoring input | Context for LLM |
| **Flexibility** | Fixed formula | LLM judges context |

## Future Extensions

### Batch Grading (Task #5)

- Grade multiple students for same question
- Reuse evidence context
- Parallel or sequential processing
- Aggregate statistics

### Dynamic Rubric Generation

- Generate rubrics from course materials
- Create evidence context automatically
- Support for new questions without manual setup

### Confidence Scores

- Ask LLM for confidence in score
- Flag low-confidence grades for review
- Optional human review workflow

### Fine-Tuning

- Collect grades + LLM confidence
- Analyze systematic biases
- Adjust prompts for better calibration

## References

- `AGENT.md` - General agent constraints
- `CLAUDE.md` - Claude Code specific rules
- `grading_dynamic_rubrics/grade_with_evidence.py` - Implementation
- `grading_dynamic_rubrics/grade_from_evidence.py` - CLI interface
- `tests/test_grade_with_evidence.py` - Unit tests
- `tests/test_grade_from_evidence.py` - Integration tests
