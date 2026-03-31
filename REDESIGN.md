# Autograder Redesign — Design Summary

**Date:** 2026-03-31
**Status:** Pre-implementation design document
**Context:** Lessons learned from v1 (keyword+semantic pipeline) drive a substantive
refactoring into v2 (concept-based, LLM-judge pipeline).

---

## 1. Motivation — What We Learned

### What the current pipeline does

Each question has a dynamically-generated rubric with named criteria. For each
criterion the pipeline computes:

```
combined_score = keyword_weight × keyword_score + semantic_weight × semantic_score
```

- **keyword_score**: fraction of criterion keywords found in the student answer
- **semantic_score**: `min(1, evidence_chunks_retrieved / top_k)`

Final score per criterion: `round(combined_score × max_points)`

### Why it fails

1. **Keyword matching checks vocabulary, not understanding.**
   A student who writes "you can't divide Celsius temperatures" has the right
   concept but misses the keyword "ratio". Keyword score = 0. Correct answer = 0.

2. **Stopwords leak into keyword lists.**
   Rubric descriptions contain words like "full", "credit", "awarded", "student",
   "provides" — these dominate keyword lists and dilute content signal. P2 (this
   session) partially addressed this but did not fix ordering violations.

3. **Semantic score is uniform across answer quality levels.**
   All answers (good/less_good/wrong) retrieve similar chunk counts on the same
   topic, so `evidence_count / top_k` ≈ constant. It provides no discrimination.

4. **Rubric generated from slides only, independently of answers.**
   The rubric uses slide vocabulary; students use their own vocabulary (they have
   access to AI and the web). Mismatch is structural, not fixable by stopword lists.

5. **`int()` truncation collapses ~80% of scores to 0** (P1, partially addressed).

### Ordering violations observed (benchmark, q01–q05)

- `float` method: q03 less_good < wrong, q05 less_good < wrong
- `round` method: q05 wrong ≥ less_good

These are not noise — they are structural failures of keyword-based scoring.

---

## 2. Core Design Insight

**Replace keyword matching with concept-presence evaluation by an LLM judge.**

A criterion is no longer "does the answer contain these words?" but
"does the answer demonstrate this concept, at what level of precision?"

This is vocabulary-agnostic, handles paraphrase, and naturally produces
partial credit.

---

## 3. New Rubric Structure

### Criterion schema (v2)

```yaml
criterion_id: role_of_zero_point
points: 3
checks:
  - type: definition
    concept: "zero point on an interval scale is arbitrary/conventional, not an
              absence of the measured quantity"
    points: 1
    precision_levels:
      2: "Names the specific convention (e.g., freezing point of water) and
          states it is not absence of heat/temperature"
      1: "States zero is arbitrary or conventional without specifics"
      0: "Absent, circular, or states zero has physical meaning on Celsius"

  - type: mechanism
    concept: "arbitrary zero makes ratio comparisons meaningless"
    points: 1
    precision_levels:
      2: "Explains causal chain: ratios compare relative to origin;
          arbitrary origin → ratio is relative to convention, not physics"
      1: "States ratios don't work because of the zero, without causal chain"
      0: "Absent or causally wrong"

  - type: example
    concept: "concrete case showing ratio breaks on interval (or works on ratio scale)"
    points: 1
    precision_levels:
      2: "Specific numbers with explanation: 20°C/10°C ≠ 'twice as warm'
          because 0°C is not absence of heat; OR 200K/100K = 2 is valid because
          0K = no thermal energy"
      1: "Mentions Celsius vs Kelvin without numeric example"
      0: "No example, or example is wrong"
```

### Check types

