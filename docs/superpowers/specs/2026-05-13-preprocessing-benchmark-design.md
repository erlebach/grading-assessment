# Gold Preprocessing Benchmark — Design

**Status:** DRAFT — brainstorming in progress, started 2026-05-13.
**Author/Driver:** erlebach (with Claude)
**Supersedes (in part):** `docs/superpowers/specs/2026-05-12-v2-self-contained-benchmark-design.md`

> This document is being written **as the design is agreed, section by section**, so that no work is lost if the session is interrupted. Sections marked DRAFT below have been ratified in conversation. Sections marked PENDING are still to be discussed.

---

## 0. Goal and framing

Build a preprocessing pipeline that uses **foundational models** (Claude by default, model-agnostic via tier dispatch) to produce **frozen gold-standard artifacts**:

- Universal-layer rubrics (one per question type, calibrated once)
- Per-question rubrics (concept overlay + weights)
- Synthetic answers at three quality levels (good / less_good / wrong), plus axis-perturbation answers for diagnostic discrimination
- Gold per-concept coverage annotations on every synthetic answer
- Gold reference scores from a Claude-driven concept judge

These artifacts become a **benchmark**: future cheaper grading approaches (OSS judges, smaller models, retrieval-only, etc.) will be evaluated by how closely they reproduce the gold scores and concept votes on the same synthetic answers under the same rubrics.

### Key framing decisions (DRAFT — agreed)

- **Optimization target:** artifact quality, not runtime cost. The whole pipeline is preprocessing — runtime cost is out of scope here.
- **Grading philosophy:** grade *concepts*, not keywords (unless a question is explicitly about specific keywords).
- **Reusability:** the universal layer is **content-independent by construction**. It is never calibrated on a single course; it always uses cross-topic seed questions (curated, source-derived, or Claude-knowledge-generated). The user vetoed single-course bootstrap.
- **Reproducibility:** every run is fully self-contained on disk, including a source-code snapshot. A future researcher can reproduce a run with no access to the original git repository.

### Explicit non-goals

- **Real student answers.** Out of scope. Synthetic answers are the gold reference; real-student grading is a downstream consumer.
- **Question generation.** Questions are user-curated YAML. The pipeline consumes; it does not invent.
- **Retrieval / chunking.** Slide deck is short enough that whole-markdown context plus prompt caching is sufficient. If a future source PDF is too large, swap in `retrieval_core/` at the affected stages without touching the rest.
- **Runtime / on-line rubric refinement.** All refinement happens during preprocessing. Output is frozen.
- **Karpathy-loop's ordering-only criterion.** Superseded by concept-vote + score bands + axis discrimination (see §4).

---

## 1. Pipeline architecture (DRAFT — agreed)

Linear chain of **five stages**, each producing frozen on-disk artifacts that the next stage consumes. No stage re-processes upstream source material; each loads its inputs from disk and writes its outputs to disk.

| # | Stage | Run cadence | Reads | Writes |
|---|---|---|---|---|
| 0 | `translate_sources` | Once per source file | a PDF *or* markdown file | `sources/<source_name>/{content.md, meta.yaml, figures/}` |
| 1 | `prepare_seed_questions` | Once per type catalog change | translated sources + Claude general knowledge + type catalog | `seed_questions/<type>/<seed_id>.yaml` |
| 2 | `calibrate_types` | Once total (re-run when type catalog, criterion, or seed pool changes) | seed-question pool | `types/<type>/{universal_rubric.yaml, calibration_meta.yaml}` |
| 3 | `generate_rubric` | Once per assessment question | frozen universal rubric for the question's type + the question + relevant translated source(s) | `rubrics/<course>/<q>/rubric.yaml`, `synthetic_answers/<course>/<q>/answers.yaml`, `gold_concept_coverage` |
| 4 | `gold_grade` | Once per assessment question (after Stage 3) | per-question rubric + synthetic answers | `grades/<course>/<q>/grades.yaml` |

### Flow

```
sources/*.{pdf,md}
        │
        ▼
┌─────────────────────────┐
│ 0 translate_sources     │  PDF: Claude w/ vision → markdown + figures.
│                         │  Markdown: passthrough into canonical layout.
└──────────┬──────────────┘
           ▼
sources/<source_name>/{content.md, meta.yaml, figures/}
           │
           ▼
┌─────────────────────────┐
│ 1 prepare_seed_questions│  K seeds per type, ≥ J topical domains.
│                         │  Sources: curated YAML / source-derived / Claude-knowledge.
└──────────┬──────────────┘
           ▼
seed_questions/<type>/*.yaml
           │
   ┌── user review gate ──┐
   ▼                      │
┌─────────────────────────┐
│ 2 calibrate_types       │  Concept-vote + score bands + axis discrimination.
│                         │  Outputs frozen universal layer per type.
└──────────┬──────────────┘
           ▼
types/<type>/{universal_rubric.yaml, calibration_meta.yaml}
           │
           ▼
┌─────────────────────────┐
│ 3 generate_rubric       │  Per assessment question. Uses frozen universal layer
│                         │  + translated source(s) + question text.
└──────────┬──────────────┘
           ▼
rubrics/<course>/<q>/rubric.yaml
synthetic_answers/<course>/<q>/answers.yaml + gold_concept_coverage
           │
           ▼
┌─────────────────────────┐
│ 4 gold_grade            │  Claude judge applies rubric to synthetic answers.
└──────────┬──────────────┘
           ▼
grades/<course>/<q>/grades.yaml   (the benchmark output)
```

