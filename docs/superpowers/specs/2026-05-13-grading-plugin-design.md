# Gold Preprocessing Benchmark — Design (Option D: Claude Code Grading Plugin)

**Status:** DRAFT — Option D design ratified, 2026-05-13.
**Author/Driver:** erlebach (with Claude)
**Supersedes (in part):** `docs/superpowers/specs/2026-05-12-v2-self-contained-benchmark-design.md`
**Diverges from:** `docs/superpowers/specs/2026-05-13-preprocessing-benchmark-design.md` (an earlier same-day draft assuming Python + Anthropic SDK; preserved as historical record).

> **Both 2026-05-13 specs are drafts of the autograder's v3 direction** — the gold preprocessing benchmark, succeeding v1 (legacy keyword pipeline in `grading_pipeline/`) and v2 (concept-check pipeline in `v2/`, `version2/`). This file is the ratified design; the sibling file is preserved as a record of the earlier SDK-driven approach that was reconsidered mid-session once Claude MAX billing was factored in.
>
> **Architecture pivot from the earlier same-day draft.** The earlier draft assumed a Python codebase calling the Anthropic API directly, which would have required separate API billing on top of the user's Claude MAX subscription. This Option D design re-architects the same preprocessing pipeline as a **Claude Code plugin**: every LLM operation runs through Claude Code subagents (covered by MAX), the whole thing ships as an installable plugin at `plugins/grading/`, LLM calls are batched aggressively, and operations are tagged by `role` resolved to a tier (Claude Opus / Sonnet / Haiku now; Ollama Gemma4 later) via plugin config.
>
> **What carries over verbatim from the earlier draft:** §0 framing, §2 run-folder layout, §3 data model (schemas, aggregation formula, validators, score bands), §7 open questions (with §7.2 updated). Architecture-independent.
>
> **What changes here:** §1 architecture (invocation via `/grade:*` slash commands), §4 stage details (algorithms as subagent dispatches + Python helper calls; LLM calls batched), §5 tracing & retry (Claude Code session history + subagent summaries replace SDK JSONL), §6 testing (cassettes dropped; tests Python helpers only). §8 is new (plugin layout).

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

Every subagent dispatched across all stages leaves a JSON summary at `traces/<stage>/<subagent_id>.json` and a full transcript in Claude Code's session history.

### Invocation

Each stage is a Claude Code slash command provided by the `grading` plugin (see §8). The main agent (you in this Claude Code session) reads the command's skill, dispatches subagents for LLM operations, and calls Python helpers for pure-computation tasks:

```
/grade:translate <source_path>
/grade:seeds [--types DEFINITION,MECHANISM,...]
/grade:review-seeds [--type <T>] [--accept-all]
/grade:calibrate [--types <T,...>] [--proceed-on-warning]
/grade:test-universal [--type <T>] [--seeds <N>]
/grade:question --course <course_id> --question <q_id>
/grade:gold-grade --course <course_id> --question <q_id>
/grade:course <course_id>          # runs /grade:question + /grade:gold-grade for each question
/grade:status                       # current run state
/grade:diff <run_a> <run_b>         # compare two runs
```

`/grade:course <course_id>` is the orchestrating wrapper: it iterates through every question in `inputs/questions/<course>/`, dispatches a per-question subagent that invokes the Stage 3 + Stage 4 logic, and writes a course-level summary. Stages 0–2 are explicit prerequisites — the wrapper refuses to start if their outputs are missing from the active run folder.

Behind every `/grade:*` command:
- A **skill** (`plugins/grading/skills/preprocessing/<stage>.md`) holds the procedure the main agent follows.
- The main agent **dispatches subagents** via the Agent tool for batched LLM operations. Each subagent receives a focused task with the necessary file references, performs its LLM work, writes outputs to disk, returns a short confirmation.
- The main agent invokes **Python helpers** (`plugins/grading/python/*.py`) via Bash for deterministic computation: schema validation, aggregation arithmetic, semantic diff, snapshot tarball creation. No `anthropic` SDK, no API key.
- **Tier dispatch**: each subagent task carries a `role` (e.g., `role: judge`, `role: critic`, `role: answer_gen`); the plugin's `config/tier_dispatch.yaml` maps roles to tiers (Claude Opus / Sonnet / Haiku now; Ollama Gemma4 later).

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

Every stage (as orchestrated by its skill, executed by the main agent in this Claude Code session):
- Validates inputs at load time using the §3.6 validators (Python helper `plugins/grading/python/schema.py`).
- Writes outputs into the active run folder (`runs/<run_id>/...`).
- Writes a JSON summary record for each dispatched subagent to `traces/<stage>/<subagent_id>.json` capturing: `task`, `role`, `tier`, `inputs[]` (file refs), `outputs[]` (file refs), `started_at`, `ended_at`, `status` (success / partial / error), `error_summary` (if any). The full subagent transcript lives in Claude Code session history (`.specstory/`).
- Appends to `traces/<stage>/timeline.jsonl` for **every** agent / subagent activity (start + end timestamps, name, actor) — see §5.6 for the schema and event types. This is a hard invariant: no activity goes unlogged.
- Hard errors on schema violations or invariant failures (halts the stage; trace records offending file).
- Soft errors on per-item failures (one synthetic answer failed to generate, one seed validation timed out): main agent logs it, continues with the rest, marks the affected artifact `status: partial` and surfaces to the user at stage end.
- Supports `--run <prefix>` (resolved via the Python helper) for selecting an active run folder; defaults to most recent run if omitted.
- Operations carry a `role` tag (`pdf_translator`, `seed_gen`, `seed_validator`, `materialize_seed`, `judge`, `critic`, `gold_annotator`, `answer_gen`, `overlay_gen`). The plugin's `config/tier_dispatch.yaml` resolves `role → tier (model)` at dispatch time.

