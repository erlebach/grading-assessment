# Autograder v2 — Usage Guide

## Overview

The v2 pipeline replaces keyword/semantic scoring with a **concept-presence LLM judge**. It operates on typed rubric checks with precision levels, and uses a Karpathy-style iterative refinement loop to ensure rubrics discriminate `good > less_good > wrong` synthetic answers.

### Pipeline Stages

```
Student question
    │
    ▼
Answer Generation   — 9 synthetic answers (3 good / 3 less_good / 3 wrong) at T=0.7
    │
    ▼
Rubric Generation   — LLM generates concept-check rubric informed by source + answers
    │
    ▼
Karpathy Loop       — train/val split, critic fixes violations, stops at convergence
    │
    ▼
LLM Judge           — evaluates each student answer against final rubric (single/multi mode)
    │
    ▼
Scoring             — weighted-mean float grade (0–10, no truncation)
```

---

## File Structure

```
v2/
  __init__.py
  models.py             # Core data models
  rubric_schema.py      # LLM JSON → RubricV2 validation
  question_types.py     # 10 QuestionType enum values + prompt templates
  answer_generator.py   # Synthetic answer generator (3×3)
  rubric_generator.py   # Concept-check rubric generator
  rubric_critic.py      # Proposes rubric fixes for ordering violations
  karpathy_loop.py      # Iterative rubric refinement
  judge.py              # LLM concept-presence judge (single/multi)
  scoring.py            # Weighted-mean float scoring
  benchmark.py          # Ordering violation checker
  pipeline.py           # Full v2 orchestration

config/
  rubric_generation.yaml  # Model tiers, loop parameters, scoring mode

tests/v2/               # Full test suite (45 tests)
```

---

## Configuration: `config/rubric_generation.yaml`

```yaml
model_tier: foundational      # oss | foundational | mixed
evaluation_mode: single       # single | multi
max_iterations: 5             # Karpathy loop budget (max refinement rounds)
max_checks_per_criterion: 4   # Max concept checks per rubric criterion
score_mode: float             # float | binary
answer_variants_per_level: 3  # Synthetic answers per quality level (3×3 = 9 total)
answer_temperature: 0.7       # LLM temperature for answer generation

# Train/validation split for Karpathy loop
train_per_level: 2            # Answers used for training (violation detection)
val_per_level: 1              # Answers held out for validation

# LLM settings per tier
tiers:
  foundational:
    provider: gemini
    model: models/gemini-2.5-flash
  oss:
    provider: ollama
    model: gpt-oss:20b
  mixed:
    rubric_generation: foundational   # Use foundational LLM for rubric gen
    scoring: oss                      # Use OSS LLM for scoring
```

### Model Tiers

| Tier | Provider | Use Case |
|------|----------|----------|
| `foundational` | Gemini Flash | Default; best quality rubric generation |
| `oss` | Ollama (gpt-oss:20b) | Local/offline; lower cost |
| `mixed` | Both | Foundational for rubric gen, OSS for scoring |

---

## Core Data Models (`v2/models.py`)

### `ConceptCheck`

One typed concept check within a rubric criterion.

| Field | Type | Description |
|-------|------|-------------|
| `check_id` | `str` | Unique identifier |
| `check_type` | `CheckType` | One of: `definition`, `distinction`, `mechanism`, `positive_example`, `negative_example`, `generalization` |
| `concept` | `str` | Vocabulary-agnostic concept description |
| `points` | `float` | Point value (> 0) |
| `precision_levels` | `dict[PrecisionLevel, str]` | Descriptions for `full`, `partial`, `none` — all three required |

### `PrecisionLevel` Weights

| Level | Weight | Meaning |
|-------|--------|---------|
| `full` | 1.0 | Complete, precise answer |
| `partial` | 0.5 | Correct concept but vague/incomplete |
| `none` | 0.0 | Absent or wrong |

### `CriterionV2`

A rubric criterion composed of typed concept checks.

| Field | Type | Description |
|-------|------|-------------|
| `criterion_id` | `str` | Unique identifier |
| `points` | `float` | Must equal sum of check points |
| `checks` | `list[ConceptCheck]` | At least 1, max 4 |

### `RubricV2`

Complete rubric for one question.

| Field | Type | Description |
|-------|------|-------------|
| `rubric_id` | `str` | Format: `{question_id}_v{version}` |
| `question_id` | `str` | e.g. `q01` |
| `question_type` | `str` | Matches `QuestionType` enum value |
| `version` | `int` | Starts at 1, incremented by Karpathy loop |
| `criteria` | `list[CriterionV2]` | At least 1, max 6 |
| `iteration` | `int` | Karpathy iteration that produced this rubric |

### `GradeV2`

Final grade record for one student answer.