Every Claude call across all stages writes JSONL to `traces/<stage>/`.

### Invocation

Each stage is a separate CLI module, independently runnable, idempotent:

```bash
python -m preprocessing.translate_sources <source_path>
python -m preprocessing.prepare_seed_questions [--types DEFINITION,MECHANISM,...]
python -m preprocessing.calibrate_types
python -m preprocessing.generate_rubric --course data_quality --question Q03
python -m preprocessing.gold_grade --course data_quality --question Q03
```

A wrapper `python -m preprocessing.run_course --course data_quality` runs Stages 3 + 4 for every question in the course (Stage 0–2 are explicit prerequisites).

---

## 2. Run isolation, folder layout, reproducibility (DRAFT — agreed)

Every invocation produces its own top-level **run folder** containing all artifacts from all stages that ran. Different runs are sibling folders. Nothing is overwritten. Comparison is folder-tree diff plus YAML-aware semantic diff helpers.

This is the W&B-style "every run is a top-level isolation boundary" model.

### Run folder layout

```
preprocessing/
  runs/
    2026-05-13_13-15-00Z__abc1/                  # one run folder
      sources/
        <source_name>/
          content.md
          meta.yaml                              # format, courses, topics, extraction model + ts
          figures/
            fig_001.png
            ...
      seed_questions/
        <type>/
          <seed_id>.yaml                         # {question, type, topic, source, notes}
      types/
        <type>/
          universal_rubric.yaml                  # frozen calibrated rubric (axes + weights)
          calibration_meta.yaml                  # which seeds, iterations, criterion outcomes
      rubrics/
        <course>/
          <question_id>/
            rubric.yaml                          # per-question concept overlay + weights
      synthetic_answers/
        <course>/
          <question_id>/
            answers.yaml                         # good / less_good / wrong + axis-perturbation
            gold_concept_coverage.yaml           # Claude-annotated per-concept coverage per answer
      grades/
        <course>/
          <question_id>/
            grades.yaml                          # gold reference scores from Claude judge
      traces/
        translate_sources/*.jsonl
        prepare_seed_questions/*.jsonl
        calibrate_types/*.jsonl
        generate_rubric/*.jsonl
        gold_grade/*.jsonl
      run_meta.yaml                              # see schema below
      config.yaml                                # the config that drove this run
      src_snapshot.tar.gz                        # full source tree at run time
      REPRODUCE.md                               # exact commands used in this run
    2026-05-14_09-22-31Z__def6/
      ...same shape...
```

### Run ID format

`YYYY-MM-DD_HH-MM-SSZ__<4-char-fingerprint>` — e.g. `2026-05-13_13-15-00Z__abc1`.

- Timestamp matches the format used in `.specstory/history/`, so you can correlate a run with the chat session that produced it via substring grep.
- Fingerprint = `SHA8(model_id, tier, sorted_input_artifact_run_ids, stage_config)[:4]`. Same fingerprint across two runs means "semantically identical inputs and config" — useful for detecting accidental reproductions.

### CLI run resolution

`--run <prefix>` (git-style prefix matching):

- `--run 2026-05-13_13-15-00Z__abc1` — exact match.
- `--run 2026-05-13_13-15-00Z` — matches the timestamped run even without the fingerprint suffix.
- `--run 2026-05-13` — matches anything from that date; errors with a list if multiple.

Scripts default to "most recent run" when `--run` is omitted (`max(glob runs/*)`).

### Reproducibility — two independent paths

Every run records both, so reproduction works even if one path fails:

1. **Tarball path (always works):** `runs/<id>/src_snapshot.tar.gz` contains the working tree at run time (preprocessing source, root `pyproject.toml`, `.python-version`, lockfile, etc.), excluding `.git/`, `.venv/`, `__pycache__/`, `.specstory/`, `runs/`. Reproduction:
   ```bash
   tar xzf runs/<X>/src_snapshot.tar.gz -C /tmp/rerun_X
   cd /tmp/rerun_X && uv sync
   python -m preprocessing.<stage> --config runs/<X>/config.yaml ...
   ```
2. **Git path (when `.git` is intact and matches):** `run_meta.yaml` records `git_sha` and `git_dirty: bool`. If clean and the repo is reachable, `git checkout <sha>` and re-run.

`runs/<id>/REPRODUCE.md` lists the exact CLI commands used during the run, so re-running is mechanical.

### What's NOT in the layout (and why)

- **No `promoted.yaml` / `latest.yaml` pointer files.** Which run is "the benchmark" is decided by external agreement (PR description, README), not a system pointer.
- **No `preprocessing.gc`.** Runs are immutable; `rm -rf` when you want to clean.
- **No per-artifact-scope versioning.** Versioning happens at the run level.

### Future enhancement (NOT implemented now, design noted)

**Content-addressed source cache.** When PDF translation becomes expensive or the source library grows, introduce `preprocessing/cache/sources/<content_sha>/` outside `runs/`. Each run's `sources/<source>/meta.yaml` records `content_sha`; if the cache has a hit, the run links/copies from cache instead of re-translating. Out of scope for the first implementation.

### Comparison tooling (DRAFT — agreed)

`python -m preprocessing.diff <run_a> <run_b>` — thin wrapper around recursive folder diff plus YAML-aware semantic diff for each artifact type:

- **Sources**: diff `meta.yaml` keys and `content.md` line counts.
- **Seed questions**: added/removed/edited seeds, topic-domain coverage diff.
- **Universal rubrics**: axes added/removed, weight deltas with magnitude flags, calibration iteration count, criterion-pass outcomes.
- **Per-question rubrics**: concept-list diff, concept-weight diff.
- **Synthetic answers + coverage**: which answers changed, gold-coverage stability.
- **Grades**: per-answer score deltas, mean/std shifts, ordering preserved?, criterion still satisfied?

Output: human-readable table (default), JSON, or markdown report.

---

## 3. Data model / YAML schemas (DRAFT — agreed)

### 3.0 Taxonomy — inputs vs outputs inside a run folder

```
<run>/
  inputs/                                  # everything the run consumed
    sources_raw/<source>/<original>.pdf    # original PDFs or .md (verbatim)
    type_catalog.yaml                      # list of 10 types + candidate axes
    questions/<course>/<q>.yaml            # assessment question definitions
    seed_questions_curated/<type>/*.yaml   # any user-curated seeds
  sources/<source>/{content.md, meta.yaml, figures/}   # Stage 0 output
  seed_questions/<type>/*.yaml             # Stage 1 output (curated + generated, normalized)
  types/<type>/{universal_rubric.yaml, calibration_meta.yaml}   # Stage 2
  rubrics/<course>/<q>/rubric.yaml         # Stage 3
  synthetic_answers/<course>/<q>/{answers.yaml, gold_concept_coverage.yaml}  # Stage 3
  grades/<course>/<q>/grades.yaml          # Stage 4
  traces/<stage>/*.jsonl
  run_meta.yaml, config.yaml, src_snapshot.tar.gz, REPRODUCE.md
```

### 3.1 Vocabulary

- **Type** — a question category. There are 10: DEFINITION, DISTINCTION, MECHANISM, CLASSIFICATION, ENUMERATION, EXAMPLE_GENERATION, ERROR_IDENTIFICATION, COMPARISON, APPLICATION, PROOF_OR_ARGUMENT. Every question has exactly one type.
- **Axis** — a sub-dimension of one type's universal rubric. E.g., MECHANISM's axes = `{causal_chain_correctness, temporal_ordering, completeness, component_dependencies}`. Defined per type; never shared across types (even when names repeat, they are independent entries with independent weights and criteria).
- **Concept** — a content-specific item the per-question rubric demands. E.g., Q03's concepts = `{schema_drift_definition, detection_mechanism_versioning, …}`. Specific to one question. A concept's `relevant_axes` is a non-empty subset of *its question's type's* axes.
- **Score level** — one of `full | partial | none`, with fixed global values `{full=1.0, partial=0.5, none=0.0}`. The *criterion* for each level is rubric-defined per axis.

### 3.2 Contract schemas

**(a) `types/<type>/universal_rubric.yaml`** — calibrated universal layer (one file per type, ten files total):

```yaml
type: MECHANISM
status: frozen
axes:
  - name: causal_chain_correctness
    description: "Are causes correctly linked to effects in the right direction?"
    weight: 0.35
    score_levels:
      full:    { value: 1.0, criterion: "All causal links correct and explicit." }
      partial: { value: 0.5, criterion: "Some links correct but 1-2 incorrect or ordering unclear." }
      none:    { value: 0.0, criterion: "Multiple incorrect or missing causal links." }
  - name: temporal_ordering
    weight: 0.25
    ...
aggregate:
  method: weighted_mean
  out_of: 10.0
```

Axis weights within a single type's universal rubric MUST sum to 1.0 (within ε).

**(b) `rubrics/<course>/<q>/rubric.yaml`** — per-question concept overlay:

```yaml
question_id: Q03
course: data_quality
type: MECHANISM
universal_rubric_ref: types/MECHANISM/universal_rubric.yaml
concept_overlay:
  - id: schema_drift_definition
    text: "Defines schema drift as changes in data structure over time."
    weight: 0.30
    relevant_axes: [causal_chain_correctness, completeness]   # subset of MECHANISM's axes
  - id: detection_mechanism_versioning
    text: "Identifies version-tracking as a detection mechanism."
    weight: 0.25
    relevant_axes: [causal_chain_correctness]
  ...
status: frozen
```

Concept weights MUST sum to 1.0 (within ε). Every `relevant_axes` MUST be a non-empty subset of the referenced universal rubric's axis names.

**(c) `grades/<course>/<q>/grades.yaml`** — gold reference scores:

```yaml
question_id: Q03
rubric_ref: rubrics/data_quality/Q03/rubric.yaml
universal_rubric_ref: types/MECHANISM/universal_rubric.yaml
grades:
  - answer_id: good_1
    per_concept:
      schema_drift_definition: { causal_chain_correctness: full, completeness: full }
      detection_mechanism_versioning: { causal_chain_correctness: full }
      ...
    aggregate: 0.895
    aggregate_x10: 8.95
  - answer_id: less_good_1
    per_concept: { ... }
    aggregate: 0.55
    aggregate_x10: 5.5
  - answer_id: axis_perturb_causal_chain_correctness
    per_concept: { ... }
    aggregate: 0.58
    aggregate_x10: 5.8
    target_axis_drop_observed: 0.42
summary:
  mean_by_quality:
    good: 0.97
    less_good: 0.55
    wrong: 0.13
    axis_perturbation: 0.62
  ordering_preserved: true
  bands_satisfied: true
  axis_discrimination_passed: true
```

### 3.3 Aggregation formula

For a single answer, given the judge's per-(concept, axis) level votes:

```
# Step 1: score each concept by averaging over its relevant axes, weighted by universal axis weights
score(c) = Σ over a ∈ relevant_axes(c):
              universal_axis_weight(a) × level_value(judge_vote(c, a))
           / Σ over a ∈ relevant_axes(c):
              universal_axis_weight(a)

# Step 2: aggregate across concepts using concept weights
aggregate_raw = Σ over c: concept_weight(c) × score(c)
              / Σ over c: concept_weight(c)

aggregate_x10 = aggregate_raw × 10
```

Worked example (Q03, answer `good_1`, with universal axis weights `{causal=0.35, temporal=0.25, completeness=0.25, deps=0.15}` and concept weights `{C1=0.30, C2=0.25, C3=0.20, C4=0.25}`, judge votes giving C1=1.0, C2=1.0, C3=0.708, C4=0.813):

```
aggregate_raw = 0.30×1.000 + 0.25×1.000 + 0.20×0.708 + 0.25×0.813 = 0.895
aggregate_x10 = 8.95
```

### 3.4 Score-band targets (calibration parameter; tunable)

```yaml
score_bands:
  good:      [0.85, 1.00]
  less_good: [0.40, 0.70]
  wrong:     [0.00, 0.30]
```

Deliberate gaps `(0.70, 0.85)` and `(0.30, 0.40)` force genuine discrimination.

### 3.5 Other schemas (mechanical)

- `inputs/type_catalog.yaml` — 10 types with description + candidate_axes.
- `inputs/questions/<course>/<q>.yaml` — `{question_id, course, type, text, sources, notes}`.
- `inputs/seed_questions_curated/<type>/<id>.yaml` and `seed_questions/<type>/<id>.yaml` — `{seed_id, type, topic, source, text, generated_by, user_review}`.
- `types/<type>/calibration_meta.yaml` — full iteration history (per-iteration weights, criterion outcomes, refinement proposals, final pass).
- `synthetic_answers/<course>/<q>/answers.yaml` — list of answers tagged by quality (`good | less_good | wrong | axis_perturbation`), with `target_axis` on perturbations.
- `synthetic_answers/<course>/<q>/gold_concept_coverage.yaml` — per-answer-per-concept-per-axis Claude annotation, plus `target_axis_weakness` for perturbations.
- `sources/<source>/meta.yaml` — `{format, courses, topics, extraction model+ts, content_sha, figure_count, page_count}`.
- `config.yaml` and `run_meta.yaml` — sketched in §2.

### 3.6 Invariants and validators

All scores positive, totals in `[0, 10]`, by construction. Validators enforce explicitly at every artifact boundary:

- `validate_universal_rubric`: axis weights ≥ 0; `Σ = 1.0 ± ε`; level values monotone (`full > partial > none`); all three levels present with explicit criteria; aggregate.out_of > 0.
- `validate_per_question_rubric`: concept weights ≥ 0; `Σ = 1.0 ± ε`; every `relevant_axes` non-empty and ⊆ universal axes.
- `validate_grade`: every (concept, axis) pair from rubric is graded; levels ∈ `{full, partial, none}`; `aggregate ∈ [0, 1]`; `aggregate_x10 ∈ [0, 10]`; `aggregate_x10 = aggregate × 10 ± ε`.
- Any failure halts the run with a hard error; trace records the offending file path and field.

---

## 4. Stage details (DRAFT — agreed)

### 4.0 Universal contracts

Every stage:
- Validates inputs at load time using the §3.6 validators.
- Writes outputs into the active run folder (`runs/<run_id>/...`).
- Streams one JSONL trace record per Claude call into `traces/<stage>/calls.jsonl` (full prompt + full response, no truncation).
- Hard errors on schema violations or invariant failures (halts run; trace records offending file).
- Soft errors on per-item failures (one synthetic answer failed to generate, one seed validation timed out): log it, continue with the rest, mark the affected artifact `status: partial`.
- Supports `--run <prefix>` for resolving run folder; defaults to most recent run if omitted.

**Persistence policy (applies to every stage):** *nothing inside a run folder is ever discarded by the pipeline.* "Throwaway" artifacts — Stage 2's per-seed concept overlays, every iteration's intermediate rubric + judge outputs + critic proposals, Stage 3's overlay refinement iterations — are all persisted as their own files. The downstream pipeline may not read them, but the user can. Disk is cheap; auditability is not.

### 4.1 Stage 0 — `translate_sources` (one invocation per source file)

**Purpose**: convert each input source (PDF or markdown) into canonical markdown + page-level figure snapshots.

**For PDFs:**
1. `pymupdf` renders every page to `figures/page_NNN.png` (3-digit zero-padded). Page-level snapshots are lossless — they preserve all visual content for downstream stages that need visual grounding (e.g., "what does the diagram show" questions). Per-figure crops are a future enhancement.
2. One Claude vision call reads the PDF (full doc as attachment) and outputs `content.md`. The markdown includes `[Figure: page_NNN]` markers where a page is visually load-bearing. Otherwise plain text/headings/code blocks/tables.
3. `meta.yaml` records `format: pdf`, `page_count`, `figure_count`, `content_sha` (of resulting markdown), `extraction.model`, `extraction.ts`, `extraction.tier`.

**For markdown inputs:**
1. Read input. Optional light validation (front matter, heading structure).
2. Copy verbatim to `content.md`. No figures unless inline image links exist (those images are then copied too).
3. `meta.yaml` with `format: markdown`.

**Source naming**: `<source_name>` = input filename stem, lowercased + snake_cased. `--name` CLI arg overrides on collision.

**Knobs (config.yaml)**: vision model id, output verbosity (terse / detailed markdown), figure inclusion threshold (always / on-detection / never).