**Persistence policy (applies to every stage):** *nothing inside a run folder is ever discarded by the pipeline.* "Throwaway" artifacts — Stage 2's per-seed concept overlays, every iteration's intermediate rubric + judge outputs + critic proposals, Stage 3's overlay refinement iterations — are all persisted as their own files. The downstream pipeline may not read them, but the user can. Disk is cheap; auditability is not.

### 4.1 Stage 0 — `translate_sources` (one invocation per source file)

**Purpose**: convert each input source (PDF or markdown) into canonical markdown + page-level figure snapshots.

**For PDFs:**
1. Python helper `plugins/grading/python/pdf_render.py` runs `pymupdf` to render every page to `figures/page_NNN.png` (3-digit zero-padded). Page-level snapshots are lossless — they preserve all visual content for downstream stages that need visual grounding. Per-figure crops are a future enhancement.
2. Main agent dispatches **one subagent** (`role: pdf_translator`) that reads the rendered pages, outputs `content.md`. The markdown includes `[Figure: page_NNN]` markers where a page is visually load-bearing. Otherwise plain text/headings/code blocks/tables.
3. Python helper writes `meta.yaml` recording `format: pdf`, `page_count`, `figure_count`, `content_sha`, `extraction.role`, `extraction.tier`, `extraction.ts`.

**For markdown inputs:**
1. Python helper validates front matter + heading structure (optional, configurable).
2. Python helper copies verbatim to `content.md`. No figures unless inline image links exist (those images are copied too).
3. `meta.yaml` with `format: markdown`. No subagent dispatch needed (no LLM work).

**Source naming**: `<source_name>` = input filename stem, lowercased + snake_cased. `--name` arg to `/grade:translate` overrides on collision.

**Knobs (plugin `config/pipeline.yaml`)**: `pdf_translator` role's verbosity (terse / detailed markdown), figure inclusion threshold (always / on-detection / never). Role-to-tier mapping in `config/tier_dispatch.yaml`.

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

**Claude-knowledge generation**: main agent dispatches **one subagent (`role: seed_gen`) per type**, instructed to emit a batch of N seeds in a single structured JSON response. Subagent prompt:
```
TASK: Generate <N> distinct <TYPE> questions matching the criterion: <type_description>.

DIVERSITY REQUIREMENT: span ≥ <J> distinct topical domains. Suggested domains:
biology, history, physics, economics, literature, chemistry, engineering, sociology,
mathematics, programming, philosophy, medicine.

CONSTRAINTS:
- Each question must be a clear <TYPE> question (not just adjacent).
- Self-contained (no external context required).
- Avoid politically charged or sensitive topics.

OUTPUT (JSON array, written to <output_file>):
  [ { "topic": "...", "text": "...", "rationale": "..." }, ... ]
```
Subagent writes the JSON array to a file under `seed_questions/<type>/`. Main agent reads it and emits one YAML per seed.

**Source-derived generation**: same shape; subagent is also given a translated source's `content.md` and told "draw questions from the material below" instead of the diversity instruction.

**Validation pass** (optional, controlled by `validation_pass_enabled` knob): main agent dispatches **one subagent (`role: seed_validator`) per type** that receives the generated seeds in batch and returns per-seed `well_formed: yes | no | borderline + rationale`. Borderline + no are flagged for user review.

**User review gate** (slash command, interactive or batch):
```
/grade:review-seeds --type MECHANISM [--accept-all]
```
The main agent presents each unreviewed seed for the user to approve / reject / edit, then writes `user_review.approved: true | false` back to each seed file. Stage 2 only loads `approved == true`.

**Knobs**: `seeds_per_type`, `topical_domains_min` (J), `composition` shares, `validation_pass_enabled`. Role-to-tier mapping in `config/tier_dispatch.yaml`.

### 4.3 Stage 2 — `calibrate_types` (per type; produces frozen universal layer)

**Per-type algorithm** (the main agent orchestrates; `/grade:calibrate` invokes the `calibrate_types.md` skill):

1. **Initialize**: Python helper loads candidate axes from `type_catalog.yaml`; uniform weights. Main agent dispatches one **`role: axis_criterion_drafter`** subagent that drafts initial `score_levels.{full, partial, none}.criterion` from the type description (one subagent per type, one batched response covering all axes for that type).