| Field | Type | Description |
|-------|------|-------------|
| `grade_id` | `str` | Format: `{student_id}_{question_id}` |
| `question_id` | `str` | |
| `student_id` | `str` | |
| `rubric_id` | `str` | |
| `rubric_version` | `int` | |
| `check_evaluations` | `list[CheckEvalV2]` | One per concept check |
| `raw_score` | `float` | Weighted mean of check scores (0.0–1.0) |
| `final_score` | `float` | `raw_score × 10` (0.0–10.0, float, no truncation) |
| `evaluation_mode` | `str` | `single` or `multi` |
| `model_tier` | `str` | `oss`, `foundational`, or `mixed` |

### `SyntheticAnswer`

One LLM-generated synthetic answer.

| Field | Type | Description |
|-------|------|-------------|
| `question_id` | `str` | |
| `quality` | `AnswerQuality` | `good`, `less_good`, or `wrong` |
| `variant` | `int` | 1, 2, or 3 |
| `text` | `str` | Answer text |

---

## Question Types (`v2/question_types.py`)

Ten canonical question types, each with a rubric-generation prompt template.

| Enum Value | Description |
|------------|-------------|
| `definition` | Define a concept — tests properties, precision, distinction |
| `distinction` | Contrast two concepts — tests naming, key property, example |
| `mechanism` | Explain why/how — tests causal chain, breaking point |
| `classification` | Assign items to categories — tests assignment, justification, edge cases |
| `enumeration` | List items — tests completeness, absence of errors |
| `example_generation` | Give a valid example — tests validity, explanation, non-triviality |
| `error_identification` | Find the error — tests identification, explanation, correction |
| `comparison` | Compare two things — tests similarity, difference, judgment |
| `application` | Apply concept to scenario — tests identification, application, justification |
| `proof_or_argument` | Construct an argument — tests premises, logical steps, conclusion |

### Usage

```python
from v2.question_types import QuestionType, get_prompt_template

tmpl = get_prompt_template(QuestionType.MECHANISM)
# Returns prompt fragment with {question} placeholder
```

---

## Components

### `AnswerGenerator` (`v2/answer_generator.py`)

Generates 9 synthetic answers (3 per quality level).

```python
from v2.answer_generator import AnswerGenerator, AnswerGeneratorConfig

config = AnswerGeneratorConfig(
    variants_per_level=3,   # answers per quality level
    temperature=0.7,        # LLM temperature
)
gen = AnswerGenerator(llm=llm, config=config)
answers = gen.generate(
    question_id="q01",
    question_text="Why can't you compute ratios on Celsius?",
    question_type="mechanism",
    source_material="<course text>",
)
# Returns list[SyntheticAnswer] — 9 items (3 good, 3 less_good, 3 wrong)
```

### `RubricGeneratorV2` (`v2/rubric_generator.py`)

Generates a concept-check rubric from source material and synthetic answers.

```python
from v2.rubric_generator import RubricGeneratorV2, RubricGeneratorConfig

config = RubricGeneratorConfig(
    max_checks_per_criterion=4,   # complexity budget
    max_criteria=6,               # max criteria in rubric
)
gen = RubricGeneratorV2(llm=llm, config=config)
rubric = gen.generate(
    question_id="q01",
    question_text="...",
    question_type="mechanism",
    source_material="<course text>",
    synthetic_answers=answers,    # list[SyntheticAnswer] from AnswerGenerator
    version=1,
)
# Returns RubricV2
```

### `KarpathyLoop` (`v2/karpathy_loop.py`)

Iteratively refines a rubric until it discriminates quality levels correctly.

```python
from v2.karpathy_loop import KarpathyLoop, KarpathyConfig

config = KarpathyConfig(
    max_iterations=5,     # stop after this many refinement rounds
    train_per_level=2,    # answers per level used for training
    val_per_level=1,      # answers per level held out for validation
)
loop = KarpathyLoop(
    judge=judge,              # ConceptJudge instance
    scorer=score_fn,          # callable(**kw) -> GradeV2
    critic=critic,            # RubricCritic instance
    rubric_generator=gen,     # RubricGeneratorV2 instance
    config=config,
)
result = loop.run(
    initial_rubric=rubric,
    answers=synthetic_answers,
    question_id="q01",
    question_text="...",
    question_type="mechanism",
    source_material="...",
)
# result.converged: bool
# result.iterations_used: int
# result.final_rubric: RubricV2
# result.all_violations: list[OrderingViolation]
```

**Convergence condition:** No ordering violations on both train and val sets.

### `ConceptJudge` (`v2/judge.py`)

Evaluates a student answer against a rubric using an LLM.

```python
from v2.judge import ConceptJudge, EvaluationMode

judge = ConceptJudge(llm=llm, mode=EvaluationMode.SINGLE)
# or EvaluationMode.MULTI (one LLM call per check)

evals = judge.evaluate(
    answer_text="The student's answer...",
    rubric=rubric,
    evidence_context="",   # optional retrieved context
)
# Returns list[CheckEvalV2] — one per concept check
```