### 4.2 Stage 1 — `prepare_seed_questions`

**Purpose**: build a cross-topic seed-question pool, K seeds per type, ≥ J topical domains.

**Composition** (configurable per type in `config.yaml`):
```yaml
seeds_per_type:
  default: 8
  composition:
    from_user_curated: 2       # read verbatim from inputs/seed_questions_curated/<type>/
    from_source: 2             # Claude extracts/invents from a translated source
    from_claude_knowledge: 4   # Claude generates from general knowledge
```

Shortfalls in `from_user_curated` rebalance into `from_claude_knowledge`.

**Claude-knowledge generation** (one batched call per type):
```
TASK: Generate <N> distinct <TYPE> questions matching the criterion: <type_description>.

DIVERSITY REQUIREMENT: span ≥ <J> distinct topical domains. Suggested domains:
biology, history, physics, economics, literature, chemistry, engineering, sociology,
mathematics, programming, philosophy, medicine.

CONSTRAINTS:
- Each question must be a clear <TYPE> question (not just adjacent).
- Self-contained (no external context required).
- Avoid politically charged or sensitive topics.

OUTPUT (JSON array): [ { "topic": "...", "text": "...", "rationale": "..." }, ... ]
```

**Source-derived generation**: same prompt, but with a translated source's `content.md` in the cached prefix and "draw questions from the material below" replacing the diversity instruction.

**Validation pass** (Claude, second call per seed batch): scores "is this a well-formed <TYPE> question? yes / no / borderline + rationale". Borderline + no are flagged for user review.

**User review gate** (CLI):
```
python -m preprocessing.review_seeds --type MECHANISM [--accept-all]
```
Interactive (or batch with `--accept-all` if trusted). Each seed's `user_review.approved` is set to `true | false`. Stage 2 only loads `approved == true`.

**Knobs**: `seeds_per_type`, `topical_domains_min` (J), `composition` shares, `validation_pass_enabled`.

### 4.3 Stage 2 — `calibrate_types` (per type; produces frozen universal layer)

**Per-type algorithm:**

1. **Initialize**: candidate axes from `type_catalog.yaml`; uniform weights; Claude drafts initial `score_levels.{full, partial, none}.criterion` from the type description.

2. **Materialize per-seed scoring set** (for each approved seed of this type):
   - **Synthetic answers**: 3 good + 3 less_good + 3 wrong (Claude, one call per quality level).
   - **Axis-perturbation answers**: 1 per candidate axis (Claude, one call per axis; the prompt holds all other axes high while weakening the target).
   - **Throwaway per-seed concept overlay** (Claude, one call): 2-5 concepts with weights + `relevant_axes` referencing candidate universal axes. Used only for calibration scoring; never frozen. Persisted only in `calibration_meta.yaml` for audit.
   - **Gold concept coverage** (Claude, one call per answer): per-(concept, axis) labels.

3. **Train / val / test split**: 60 / 20 / 20 over approved seeds, deterministic by `SHA(seed_id)`.
   - **Train**: critic uses these failure cases to propose refinements.
   - **Val**: iteration stop signal — criterion must pass on val to declare calibration done.
   - **Test**: never touched during calibration. Used only in the held-out test pass below.