2. **Materialize per-seed scoring set** — for each approved seed of this type, the main agent dispatches a **`role: materialize_seed`** subagent (parallelizable across seeds). The subagent's task in one batched call:
   - Generate 3 good + 3 less_good + 3 wrong synthetic answers (9 total).
   - Generate 1 axis-perturbation answer per candidate axis (~4 more).
   - Propose a throwaway 2–5 concept overlay (per-seed; used only for calibration scoring; never frozen).
   - Annotate gold per-(concept, axis) coverage on every answer above.
   - Write all outputs to `types/<type>/seed_artifacts/<seed_id>/`.
   One subagent dispatch per seed produces all of the above in a single structured JSON response, avoiding the per-item dispatch overhead.

3. **Train / val / test split**: 60 / 20 / 20 over approved seeds, deterministic by `SHA(seed_id)`.
   - **Train**: critic uses these failure cases to propose refinements.
   - **Val**: iteration stop signal — criterion must pass on val to declare calibration done.
   - **Test**: never touched during calibration. Used only in the held-out test pass below.

4. **Iterate** (≤ `max_iterations`, default 6). Each iteration:
   - **Judge pass**: main agent dispatches **one `role: judge` subagent per val seed** (parallelizable). Each subagent receives `(seed, throwaway_overlay, candidate_universal_rubric, all answers for this seed)` and returns per-(answer, concept, axis) labels in one batched JSON response. ~`|val|` subagents per iteration.
   - Python helper aggregates judge outputs and computes the three criteria:
     - **Concept-vote agreement** ≥ 0.85 — fraction of (concept, axis) pairs where judge label == gold label.
     - **Score-band satisfaction** ≥ 0.90 — fraction of answers landing in their quality-level's target band.
     - **Axis discrimination** — for each axis-perturbation answer, the targeted axis must show a clearly lower per-pair score than non-target axes. Quantified as: target-axis mean score < non-target-axes mean score by at least 0.25.
   - If all three pass on val → exit loop (proceed to held-out test pass).
   - Else: main agent dispatches **one `role: critic` subagent** that sees current rubric + criterion outcomes + concrete failure cases from the **train** set (e.g., "axis X showed 'full' but gold was 'partial' on 8 of 12 less_good answers"). Critic returns proposed revisions to weights and/or level criteria in structured JSON. Python helper applies revisions; main agent persists `iter_NN/` artifacts.

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

8. **Standalone test command**: `/grade:test-universal --type MECHANISM [--seeds <N>]` runs an additional ad-hoc test pass against fresh Claude-generated seeds (not in the original pool). Useful as a sanity check before kicking off a batch of per-question runs in Stage 3. Main agent dispatches fresh `seed_gen` + `materialize_seed` + `judge` subagents and writes `types/<type>/adhoc_test_<timestamp>.yaml`; does not modify the frozen `status`.

**Knobs**: `max_iterations`, split ratios (`train/val/test`), three criterion thresholds, critic prompt strategy, perturbation magnitude expectation, `proceed_on_warning`.

### 4.4 Stage 3 — `generate_rubric` (per assessment question; produces frozen per-question artifacts)

Reuses §4.3 machinery but with a **frozen** universal rubric. Universal layer is immutable in this stage; only the per-question overlay is iterated.

**Pre-flight check** (Python helper): Stage 3 reads `types/<type>/universal_rubric.yaml`. If `status: warning_test_marginal`, the main agent refuses to dispatch the question's subagent unless `--proceed-on-warning` was passed. If `status: failed_to_converge`, refuses outright (no override). Guard rail: a fundamentally bad universal rubric cannot silently corrupt downstream per-question artifacts.

**Per-question algorithm** (`/grade:question --course <c> --question <q>`):

1. Python helper loads `inputs/questions/<course>/<q>.yaml` + frozen `types/<type>/universal_rubric.yaml`.