**Modes:**

| Mode | LLM Calls | Use Case |
|------|-----------|----------|
| `SINGLE` | 1 per answer | Faster; all checks in one prompt |
| `MULTI` | 1 per check per answer | More focused; better for complex rubrics |

### `compute_grade` (`v2/scoring.py`)

Computes weighted-mean float grade from check evaluations.

```python
from v2.scoring import compute_grade

grade = compute_grade(
    grade_id="student_001_q01",
    question_id="q01",
    student_id="student_001",
    rubric=rubric,
    check_evaluations=evals,
    evaluation_mode="single",
    model_tier="foundational",
)
# grade.raw_score: float (0.0–1.0)   = sum(score_i * points_i) / sum(points_i)
# grade.final_score: float (0.0–10.0) = raw_score * 10  (no int() truncation)
```

### Ordering Benchmark (`v2/benchmark.py`)

Checks that rubric grades satisfy `good > less_good > wrong`.

```python
from v2.benchmark import find_violations, check_ordering
from v2.models import AnswerQuality

# Single question
violations = find_violations(
    question_id="q01",
    grades_by_quality={
        AnswerQuality.GOOD: grade_good,
        AnswerQuality.LESS_GOOD: grade_less_good,
        AnswerQuality.WRONG: grade_wrong,
    }
)

# Multiple questions
result = check_ordering(all_grades_dict)
# result.total_questions: int
# result.questions_with_violations: int
# result.violation_rate: float  (0.0–1.0)
# result.passed(): bool
```

---

## Full Pipeline (`v2/pipeline.py`)

Orchestrates all stages for one question.

```python
from v2.pipeline import PipelineV2, PipelineConfig

config = PipelineConfig(
    evaluation_mode="single",    # "single" | "multi"
    model_tier="foundational",   # "oss" | "foundational" | "mixed"
)

pipeline = PipelineV2(
    answer_generator=answer_gen,
    rubric_generator=rubric_gen,
    karpathy_loop=karpathy_loop,
    judge=judge,
    config=config,
)

result = pipeline.run(
    question_id="q01",
    question_text="Why can't you compute ratios on Celsius?",
    question_type="mechanism",
    source_material="<course text>",
    student_answers={
        "student_001": "Celsius has an arbitrary zero point...",
        "student_002": "You can't because the scale is different.",
    },
    synthetic_answers=None,      # optional: provide pre-generated answers
    evidence_context="",         # optional: retrieved context for judge
)

# result["rubric"]          — final RubricV2 after Karpathy refinement
# result["student_grades"]  — dict[student_id, GradeV2]
# result["converged"]       — bool: did Karpathy loop converge?
# result["iterations"]      — int: how many refinement iterations ran
```

---

## LLM Tier Helper (`config/llm_config.py`)

```python
from config.llm_config import configure_llm_for_tier

llm = configure_llm_for_tier("foundational")  # reads config/rubric_generation.yaml
llm = configure_llm_for_tier("oss")
llm = configure_llm_for_tier("mixed")         # returns foundational LLM
# Raises ValueError for unknown tiers
```

---

## Rubric Schema Validation (`v2/rubric_schema.py`)

Validates raw LLM JSON output into a `RubricV2`.

```python
from v2.rubric_schema import parse_rubric_response

rubric = parse_rubric_response(
    raw=llm_json_dict,         # parsed from LLM output
    question_id="q01",
    question_type="mechanism",
    version=1,
)
# Raises ValidationError if:
#   - precision_levels missing any of full/partial/none
#   - criterion has > 4 checks
#   - rubric has > 6 criteria
```

---

## Running Tests

```bash
# All v2 tests (45 tests)
.venv/bin/python -m pytest tests/v2/ -v

# Existing pipeline tests (183 tests)
.venv/bin/python -m pytest tests/test_models.py tests/test_check_extraction.py \
  tests/test_categorization.py tests/test_deduplication.py \
  tests/test_rubric_generator.py tests/test_check_evaluation.py \
  tests/test_scoring.py tests/test_grade_storage.py -v
```

---

## Design Notes

- **No vocabulary matching:** Rubric checks judge concept presence, not specific words.
- **Float scores throughout:** `raw_score` and `final_score` are always `float`; no `int()` truncation.
- **Precision levels enforce scores:** `CheckEvalV2` validates that `score` matches the precision weight (full=1.0, partial=0.5, none=0.0) to within 0.01.
- **Criterion point consistency:** `CriterionV2.points` must equal the sum of its checks' points (enforced by validator).
- **Ordering violations use strict inequality:** Tied scores between quality levels are not treated as violations (`score_higher < score_lower` triggers a violation, not `<=`).
- **Retrieval integration:** `ConceptJudge.evaluate()` accepts `evidence_context: str`; wiring `retrieval_core` to populate this per answer is a follow-on task.