4. **Iterate** (≤ `max_iterations`, default 6):
   - Apply candidate universal rubric (with each seed's throwaway overlay) via the judge to all val-set answers.
   - Compute three criteria:
     - **Concept-vote agreement** ≥ 0.85 — fraction of (concept, axis) pairs where judge label == gold label.
     - **Score-band satisfaction** ≥ 0.90 — fraction of answers landing in their quality-level's target band.
     - **Axis discrimination** — for each axis-perturbation answer, the targeted axis must show a clearly lower per-pair score than non-target axes. Quantified as: target-axis mean score < non-target-axes mean score by at least 0.25.
   - If all three pass on val → exit loop (proceed to held-out test pass).
   - Else: Claude critic call. Critic sees current rubric + outcomes + concrete failures from the **train** set (e.g., "axis X showed 'full' but gold was 'partial' on 8 of 12 less_good answers"). Critic returns proposed revisions to weights and/or level criteria. Apply revisions; record in `calibration_meta.yaml`.

5. **Held-out test pass** (after the iteration loop exits, with the candidate-now-frozen rubric):
   - Apply the rubric to the **test** set (never seen during iteration).
   - Compute the same three criteria.
   - Write `types/<type>/test_results.yaml` with test-set outcomes.
   - **Status tagging**:
     - All three test-set criteria pass → `universal_rubric.yaml: status: frozen`.
     - Any test-set criterion fails → `universal_rubric.yaml: status: warning_test_marginal`. The rubric is still written (auditable), but Stage 3 will refuse to consume it without an explicit override.

6. **Output** (every artifact persisted; nothing discarded):
   - `types/<type>/universal_rubric.yaml` — final frozen (or warning) rubric.
   - `types/<type>/calibration_meta.yaml` — summary log: train/val/test seed list, per-iteration outcomes, final outcomes, `limitation_notes`.
   - `types/<type>/test_results.yaml` — held-out test seed list + per-criterion outcomes.
   - `types/<type>/seed_artifacts/<seed_id>/` — one folder per approved seed, containing:
     - `concept_overlay.yaml` (the throwaway per-seed overlay)
     - `synthetic_answers.yaml` (9 quality answers + axis perturbations)
     - `gold_concept_coverage.yaml` (Claude-annotated gold labels)
   - `types/<type>/iterations/iter_NN/` — one folder per calibration iteration, containing:
     - `candidate_rubric.yaml` (rubric at start of this iteration)
     - `val_judge_outputs.yaml` (judge labels on val set)
     - `val_criterion_outcomes.yaml` (the three criteria, evaluated)
     - `critic_proposal.yaml` (critic's suggested revisions, if iteration didn't pass)

7. **Failure modes**:
   - Max iterations reached without val pass → `status: failed_to_converge`, halt the run.
   - Val pass but test fails → `status: warning_test_marginal`, run halts at the universal layer; Stage 3 will not proceed without `--proceed-on-warning`.

8. **Standalone test CLI**: `python -m preprocessing.test_universal --type MECHANISM [--seeds <N>]` runs an additional ad-hoc test pass against fresh Claude-generated seeds (not in the original pool). Useful as a sanity check before kicking off a batch of per-question runs in Stage 3. Writes `types/<type>/adhoc_test_<timestamp>.yaml`; does not modify `status`.

**Knobs**: `max_iterations`, split ratios (`train/val/test`), three criterion thresholds, critic prompt strategy, perturbation magnitude expectation, `proceed_on_warning`.

### 4.4 Stage 3 — `generate_rubric` (per assessment question; produces frozen per-question artifacts)

Reuses §4.3 machinery but with a **frozen** universal rubric. Universal layer is immutable in this stage; only the per-question overlay is iterated.

**Pre-flight check**: Stage 3 reads `types/<type>/universal_rubric.yaml` at startup. If `status: warning_test_marginal`, Stage 3 **refuses to run** unless `--proceed-on-warning` is set. If `status: failed_to_converge`, Stage 3 refuses outright (no override). This is the guard rail: a fundamentally bad universal rubric does not get to corrupt downstream per-question artifacts silently.

**Per-question algorithm:**

1. Load `inputs/questions/<course>/<q>.yaml`. Load frozen `types/<type>/universal_rubric.yaml` for the question's type.

2. **Generate synthetic answers**:
   - 3 good (grounded in the source material listed in the question's `sources:` field; Claude has the relevant `content.md` in the cached prefix).
   - 3 less_good (partially correct; missing or weak on some concepts).
   - 3 wrong (off-direction or off-topic).
   - 1 axis-perturbation per universal axis for this type (benchmark integrity check, not used as a calibration signal here since universal is frozen).

3. **Generate concept overlay** (Claude, one call): given question + answer set + universal axes for this type, propose 2-5 concepts with weights (summing to 1.0) and `relevant_axes` (each a non-empty subset of universal axes).

4. **Annotate gold concept coverage** (Claude, one call per answer): per-(concept, axis) labels.

5. **Sanity-check** (apply judge with rubric to all answers, then check ordering + bands hold):
   - If pass: proceed.
   - If fail: refine **only the concept overlay** (weights or `relevant_axes`). Universal layer untouchable. Max `overlay_refinement_iterations`, default 3.
   - On exhaustion: write rubric with `status: degraded`, halt the run. Many `degraded` per-question rubrics ⇒ signal to re-run Stage 2 with a broader seed pool.

6. **Output** (every artifact persisted; nothing discarded):
   - `rubrics/<course>/<q>/rubric.yaml` (final frozen overlay).
   - `synthetic_answers/<course>/<q>/answers.yaml`.
   - `synthetic_answers/<course>/<q>/gold_concept_coverage.yaml`.
   - `rubrics/<course>/<q>/iterations/iter_NN/` — one folder per overlay refinement iteration, each containing:
     - `candidate_overlay.yaml`
     - `judge_outputs.yaml`
     - `criterion_outcomes.yaml`
     - `refinement_proposal.yaml`

**Knobs**: per-quality answer count, axis-perturbation count per question, `overlay_refinement_iterations`.

### 4.5 Stage 4 — `gold_grade` (per question; produces gold reference scores)

**Judge call** — one Claude call per synthetic answer, batches all (concept, axis) pairs:

```
SYSTEM: You are a careful grader. For each (concept, axis) pair below, classify the
answer's coverage as "full" / "partial" / "none" using the per-axis criteria provided.

INPUT (cached prefix):
  Source content: <content.md inline>
  Universal rubric for <TYPE>: { axes + score_levels }
  Per-question rubric for <Q_ID>: { concepts + relevant_axes }

INPUT (variable per call):
  Answer text: <one synthetic answer>

OUTPUT (JSON array, one entry per (concept, axis) pair):
  [
    { "concept_id": "...", "axis": "...", "level": "full" | "partial" | "none",
      "rationale": "<1-2 sentences>" },
    ...
  ]
```

**Design choices**:
- One call per answer (batches all pairs). Internal consistency > per-pair isolation; cost lower; cache hits the prefix.
- Rationale per pair mandatory; stored in `traces/gold_grade/<call_id>.jsonl` AND propagated into `grades.yaml` per pair.
- Prompt caching for the prefix (source + both rubrics). Subsequent answers in the same run hit cache at ~10% of full input cost.

**Per-question summary** (computed from the grades, written into `grades.yaml`'s `summary` block):
- `mean_by_quality`: average aggregate per quality level (good / less_good / wrong / axis_perturbation).
- `ordering_preserved`: mean(good) > mean(less_good) > mean(wrong)?
- `bands_satisfied`: all answers in their target band?
- `axis_discrimination_passed`: each axis-perturbation drop targeted right axis?

**Failure mode at Stage 4**: if `bands_satisfied == false` or `ordering_preserved == false`, this question's benchmark output is flagged `degraded` in the run summary. The run continues for other questions (a single bad question doesn't kill the whole gold pipeline).

### 4.6 Stage glue and `run_course` wrapper

`python -m preprocessing.run_course --course data_quality` runs **Stages 3 + 4 for every question in the course's questions list**, in parallel where allowed (subject to API rate limits). Stages 0–2 are explicit prerequisites — `run_course` checks the run folder for their outputs and refuses to start if any are missing.

The wrapper writes a course-level summary at `runs/<id>/summary_<course>.yaml`:
- per-question pass/degrade status,
- aggregate grades by quality level across all questions,
- total Claude calls, tokens, cost,
- elapsed time per stage.

## 5. Tracing and retry infrastructure (DRAFT — agreed)

### 5.1 JSONL trace record schema

One file per stage per run: `runs/<id>/traces/<stage>/calls.jsonl`. One JSONL record per Claude call, full prompt and full response, no truncation.

```jsonl
{
  "call_id": "01HXYZAB...",                        // ULID, sortable
  "ts_start": "2026-05-13T13:15:01.234Z",
  "ts_end":   "2026-05-13T13:15:33.567Z",
  "latency_ms": 32333,
  "stage": "calibrate_types",
  "sub_operation": "iter_3_critic_MECHANISM",      // descriptive sub-call label
  "model": "claude-opus-4-7",
  "tier": "foundational",
  "request": {
    "system": "<full system prompt text>",
    "messages": [
      { "role": "user", "content": [<full content blocks>] }
    ],
    "max_tokens": 4096,
    "temperature": 0.0,
    "cache_control_markers": [<positions>]
  },
  "response": {
    "stop_reason": "end_turn",
    "content": [<full output content blocks>],
    "text": "<extracted text concatenation if applicable>"
  },
  "usage": {
    "input_tokens": 4521,
    "output_tokens": 892,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 4200
  },
  "retry_count": 0,
  "attempts": [...],                               // populated on retried calls
  "status": "success",                             // success | error_transient | error_permanent | error_parse
  "error": null                                    // or { type, message, http_status }
}
```

**Large-prompt handling**: if a single trace record exceeds 10 MB (e.g., a vision call with a very large attached PDF), the request payload is moved to `traces/<stage>/large/<call_id>.json` and the JSONL record stores `request_ref: large/<call_id>.json` instead. The response is always inlined.

### 5.2 Retry policy

- **3 attempts per call** with exponential backoff: 5s, 15s, 45s.
- **Retry on**: `httpx.ReadTimeout`, `httpx.ConnectError`, HTTP 5xx, HTTP 429 (rate limit; `Retry-After` honored if present).
- **Don't retry on**: HTTP 4xx (other than 429), schema validation failure on our request construction.
- **JSON-parse failures on response**: 1 retry with a "your previous response was not valid JSON; return only the requested JSON" reminder appended; then hard fail. Recorded with `status: error_parse`.
- **Per-attempt sub-records** under `attempts: [...]` in the JSONL record, including failed attempts. Final `status` reflects the outcome of the last attempt; `retry_count` reflects total attempts minus one.

### 5.3 Prompt cache strategy

Anthropic prompt caching enabled by default for cost amortization across calls in the same stage. Per-stage cache layout:

- **Stage 0** (translate_sources): no caching — single call per source.
- **Stage 1** (prepare_seed_questions): if multiple types share a source-derived call against the same translated source, that source's `content.md` is cached.
- **Stage 2** (calibrate_types): per-seed source content + candidate rubric in cached prefix when scoring multiple answers; refreshed each iteration when rubric changes.
- **Stage 3** (generate_rubric): question's source content + frozen universal rubric in cached prefix across all per-question calls.
- **Stage 4** (gold_grade): source content + universal rubric + per-question rubric in cached prefix; subsequent answers in the same run hit cache.

Cache markers at chunk boundaries. Cache TTL = 5 minutes (Anthropic default). `cache_read_input_tokens` recorded per call; aggregate cache savings reported in `traces/<stage>/cache_summary.yaml`.

### 5.4 Error escalation

- **Per-call retries exhausted** → trace records `status: error_*`. The caller decides: a per-answer-generation failure inside Stage 3 might be soft (skip this answer, mark `status: partial`); a critic call failure inside Stage 2 is hard (halt the run — we cannot proceed without a refinement proposal).
- **Halt-on-fail** decisions are documented per call site in the stage's source code.
- The run's `run_meta.yaml` final `status` field is the worst status across all stages: `success` | `partial` | `failed`.

---

## 6. Testing strategy (DRAFT — agreed)

The preprocessing pipeline runs many Claude calls. We can't run them in CI. The test pipeline uses recorded fixtures for everything LLM-touching.

### 6.1 Unit tests (no LLM)

- `tests/preprocessing/test_models.py` — schema validation for every YAML artifact in §3 (positive + negative cases).
- `tests/preprocessing/test_aggregation.py` — the §3.3 formula with worked numeric examples (including the Q03 walked example).
- `tests/preprocessing/test_validators.py` — every validator in §3.6: positives pass, negatives raise the expected error type.
- `tests/preprocessing/test_run_resolution.py` — `--run <prefix>` resolution: exact / partial / ambiguous (errors) / no match.
- `tests/preprocessing/test_diff.py` — semantic diff for rubrics, grades, seeds, against fixed-input fixtures.
- `tests/preprocessing/test_prompts.py` — prompt construction is deterministic given inputs (snapshot tests against committed expected prompts).
- `tests/preprocessing/test_aggregation_invariant.py` — random rubrics + random level inputs ⇒ aggregate ∈ [0, 1], aggregate_x10 ∈ [0, 10] (property-based, hypothesis library).

### 6.2 Integration tests with cassettes (replay; no live calls)

Use `pytest-recording` (or hand-rolled VCR) to record real Claude responses once, replay in CI. Cassettes live in `tests/preprocessing/cassettes/<test_name>.yaml`. Recorded request fingerprints are compared on replay; mismatches fail with a clear message ("prompt has changed; re-record cassette").

- `test_translate_sources_pdf.py` — feeds a tiny fixture PDF (1-2 pages), replays vision response.
- `test_prepare_seed_questions_claude_knowledge.py` — replays seed generation + validation.
- `test_calibrate_types_one_iteration.py` — replays one calibration iteration on a tiny seed pool.
- `test_generate_rubric_one_question.py` — replays full Stage 3 for one question.
- `test_gold_grade_one_answer.py` — replays one judge call.

To re-record after prompt changes: `pytest --record-mode=rewrite` (requires `ANTHROPIC_API_KEY`).

### 6.3 End-to-end smoke test (cassette-driven)

`tests/preprocessing/test_smoke.py` runs a minimal pipeline through all 5 stages from a tiny fixture: 1 source (5 pages), 2 types calibrated, 2 seeds per type, 1 assessment question. Uses recorded cassettes.

Verifies:
- Run folder structure as in §2.
- All `status` tags as expected for the recorded path.
- Validators pass at every artifact boundary.
- Aggregation arithmetic correct (numeric comparison against handwritten expected).
- Trace JSONL records well-formed and queryable.

Runs in CI without Claude credits.

### 6.4 Live tests (manual, marked `@pytest.mark.live`)

- `tests/preprocessing/test_live_smoke.py` — same as smoke but live. Used to re-record cassettes, verify prompts still work after Claude model updates, and spot-check artifact quality.
- Not run in CI. Owner runs manually with `pytest -m live`.

### 6.5 Schema-level CI checks

Every YAML artifact in the run folder validates against the §3 schemas. CI runs `python -m preprocessing.validate_run runs/<id>` on the smoke test's output and the latest committed example run. Failure ⇒ build red.

---

## 7. Open questions and deferred items (DRAFT)

### 7.1 Architectural decisions deferred to a later iteration

- **Cross-course seed pool expansion**. Initial implementation uses Claude-knowledge seeds + (optionally) the user's available courses. When a second course PDF arrives, Stage 2 is re-run with expanded seed pool. **Threshold for re-freezing**: TBD — empirical question. Suggested first cut: if any axis weight changes by ≥ 0.10, re-freeze; else original calibration validated.
- **HyDE for seed-question discovery (Phase 1B)** — defer until we have a corpus of past coursework to retrieve over.
- **Per-figure crops** in Stage 0 — page-level snapshots sufficient for now; per-figure cropping is implementable later via Claude bbox detection or `pymupdf` image extraction.
- **Content-addressed source cache** outside `runs/<id>/` — defer until per-run translation cost becomes painful.
- **Karpathy-style runtime refinement** — explicitly NOT in this design. The benchmark is frozen at preprocessing time. If needed for a different use case, separate spec.
- **Real student answers** — out of scope (§0). The benchmark is the gold reference; real-student grading is a downstream consumer.

### 7.2 Implementation-time questions (resolved during writing-plans)

- Exact CLI module names (`preprocessing.translate_sources` vs `preprocessing.translate` vs other).
- Concrete model versions and tier-dispatch wiring (touches `version2/config/llm_config.py`; spec only commits to "foundational tier").
- Cassette library choice (`pytest-recording` vs `vcrpy` vs hand-rolled).
- Whether to use `pydantic` vs `attrs` vs `dataclasses` for YAML model validation.

### 7.3 Open quality questions

- **Initial threshold values** for the three Stage 2 criteria (0.85 concept-vote agreement, 0.90 score-band satisfaction, 0.25 axis-discrimination delta) are educated guesses. First few runs should empirically validate or tune these. Spec calls them out as `Knobs` accordingly.
- **`max_iterations` default of 6** for Stage 2 is a guess. May need to be higher if calibration is hard to converge.
- **`overlay_refinement_iterations` default of 3** for Stage 3 — also a guess.
- **Score-band gaps** `(0.30, 0.40)` and `(0.70, 0.85)` may need tightening or loosening based on Claude's calibration tendencies.

These tunables are all in `config.yaml`. Each run records the config it used in `run_meta.yaml`, so comparing two runs reveals which knob change moved the metrics.

### 7.4 Things the user explicitly requested be preserved (audit trail)

- All Claude prompts and responses, full text, no truncation (§5.1).
- All Stage 2 per-seed throwaway artifacts (concept overlays, synthetic answers, gold coverage) — persisted as named files in `types/<type>/seed_artifacts/<seed_id>/` (§4.3, step 6).
- All Stage 2 per-iteration intermediate state (candidate rubric, judge outputs, criterion outcomes, critic proposal) — persisted in `types/<type>/iterations/iter_NN/` (§4.3, step 6).
- All Stage 3 overlay refinement iterations — persisted in `rubrics/<course>/<q>/iterations/iter_NN/` (§4.4, step 6).
- Per-run full source-code snapshot via `src_snapshot.tar.gz` (§2).
- `REPRODUCE.md` per run with exact CLI commands (§2).