| Type | Tests | Example |
|------|-------|---------|
| `definition` | Student states what something is | "Celsius has no true zero" |
| `distinction` | Student contrasts two things | "Interval vs ratio: ratios require absolute zero" |
| `mechanism` | Student explains *why* | "Arbitrary origin → ratio comparison is relative to convention" |
| `positive_example` | Demonstrates correct usage | "200K is twice 100K" |
| `negative_example` | Shows what breaks and why | "20°C/10°C ≠ twice as warm because 0°C is arbitrary" |
| `generalization` | Applies concept to new case | "Same issue applies to year numbering" |

### Precision scoring within each check

Each check awards points on two dimensions:

- **Presence** (0/1): is the concept there at all?
- **Precision** (0/1/2): how accurately is it expressed?

Operationalized as:
1. **Specificity**: names specific property/value/scale
2. **Causal chain**: explains *why*, not just *what*
3. **Boundary conditions**: states when something holds and when it doesn't
4. **No false additions**: no incorrect claims alongside correct ones

---

## 4. Scoring Architecture (v2)

### Two scoring modes (switch-controlled)

```yaml
evaluation_mode: single   # one LLM call per answer evaluates all checks
evaluation_mode: multi    # one LLM call per check
```

### Three model tiers (switch-controlled)

```yaml
model_tier: oss           # gpt-oss:20b via Ollama (local, fast)
model_tier: foundational  # Claude / GPT-4 (external API)
model_tier: mixed         # foundational for rubric gen, oss for scoring
```

### Comparison matrix (empirical question)

| Strategy | Calls/answer | Model | Hypothesis |
|----------|-------------|-------|------------|
| single, oss | 1 | oss:20b | Baseline |
| multi, oss | N checks | oss:20b | Better than single/oss |
| single, foundational | 1 | Claude/GPT-4 | Big jump |
| multi, foundational | N checks | Claude/GPT-4 | Ceiling |
| multi, oss vs single, foundational | — | Mixed | Key comparison |

The benchmark (good > less_good > wrong ordering) measures all combinations.

---

## 5. Answer and Rubric Generation Pipeline

### Phase 1 — Answer generation (external foundational LLM, T=0.7)

For each question, generate **3 variants per quality level** = 9 answers total.
Temperature variance gives coverage of different phrasings, making the rubric
robust to vocabulary variation.

Quality levels:
- **good**: complete, precise, correct, with examples
- **less_good**: correct concepts but vague, missing mechanism or example
- **wrong**: plausible-sounding but conceptually incorrect

### Phase 2 — Rubric generation (source-grounded + answer-informed)

Two sources used jointly:

| Source | Role |
|--------|------|
| Textbook chapter | Authoritative concept definitions — what *must* be understood |
| Slides | Scope boundary — what students were taught |
| 9 synthetic answers | Vocabulary grounding, discrimination signal |

Process:
1. Extract relevant textbook excerpts for the question's chapter
2. Provide slides content
3. Provide all 9 answers grouped by quality level
4. Ask LLM: generate a rubric whose checks discriminate good from less_good from wrong,
   grounded in the concepts from the textbook and the vocabulary from the answers

Note: students have access to AI and the web; they did not see the textbook.
The textbook grounds *correctness*, not *expected vocabulary*. Rubric criteria must
be vocabulary-agnostic (concept presence, not keyword presence).

### Phase 3 — Karpathy-style iterative rubric refinement

Inspired by Karpathy's autoresearch loop (modify → experiment → evaluate → keep/discard → repeat):

```
rubric = initial_rubric(question, textbook, slides, answers_train)
for iteration in range(MAX_ITER):
    scores = score_all(answers_train, rubric)
    violations = find_ordering_violations(scores)  # good < less_good OR less_good < wrong
    if no violations:
        val_scores = score_all(answers_val, rubric)
        if no violations in val_scores:
            break   # converged on held-out set — stop to avoid overfitting
    rubric = critic_llm(rubric, violations)   # LLM proposes fix
```

**Train/validation split** (overfitting guard):
- 6 answers (2 per level) used for rubric iteration
- 3 answers (1 per level, held out) used for validation
- Stop when held-out set passes, not just training set