2. **Materialize question scoring set** — main agent dispatches **one `role: question_workup` subagent** that, in a single batched JSON response:
   - Generates 3 good answers (grounded in the source material referenced by the question's `sources:` field; subagent receives the relevant `content.md`).
   - Generates 3 less_good answers (partially correct).
   - Generates 3 wrong answers (off-direction or off-topic).
   - Generates 1 axis-perturbation per universal axis for this type (benchmark integrity check).
   - Proposes the per-question concept overlay (2–5 concepts with weights summing to 1.0; each with `relevant_axes ⊆ universal axes`).
   - Annotates gold per-(concept, axis) coverage on every answer.
   One subagent produces it all (parallels Stage 2's `materialize_seed`, but writing frozen artifacts instead of throwaway ones).

3. **Sanity-check** — Python helper applies a `judge` subagent's output (one dispatch over all answers, batched) and checks ordering + bands:
   - If pass: proceed; mark `status: frozen`.
   - If fail: dispatch a `role: overlay_critic` subagent that proposes refinements to **only the per-question concept overlay** (weights and/or `relevant_axes`). Universal layer untouchable. Max `overlay_refinement_iterations`, default 3.
   - On exhaustion: write rubric with `status: degraded`, halt this question (run continues for other questions). Many `degraded` per-question rubrics ⇒ signal to re-run Stage 2 with a broader seed pool.

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

**Judge dispatch** — main agent dispatches **one `role: judge` subagent per question**, batching all answers + all (concept, axis) pairs into one structured JSON response. The subagent's task:

```
SYSTEM: You are a careful grader. For each (answer × concept × axis) triple below,
classify the answer's coverage on that (concept, axis) as "full" / "partial" / "none"
using the per-axis criteria provided.

CONTEXT (in the subagent's task body):
  - Source content: <content.md inline>
  - Universal rubric for <TYPE>: axes + score_levels
  - Per-question rubric for <Q_ID>: concepts + relevant_axes
  - Answers: [{ id: "good_1", text: "..." }, { id: "good_2", text: "..." }, ...]
    (all ~13 synthetic answers for this question, batched)

OUTPUT (JSON array, one entry per (answer × concept × axis), written to <output_file>):
  [
    { "answer_id": "...", "concept_id": "...", "axis": "...",
      "level": "full" | "partial" | "none", "rationale": "<1-2 sentences>" },
    ...
  ]
```

**Design choices**:
- One subagent per question, batching all answers and all (concept, axis) pairs. Internal consistency across the question's answers is improved by Claude seeing the full picture at once; per-question parallelism is achieved at the *between-question* level (the `/grade:course` wrapper dispatches per-question subagents in parallel).
- Rationale per pair mandatory; subagent writes the JSON array to disk; the main agent reads it, runs aggregation via Python helper, propagates rationales into `grades.yaml` per pair.

**Per-question summary** (Python helper `aggregation.py`, written into `grades.yaml` `summary` block):
- `mean_by_quality`: average aggregate per quality level (good / less_good / wrong / axis_perturbation).
- `ordering_preserved`: mean(good) > mean(less_good) > mean(wrong)?
- `bands_satisfied`: all answers in their target band?
- `axis_discrimination_passed`: each axis-perturbation drop targeted right axis?

**Failure mode at Stage 4**: if `bands_satisfied == false` or `ordering_preserved == false`, this question's benchmark output is flagged `degraded` in the run summary. The run continues for other questions.

### 4.6 Stage glue and `/grade:course` wrapper

`/grade:course <course_id>` runs **Stages 3 + 4 for every question in the course's questions list**. The main agent dispatches per-question subagents in parallel up to the configured concurrency (knob `max_parallel_questions`, default 3 — tuned to stay comfortably within MAX rate limits). Each per-question subagent invokes Stage 3 + Stage 4 sequentially for one question. Stages 0–2 are explicit prerequisites — the main agent checks the run folder for their outputs and refuses to start if any are missing.

After all per-question subagents complete, a Python helper writes a course-level summary at `runs/<id>/summary_<course>.yaml`:
- per-question pass/degrade status,
- aggregate grades by quality level across all questions,
- total subagent dispatches per role,
- elapsed time per stage and per question.

## 5. Tracing and retry infrastructure (DRAFT — agreed)

All LLM work happens inside Claude Code subagents. The trace machinery is therefore very different from V1's SDK-call JSONL: the main agent writes a structured **subagent-summary** record per dispatch, while the full subagent transcripts (prompt + response, no truncation) are captured by Claude Code's session history.

### 5.1 Subagent summary record

For each subagent dispatch, the main agent writes a JSON file at `runs/<id>/traces/<stage>/<subagent_id>.json`:

```json
{
  "subagent_id": "01HXYZAB...",                  // ULID; matches Claude Code's dispatch id
  "ts_start": "2026-05-13T13:15:01.234Z",
  "ts_end":   "2026-05-13T13:15:33.567Z",
  "duration_ms": 32333,
  "stage": "calibrate_types",
  "sub_operation": "materialize_seed:MECHANISM_gen_003",
  "role": "materialize_seed",                    // resolved via config/tier_dispatch.yaml
  "tier": "claude-opus-4-7",                     // the actual model the role resolved to
  "task_summary": "Materialize scoring set for seed MECHANISM_gen_003 (9 quality answers, 4 axis perturbations, throwaway overlay, gold coverage).",
  "inputs": [
    "seed_questions/MECHANISM/MECHANISM_gen_003.yaml",
    "types/MECHANISM/iter_01/candidate_rubric.yaml"
  ],
  "outputs": [
    "types/MECHANISM/seed_artifacts/MECHANISM_gen_003/synthetic_answers.yaml",
    "types/MECHANISM/seed_artifacts/MECHANISM_gen_003/concept_overlay.yaml",
    "types/MECHANISM/seed_artifacts/MECHANISM_gen_003/gold_concept_coverage.yaml"
  ],
  "status": "success",                           // success | partial | error
  "retry_count": 0,
  "error_summary": null,                         // or "{ type, message }"
  "session_transcript_ref": ".specstory/history/2026-05-13_13-15-00Z-calibrate-mechanism.md"
}
```

**The full prompt + full response are NOT in this JSON record.** They live in Claude Code's session transcript at the `session_transcript_ref` path. That transcript is the audit trail; the JSON summary is a structured index over it.

### 5.2 Session-level audit trail

Claude Code automatically captures every subagent's prompt and response in `.specstory/history/<session>.md`. The persistence policy (§4.0) extends here: nothing is discarded. To inspect what a particular subagent said, the user (or future Claude session) opens the session transcript referenced from the JSON summary.

### 5.3 Retry strategy

- Within a single subagent run, Claude Code handles transient retries (rate limits, transient HTTP errors) per its own internal policy. We don't re-implement that.
- At the dispatch level, the main agent monitors subagent completion. If a subagent returns `status: error`, the main agent re-dispatches up to `max_redispatches` (default 2) with a slightly adjusted task ("your previous attempt failed with `<error_summary>`; please retry"). Each redispatch gets its own `subagent_id` and JSON summary, with `retry_count` incremented and a `prev_subagent_id` pointer in the JSON.
- **JSON parsing failures** on a subagent's structured output get one redispatch with a "your previous output was not valid JSON; return only valid JSON" reminder, then hard fail.
- **Hard fail** on a critical subagent (e.g., Stage 2 critic) halts the stage; main agent surfaces to the user with the failed subagent's transcript ref.

### 5.4 Error escalation

- **Per-subagent error**: written to its JSON summary with `status: error` + `error_summary`. The dispatching stage's skill decides soft vs. hard.
- **Soft failure** (one item in a batch failed, e.g., one synthetic answer didn't generate): main agent logs it, marks the affected artifact `status: partial`, continues.
- **Hard failure** (critic, judge on val set, type calibration itself): halts the stage; main agent surfaces to user.
- The run's `run_meta.yaml` final `status` is the worst status across all stages: `success` | `partial` | `failed`.

### 5.5 Per-stage `trace_summary.yaml`

At stage completion, the main agent writes `runs/<id>/traces/<stage>/trace_summary.yaml` aggregating across all subagent summaries in that stage:
- count by `role`, count by `status`,
- total duration, p50/p95 duration,
- per-role tier distribution (useful when verifying tier dispatch worked as intended),
- list of subagents marked `status: error` with refs.

This is the user-facing "what happened during Stage X" report.

### 5.6 Per-stage activity timeline (`timeline.jsonl`)

**Hard requirement:** every agent / subagent activity is logged with start time, end time, and a human-readable name. The per-subagent JSON summary (§5.1) covers each dispatched subagent; the per-stage **timeline.jsonl** covers the rest — every orchestration event the main agent emits, in chronological order.

File: `runs/<id>/traces/<stage>/timeline.jsonl` — one JSON object per line, append-only over the stage's lifetime.

Event schema:

```json
{
  "ts": "2026-05-13T16:15:33.214Z",
  "event_type": "subagent_dispatch",
  "actor": "main_agent",                       // "main_agent" | "<subagent_id>"
  "name": "materialize_seed:MECHANISM_seed_001",
  "phase": "start",                            // "start" | "end"
  "details": {
    "role": "materialize_seed",
    "subagent_id": "01HXYZ...",
    "summary_ref": "traces/calibrate_types/01HXYZ....json"
    // … event-type-specific fields below
  }
}
```

Event types (every meaningful activity gets `start` and matching `end` events):

| event_type | name examples | emitted by |
|---|---|---|
| `stage` | `calibrate_types:MECHANISM` | main_agent at stage entry/exit |
| `iteration` | `iter_3` (Stage 2 calibration), `overlay_iter_2` (Stage 3) | main_agent at iteration entry/exit |
| `subagent_dispatch` | `materialize_seed:MECHANISM_seed_001`, `judge:Q03`, `critic:MECHANISM_iter_3` | main_agent when dispatching |
| `python_helper_call` | `validate_universal_rubric`, `compute_aggregate`, `pdf_render` | main_agent when invoking a helper |
| `gate_decision` | `review_seeds_gate`, `warning_test_marginal_ack`, `proceed_on_warning` | main_agent at user-decision points |
| `error` | `subagent_redispatch_exhausted:critic_MECHANISM`, `validation_failed:rubrics/Q03/rubric.yaml` | main_agent when surfacing failures |

**Invariants:**
- Every `start` event has a matching `end` event with the same `name` (unless the run crashes). The Python helper's timeline-validation function checks this at run completion.
- `subagent_dispatch:start` emits before the subagent's own JSON summary exists; `subagent_dispatch:end` emits after the summary is on disk, with `summary_ref` populated.
- `python_helper_call` events bracket every Python helper invocation, capturing duration even when the helper finishes in milliseconds.
- Timestamps are ISO 8601 with millisecond precision, UTC.

**Reading the timeline:**
- Reconstruct the full stage execution by sorting `timeline.jsonl` by `ts`.
- Pair each `start` with its `end` to get per-activity duration.
- Cross-reference `summary_ref` to drill into a specific subagent's summary; from there, `session_transcript_ref` (§5.1) drills into the full transcript.

This gives three nested layers of trace, all explicit:
- Stage-level: `trace_summary.yaml` (§5.5) — aggregate report.
- Activity-level: `timeline.jsonl` (this section) — chronological log of every action.
- Call-level: `<subagent_id>.json` (§5.1) — per-subagent metadata + transcript pointer.

### 5.7 What `traces/` does *not* contain

- No raw prompt / raw response text. Those live in `.specstory/history/`.
- No retry-backoff tuning knobs. Claude Code handles those internally.
- No Anthropic-API usage metrics (input_tokens, cache_read_input_tokens). Replaced by subagent count + duration; if granular billing data is needed later, query MAX usage dashboard directly.

---

## 6. Testing strategy (DRAFT — agreed)

LLM-side work lives in Claude Code subagents, which can't be replayed in CI cheaply. Tests therefore focus on **the pure-Python helpers and the structural contracts** — anything that doesn't require an LLM call. End-to-end pipeline verification is manual, performed against a tiny fixture run-folder by dispatching real subagents.

### 6.1 Unit tests for Python helpers (no LLM, run in CI)

Tests live under `plugins/grading/python/tests/`:

- `test_schema.py` — schema validation for every YAML artifact in §3 (positive + negative cases): `universal_rubric.yaml`, per-question `rubric.yaml`, `grades.yaml`, `seed_questions/*.yaml`, `meta.yaml`, `run_meta.yaml`, `config.yaml`, `tier_dispatch.yaml`.
- `test_aggregation.py` — the §3.3 formula with worked numeric examples (including the Q03 walked example). Asserts exact outputs from fixed inputs.
- `test_validators.py` — every validator in §3.6: positives pass; negatives raise the expected error type with a useful message.
- `test_run_resolution.py` — `--run <prefix>` resolution: exact / partial / ambiguous (errors with a list) / no-match.
- `test_diff.py` — semantic diff between two fixture run folders for each artifact type (rubrics / grades / seeds).
- `test_snapshot.py` — `src_snapshot.tar.gz` creation: excludes expected paths (`.git/`, `.venv/`, `__pycache__/`, `.specstory/`, `runs/`); includes `pyproject.toml`, `plugins/grading/`, lockfile.
- `test_aggregation_invariant.py` — property-based (hypothesis): random rubrics + random level inputs ⇒ `aggregate ∈ [0, 1]`, `aggregate_x10 ∈ [0, 10]`, `aggregate_x10 = aggregate × 10 ± ε`. Random concept-weight / axis-weight distributions normalized; no NaNs.

### 6.2 Subagent-output contract tests (no live LLM)

Each subagent role produces a structured JSON output with a documented schema. We test the **schema** of these outputs against hand-built fixtures, independent of any live LLM call. Tests under `plugins/grading/python/tests/contracts/`:

- `test_judge_output_schema.py` — given a fixture JSON array (built by hand), verify the parser accepts well-formed rows and rejects malformed ones.
- `test_critic_output_schema.py` — same for critic-proposed revisions.
- `test_materialize_seed_output_schema.py` — same for the batched output of `materialize_seed`.
- `test_seed_gen_output_schema.py` — same for seed-generation output.

These tests confirm the Python side will not crash on the structured outputs of any subagent role. They do not verify that Claude *produces* well-formed output — that's the live-test concern below.

### 6.3 Fixture-driven structural smoke test (no LLM)

`plugins/grading/python/tests/test_smoke_fixture.py` reads a committed fixture run-folder at `tests/fixtures/run_smoke/` and asserts:
- Folder layout matches §2.
- All `status` tags as expected.
- Validators pass at every artifact boundary.
- Aggregation arithmetic in `grades.yaml` matches a handwritten expected.
- All `traces/<stage>/*.json` summaries are well-formed.

This is what runs in CI. The fixture is hand-crafted (not generated by live subagents); it represents a "what a successful run folder should look like" reference. The fixture is updated whenever §2 / §3 schemas change.

### 6.4 Live end-to-end (manual; outside CI)

When the user wants to verify the pipeline end-to-end against real Claude work, they run a tiny live pipeline manually:

```
/grade:translate tests/fixtures/sources/tiny_5page.pdf
/grade:seeds --types DEFINITION,MECHANISM   # K=2 per type
/grade:review-seeds --accept-all            # if trusted
/grade:calibrate --types DEFINITION,MECHANISM
/grade:test-universal --type MECHANISM
/grade:question --course fixture --question Qfix01
/grade:gold-grade --course fixture --question Qfix01
/grade:status                                # inspect outcome
```

This uses real subagent dispatches and consumes MAX quota. It is **not** part of automated CI; it is the user's bring-up smoke. After the first successful live run, the resulting run folder is what `tests/fixtures/run_smoke/` is replaced by (with sensitive content removed) — fixtures stay grounded in real shapes.

### 6.5 Schema-level CI checks against the latest committed run

CI runs the Python validators against any run folder committed under `tests/fixtures/runs/`. Failure (schema invariant violation, broken cross-ref between `rubrics/<q>/rubric.yaml` and `types/<type>/universal_rubric.yaml`) ⇒ build red. Catches regressions when §3 schemas evolve.

### 6.6 Plugin-level tests

- `test_plugin_manifest.py` — `plugins/grading/plugin.yaml` validates against a manifest schema (see §8). Required fields present; semver version string; declared skills resolve to existing files; declared commands resolve to existing files; declared hooks have executable permission.
- `test_tier_dispatch.py` — `config/tier_dispatch.yaml` validates: every declared role maps to a known tier; every tier is one of the supported set (Claude Opus / Sonnet / Haiku / Ollama Gemma4); no orphan roles relative to the role catalog.

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

- Exact slash-command names (`/grade:translate` vs `/grade:source` vs other; user-friendly naming).
- Subagent task-profile YAML format (under `plugins/grading/agents/` or inline in skills).
- Role catalog completeness (`pdf_translator`, `seed_gen`, `seed_validator`, `materialize_seed`, `axis_criterion_drafter`, `judge`, `critic`, `overlay_critic`, `question_workup`, `answer_gen`, `gold_annotator`, …) — final set ratified against actual implementation needs.
- Concrete role-to-tier mapping defaults in `config/tier_dispatch.yaml` (which roles benefit from Opus vs. Sonnet vs. Haiku, and where Ollama Gemma4 plugs in once integrated).
- `max_parallel_questions` and `max_parallel_seeds` defaults — tuned to stay within MAX rate limits comfortably.
- Plugin manifest schema (the `plugin.yaml` field set and validation rules) — confirm against the Claude Code plugin spec at implementation time.
- Whether to use `pydantic` vs `attrs` vs `dataclasses` for the Python helper schema models.
- Hook scripting language (shell, Python) for `post_subagent_validate`.

### 7.3 Open quality questions

- **Initial threshold values** for the three Stage 2 criteria (0.85 concept-vote agreement, 0.90 score-band satisfaction, 0.25 axis-discrimination delta) are educated guesses. First few runs should empirically validate or tune these. Spec calls them out as `Knobs` accordingly.
- **`max_iterations` default of 6** for Stage 2 is a guess. May need to be higher if calibration is hard to converge.
- **`overlay_refinement_iterations` default of 3** for Stage 3 — also a guess.
- **Score-band gaps** `(0.30, 0.40)` and `(0.70, 0.85)` may need tightening or loosening based on Claude's calibration tendencies.

These tunables are all in `config.yaml`. Each run records the config it used in `run_meta.yaml`, so comparing two runs reveals which knob change moved the metrics.

### 7.4 Things the user explicitly requested be preserved (audit trail)

- **All Claude prompts and responses**, full text, no truncation — captured in Claude Code session history under `.specstory/history/`, linked from each subagent's JSON summary at `traces/<stage>/<subagent_id>.json` via `session_transcript_ref` (§5.1, §5.2).
- All Stage 2 per-seed throwaway artifacts (concept overlays, synthetic answers, gold coverage) — persisted as named files in `types/<type>/seed_artifacts/<seed_id>/` (§4.3, step 6).
- All Stage 2 per-iteration intermediate state (candidate rubric, judge outputs, criterion outcomes, critic proposal) — persisted in `types/<type>/iterations/iter_NN/` (§4.3, step 6).
- All Stage 3 overlay refinement iterations — persisted in `rubrics/<course>/<q>/iterations/iter_NN/` (§4.4, step 6).
- Per-run full source-code snapshot via `src_snapshot.tar.gz` (§2).
- `REPRODUCE.md` per run with exact slash-command invocations (§2).
- Per-stage `traces/<stage>/trace_summary.yaml` aggregating subagent dispatches (§5.5).

---

## 8. Plugin layout (DRAFT — agreed)

The pipeline ships as a single Claude Code plugin at `plugins/grading/` inside this repo. The plugin bundles skills (procedures the main agent follows), slash commands (user-facing entrypoints), hooks (post-write validation), Python helpers (deterministic computation), prompt fragments, and config files.

### 8.1 Directory layout

```
plugins/grading/
  plugin.yaml                      # manifest: name, version, deps, declared skills/commands/hooks
  README.md                        # quick-start, slash-command summary, MAX quota notes

  config/
    pipeline.yaml                  # knobs: seeds_per_type, max_iterations, score_bands, parallelism, …
    tier_dispatch.yaml             # role → tier mapping
    role_catalog.yaml              # canonical list of all roles + descriptions (~10 roles)

  skills/preprocessing/
    translate_sources.md           # Stage 0 procedure
    prepare_seed_questions.md      # Stage 1
    review_seeds.md                # interactive review gate
    calibrate_types.md             # Stage 2 with iteration loop
    test_universal.md              # ad-hoc Stage 2 test pass
    generate_rubric.md             # Stage 3
    gold_grade.md                  # Stage 4
    run_course.md                  # the orchestrating wrapper

  commands/
    grade-translate.md             # /grade:translate <source_path>
    grade-seeds.md                 # /grade:seeds [--types ...]
    grade-review-seeds.md          # /grade:review-seeds [--type ...]
    grade-calibrate.md             # /grade:calibrate [--types ...] [--proceed-on-warning]
    grade-test-universal.md        # /grade:test-universal [--type ...]
    grade-question.md              # /grade:question --course <c> --question <q>
    grade-gold-grade.md            # /grade:gold-grade --course <c> --question <q>
    grade-course.md                # /grade:course <course_id>
    grade-status.md                # /grade:status
    grade-diff.md                  # /grade:diff <run_a> <run_b>

  hooks/
    post_subagent_validate.sh      # post-write YAML schema validation; halts stage on invariant violation

  agents/                          # optional: pre-baked agent profiles per role
    materialize_seed.md            # task profile for role: materialize_seed
    judge.md                       # task profile for role: judge
    critic.md                      # task profile for role: critic
    ...

  prompts/                         # reusable prompt fragments referenced by skills + agents
    judge_system.md
    critic_system.md
    materialize_seed_template.md
    seed_gen_template.md
    pdf_translator_template.md
    ...

  python/
    schema.py                      # pydantic/dataclass models + §3.6 validators
    aggregation.py                 # §3.3 formula (single source of truth)
    diff.py                        # semantic diff between two run folders
    snapshot.py                    # produce src_snapshot.tar.gz
    pdf_render.py                  # pymupdf-based page rendering
    run_resolution.py              # `--run <prefix>` matching
    validate_run.py                # CLI: validate every artifact in a run folder
    tests/
      test_schema.py
      test_aggregation.py
      ...                          # see §6
```

No `anthropic` SDK is imported anywhere in `python/`. No `ANTHROPIC_API_KEY` is read. All LLM work happens through subagents dispatched by the main agent in this Claude Code session.

### 8.2 Plugin manifest (`plugin.yaml`)

```yaml
name: grading
version: 0.1.0
description: |
  Gold preprocessing benchmark for the autograder. Produces frozen rubrics,
  synthetic answers, gold concept coverage, and gold reference scores via
  Claude Code subagents under MAX.
authors:
  - erlebach

skills:
  - skills/preprocessing/translate_sources.md
  - skills/preprocessing/prepare_seed_questions.md
  - skills/preprocessing/review_seeds.md
  - skills/preprocessing/calibrate_types.md
  - skills/preprocessing/test_universal.md
  - skills/preprocessing/generate_rubric.md
  - skills/preprocessing/gold_grade.md
  - skills/preprocessing/run_course.md

commands:
  - commands/grade-translate.md
  - commands/grade-seeds.md
  - commands/grade-review-seeds.md
  - commands/grade-calibrate.md
  - commands/grade-test-universal.md
  - commands/grade-question.md
  - commands/grade-gold-grade.md
  - commands/grade-course.md
  - commands/grade-status.md
  - commands/grade-diff.md

hooks:
  - event: post_subagent
    script: hooks/post_subagent_validate.sh

python_helpers:
  package_root: python
  entrypoints:
    - python.validate_run:main          # invoked as: python -m plugins.grading.python.validate_run
    - python.diff:main
    - python.snapshot:main
```

Exact field names are subject to whatever the Claude Code plugin format requires; the schema above is illustrative. The `test_plugin_manifest.py` test (§6.6) validates against the actual format at implementation time.

### 8.3 Skill conventions

Each skill file (`skills/preprocessing/<stage>.md`) follows a uniform structure:

1. **Frontmatter**: name, description, trigger keywords.
2. **Inputs read**: which files in `runs/<id>/` the main agent reads at startup.
3. **Algorithm**: numbered steps mapping directly to §4's per-stage algorithm. Each step explicitly says whether it dispatches a subagent (with `role:` tag), invokes a Python helper, or makes a control-flow decision.
4. **Subagent task profiles referenced**: links to `agents/<role>.md` for each role used.
5. **Outputs written**: which files in `runs/<id>/` get created or appended to.
6. **Failure modes + halt conditions**: explicit, mapping to §4's "Failure" notes.

### 8.4 Tier dispatch config (`config/tier_dispatch.yaml`)

```yaml
# Maps subagent role → tier (model). The plugin's role_catalog.yaml is the
# canonical list of declared roles; this file binds each to a tier. Tier
# names must resolve to a Claude Code-available model.
default_tier: claude-sonnet-4-6

roles:
  pdf_translator:           claude-opus-4-7        # vision-capable; complex extraction
  seed_gen:                 claude-sonnet-4-6
  seed_validator:           claude-haiku-4-5
  materialize_seed:         claude-opus-4-7        # heavy: 9 answers + perturbations + overlay + gold
  axis_criterion_drafter:   claude-sonnet-4-6
  judge:                    claude-opus-4-7        # gold standard — the benchmark scores
  critic:                   claude-opus-4-7
  overlay_critic:           claude-sonnet-4-6
  question_workup:          claude-opus-4-7
  gold_annotator:           claude-opus-4-7

# Future: Ollama Gemma4 entries below once integrated.
# gold_annotator: ollama:gemma4-26b   # cheap path for re-running annotation at scale
```

The user edits this file to control where compute goes. Swapping `judge` to Sonnet would, e.g., reduce cost at the price of benchmark quality — a deliberate, audit-visible trade-off.

### 8.5 Plugin install

Inside this repo, the plugin lives at `plugins/grading/`. Claude Code discovers it via the standard plugin-discovery path (`.claude/plugins/` or repo-root `plugins/`, depending on environment). Initial install:

1. Place the plugin folder at `plugins/grading/`.
2. Register it in `.claude/settings.json` if required by the user's Claude Code setup.
3. Verify: `/grade:status` resolves and emits "no runs yet."
4. Run the live smoke (§6.4) to bring up the first run folder.

The plugin has no external dependencies beyond what `pyproject.toml` declares for the Python helpers (`pymupdf`, `pydantic`, `pyyaml`).