**Rubric complexity budget** (second overfitting guard):
- Max criteria per question: configurable (e.g., 4–6)
- Max checks per criterion: configurable (e.g., 3)
- Prevents rubric from becoming a fingerprint of training answers

**Critic prompt** (the `program.md` equivalent):
- Explains what a good rubric looks like
- States the ordering constraint
- Warns against overfitting (don't add checks that only distinguish these specific answers)
- Constrains complexity budget

---

## 6. Retrieval Layer (carry forward, minimal change)

The dual-index retrieval (word_index + sentence_index) is retained as an
evidence-retrieval mechanism. Its role changes:

- **Old role**: evidence chunks used to compute `semantic_score` directly
- **New role**: evidence chunks provided as context to the LLM judge, who uses
  them to locate relevant course material when evaluating concept presence

The reranker is retained for evidence ranking.

---

## 7. Key Architectural Differences: v1 vs v2

| Aspect | v1 (current) | v2 (target) |
|--------|-------------|-------------|
| Scoring signal | keyword match + chunk count | LLM concept-presence judgment |
| Rubric content | keyword lists + descriptions | typed checks with precision levels |
| Rubric source | slides only | configurable material set (PDF/MD) + synthetic answers |
| Vocabulary dependency | high (keywords must match) | none (LLM judges meaning) |
| Partial credit | coarse (int/round/float truncation) | fine-grained (presence × precision) |
| Answer generation | manual / ad hoc | systematic (3×3, T=0.7, external LLM) |
| Rubric iteration | none | Karpathy loop with held-out validation |
| Model flexibility | oss:20b only | oss / foundational / mixed, switchable |

---

## 8. Files to Carry Into New Project

### Carry over (reuse with modification)

**Infrastructure — keep as-is or near-as-is:**
- `retrieval_core/` — entire module (index building, multi-retriever, reranker)
- `config/llm_config.py` — LLM provider abstraction (add model_tier switch)
- `config/config_loader.py`
- `grading_pipeline/index_builder.py`
- `grading_pipeline/index_builder_in_memory.py`
- `grading_pipeline/submission_loader.py`
- `grading_pipeline/submission_converter.py`
- `grading_pipeline/manifest.py`
- `grading_pipeline/transparency_logger.py`
- `grading_pipeline/models.py` — data models (extend for new rubric schema)
- `grading_pipeline/schemas.py`
- `grading_pipeline/storage.py`

**Rubric generation — refactor significantly:**
- `grading_pipeline/rubric_generator.py` — rewrite for concept-check schema
- `grading_pipeline/rubric_schema.py` — rewrite for v2 schema
- `grading_pipeline/create_dynamic_rubrics_for_each_question.py` — extend with
  textbook + answer inputs

**Scoring — replace keyword logic, add LLM judge:**
- `grading_dynamic_rubrics/pipeline.py` — replace `apply_rubric_scoring_dynamic()`
- `grader/lmql_grading.py` — extend or replace with concept-judge

**CLI — carry over, extend:**
- `grading_pipeline/cli.py`
- `grading_dynamic_rubrics/config_loader.py`

**Tests — carry over, update:**
- `tests/test_models.py`
- `tests/test_scoring.py`
- `tests/test_rubric_generator.py`
- `tests/test_check_extraction.py`

### Key content files — carry over unchanged
- `grading_pipeline/sources/slides_data_type_quality.pdf`
- `grading_pipeline/submissions/student_001_q0{1-5}_{good,less_good,wrong}.yaml`
- `grading_dynamic_rubrics/config/sources.yaml`
- `ten_questions.md`

### Documentation — carry over
- `CLAUDE.md`, `AGENT.md` — project rules
- `grade-spec.md` — grading authority hierarchy
- `USAGE.md` — update for v2 workflow
- `docs/DESIGN.md`, `docs/REFERENCES.md`
- `retrieval_core/README.md`
- `grading_pipeline/README.md`
- `t4_3_report.md` — baseline benchmark results

### Do NOT carry over (obsolete)
- All `IMPLEMENTATION_*.md`, `IMPLEMENTATION_STATUS*.md` files — historical
- All `plan_*.md`, `*.plan.md` — superseded
- `grader/grade_question.py` — keyword logic being replaced
- `grading_pipeline/keyword_extractor.py`, `keyword_store.py` — replaced by LLM judge
- `version1/` — superseded
- `mwe/` — scratch work
- `results/`, `my_results*/`, `reranker_results/` — run artifacts
- `tmp*/`, `pytest-of-*/` — scratch

---

## 9. Open Questions — Resolved

1. **Source material format** *(resolved)*: No textbook added to the project.
   Instead, the pipeline accepts a configurable set of markdown and/or PDF files
   associated with a given set of questions. The caller provides the relevant
   materials; the pipeline does not assume a fixed source structure. This allows
   per-assignment flexibility and future extension without refactoring.

2. **Source-to-question mapping** *(resolved)*: Irrelevant given answer to Q1.
   The caller provides the files relevant to the questions being graded.

3. **External LLM for answer/rubric generation** *(resolved)*: Settable, defaulting
   to **Gemini Flash** (fast, no deep reasoning required for this task). Provider
   and model are set via config YAML and overridable on the command line.

4. **Iteration budget** *(resolved)*: `--max-iterations` command-line argument,
   default value defined in `config/rubric_generation.yaml`. This allows
   experiments to be scripted by varying the flag without code changes.

5. **Complexity budget** *(resolved)*: Maximum **4 checks per criterion**,
   configurable downward. Defined in `config/rubric_generation.yaml`.

6. **Scoring representation** *(resolved)*: Two modes, chosen based on check count:
   - **Float scores** (0.0–1.0 per check) when check count is low (≤4 checks/criterion)
   - **Binary scores** (0/1 per check) when check count is higher
   Both modes use `float` internally throughout; no `int()` truncation anywhere.
   Mode is configurable in `config/rubric_generation.yaml`.

---

## 10. New Design Element — Question Types

A key addition not in the original design: questions can be catalogued into
**question types**, of which there are approximately 10. This serves two purposes:

1. **Reusable example banks**: positive and negative examples (for precision scoring)
   are difficult to define reliably if the rubric changes per question. Anchoring
   examples to a question type makes them reusable and stable across questions of
   the same type.

2. **Type-specific rubric templates**: the LLM rubric generator receives a
   question-type template as a prior, constraining the structure of generated
   checks and examples to patterns that work for that type.

### Candidate question types (to be refined)

| Type | Description | Example questions |
|------|-------------|-------------------|
| `definition` | Define a term precisely | "What is an object in a data table?" |
| `distinction` | Contrast two related concepts | "Difference between interval and ratio scale?" |
| `mechanism` | Explain why something works/fails | "Why can't you compute ratios on Celsius?" |
| `classification` | Assign items to categories | "Classify: zip code, age, temperature" |
| `enumeration` | List properties or operations | "What operations are valid on ordinal data?" |
| `example_generation` | Produce a valid example | "Give an example of a nominal attribute" |
| `error_identification` | Find what's wrong in a claim | "What is wrong with averaging Likert scores?" |
| `comparison` | Compare two approaches/methods | "Compare symmetric vs asymmetric similarity" |
| `application` | Apply concept to new scenario | "Which scale is GPA? Justify." |
| `proof_or_argument` | Construct a logical argument | "Argue why ratio scale supports all operations" |

### Impact on rubric generation

- The rubric generator receives `question_type` as an input parameter
- Type-specific prompt templates guide check generation
- Example banks (positive/negative) are stored per type and reused across questions
- The Karpathy iteration loop operates within type constraints, reducing
  the search space and overfitting risk
