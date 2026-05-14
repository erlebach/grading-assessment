# Stage 0 — `translate-sources` + run-folder init — Design

**Status:** DRAFT — design approved 2026-05-14.
**Author/Driver:** erlebach (with Claude)
**Parent spec:** `docs/superpowers/specs/2026-05-13-grading-plugin-design.md` (the ratified Option D grading-plugin design). This document expands §4.1 (Stage 0) and the run-init half of §2 into an implementable plan.
**Precedes:** the Stage 0 implementation plan (`writing-plans` output).

## 1. Scope

This plan delivers the entry point of the grading pipeline: creating a run folder and translating the first source into it. Concretely:

- Two slash commands: `/grade:init` and `/grade:translate`.
- Two new Python helper modules: `run_init.py` and `translate_sources.py`.
- Config additions to `plugins/grading/config/pipeline.yaml`: a `pdf_translator:` knob block and a `profiles:` block.
- One additive schema field: `RunMeta.profile`.
- A CI test suite for the Python helpers plus one frozen live-verification baseline.

Out of scope: Stages 1–4, the content-addressed source cache (parent spec §2 "Future enhancement"), per-figure crops, markdown front-matter validation.

## 2. Commands

### `/grade:init [--profile <name>]`

Creates and bootstraps a new run folder. Run-folder creation is a distinct concern from source translation (it writes reproducibility artifacts, not translated content), so it gets its own command — explicit, loggable as a discrete step in session history, and giving the bootstrap helper exactly one caller.

Behaviour:

1. Generate `run_id` = `YYYY-MM-DD_HH-MM-SSZ__<4-char-fingerprint>` (parent spec §2). At init time no input-artifact run-ids exist, so the fingerprint is `SHA8(merged_config + git_sha)[:4]`.
2. Create `preprocessing/runs/<run_id>/` and the stage subdirectory skeleton (`sources/`, `seed_questions/`, `types/`, `rubrics/`, `synthetic_answers/`, `grades/`, `traces/`).
3. Resolve `--profile` (if given) against `pipeline.yaml`'s `profiles:` block; deep-merge the profile's sparse overrides onto the base config; write the merged result to `runs/<run_id>/config.yaml`.
4. Write `src_snapshot.tar.gz` via the existing `snapshot.create_snapshot`.
5. Write the initial `run_meta.yaml` (`run_id`, `started_at`, `git_sha`, `git_dirty`, `status: success`, `stages_run: []`, `profile: <name or null>`).

All reproducibility artifacts are written **at init time** (not deferred to first stage completion): the run folder is fully self-contained from the instant it exists, there is never a half-built run folder, and the bootstrap logic lives in one code path instead of being sprinkled across stage code. If source code is edited between `/grade:init` and `/grade:translate`, the correct discipline is to discard the run and re-init — not to defer the snapshot.

### `/grade:translate <source_path> [--name <n>] [--run <prefix>]`

Pure Stage 0: translate one source file into the active run folder. Never creates a run folder — errors if none exists, directing the user to `/grade:init`.

Arguments:

- `<source_path>` — path to a `.pdf` or `.md` file under `preprocessing/inputs/sources_raw/`.
- `--name <n>` — override the auto-derived `<source_name>` on collision.
- `--run <prefix>` — target a specific run folder (git-style prefix match via `run_resolution.resolve_run`); defaults to the most-recent run (`run_resolution.most_recent_run`).
- `--force` — re-translate even if a valid translation already exists (see §3.3).

## 3. Components and data flow

### 3.1 Module layout

All under `plugins/grading/python/`:

| Module | Status | Responsibility |
|---|---|---|
| `run_init.py` | new | `init_run(runs_dir, config, profile=None) -> Path` — run_id generation, skeleton creation, config merge, snapshot, `run_meta.yaml`. |
| `translate_sources.py` | new | `prepare_source(...)` and `finalize_source(...)` — the two halves of Stage 0 either side of the subagent boundary. |
| `pdf_render.py` | reused | `render_pages` — renders PDF pages to `page_NNN.png`. |
| `run_resolution.py` | reused | `resolve_run`, `most_recent_run` — `--run` prefix resolution. |
| `snapshot.py` | reused | `create_snapshot` — `src_snapshot.tar.gz`. |
| `schema.py` | reused (+1 field) | `SourceMeta` validation; `RunMeta` gains `profile`. |

### 3.2 The subagent boundary

`translate_sources.py` is split into two functions because a subagent dispatch sits between them. Everything deterministic and unit-testable lives in Python on either side; the one non-deterministic LLM step (rendered pages → markdown) happens in between.

```
prepare_source(source_path, run_dir, name=None, force=False) -> PrepareResult
  • resolve <source_name>: input filename stem, lowercased + snake_cased; --name overrides
  • skip-if-present check (see §3.3)
  • PDF → pdf_render.render_pages() emits figures/page_NNN.png; return page paths + format
  • MD  → copy file verbatim to content.md; copy inline-linked images; return format
  • returns: format, resolved name, page paths (PDF), skip flag

── PDF only: main agent dispatches ONE `pdf_translator` subagent here.
   It reads the rendered pages and returns content.md (with [Figure: page_NNN]
   markers where a page is visually load-bearing). ──

finalize_source(run_dir, name, content_md, page_count, ...) -> Path
  • write content.md (PDF case; markdown path already wrote it in prepare)
  • compute content_sha; build + validate schema.SourceMeta
  • write meta.yaml
```

For the markdown path there is no subagent: `prepare_source` → `finalize_source` run back-to-back, no LLM work.

### 3.3 Skip-if-present

Within a single run, a source is never re-translated once done — the parent spec's standing principle is "nothing inside a run folder is ever overwritten."

- If `runs/<id>/sources/<name>/content.md` exists **and** its `meta.yaml` validates, `/grade:translate` is a no-op that prints "already translated" and exits success.
- `--force` re-translates, writing into the same path — the one sanctioned overwrite.
- The check is cheap (existence + schema validation), so it never burns a `pdf_translator` dispatch needlessly, and re-running `/grade:translate` after an earlier hard failure is safe.

Cross-run de-duplication is **not** handled here — a new run folder re-translates from scratch. That is exactly what the deferred content-addressed source cache (parent spec §2) is for; until it lands, sources are re-translated per run.

### 3.4 Data flow summary

- **PDF:** `prepare_source` renders pages → main agent dispatches one `pdf_translator` subagent → `finalize_source` writes `content.md` + `meta.yaml`.
- **Markdown:** `prepare_source` copies verbatim to `content.md` (+ inline images) → `finalize_source` writes `meta.yaml`. No subagent.
- **Source location:** raw sources live at `preprocessing/inputs/sources_raw/` — a sibling of `runs/`, **not** inside a run folder. They are captured by `src_snapshot.tar.gz` (which excludes only `.git/`, `.venv/`, `__pycache__/`, `.specstory/`, `runs/`), so reproducibility holds. Translated artifacts are written into `runs/<id>/sources/<name>/`.

### 3.5 Outputs

Per `/grade:translate` invocation, into the active run folder:

- `sources/<name>/content.md`
- `sources/<name>/figures/page_NNN.png` (PDFs only, 3-digit zero-padded)
- `sources/<name>/meta.yaml` (`format`, `courses`, `topics`, `extraction.{role,tier,ts}`, `content_sha`, `figure_count`, `page_count` — validated against `schema.SourceMeta`)
- `traces/translate_sources/<subagent_id>.json` per dispatched subagent
- `traces/translate_sources/timeline.jsonl` append-only (parent spec §4.0 invariant)

## 4. Config additions

To `plugins/grading/config/pipeline.yaml`:

### `pdf_translator:` block

The Stage 0 knobs from parent spec §4.1:

```yaml
pdf_translator:
  verbosity: detailed          # terse | detailed
  figure_inclusion: on_detection   # always | on_detection | never
```

### `profiles:` block

The `--profile` convention: a map of named profiles, each a sparse set of overrides deep-merged onto the base config by `/grade:init`. The `smoke` profile is defined now (Stage 1–4 count knobs dialled to 1); other profiles are added as later stages are specced.

```yaml
profiles:
  smoke:
    seeds_per_type:
      default: 1
    generate_rubric:
      good_count: 1
      less_good_count: 1
      wrong_count: 1
      axis_perturbation_count_per_axis: 1
    # ...filled in as Stages 1-4 are specced
```

Stage 0 itself does not branch on the profile — `translate_sources` translates one file regardless. `/grade:init` is simply where the profile is resolved, merged, and frozen into `runs/<id>/config.yaml`; the profile name is also recorded in `run_meta.yaml` so a scoped test run is self-describing.

## 5. Schema delta

`schema.RunMeta` gains one additive field:

```python
profile: str | None = None
```

Records the active profile name in `run_meta.yaml` so it is visible without parsing the merged config. Additive, no migration.

## 6. Testing

Strategy: CI tests for the Python helpers only, plus one documented live verification frozen as a regression baseline. No fake subagent is written in code — the subagent boundary is exercised live, once.

### 6.1 CI — Python helpers

New test files under `plugins/grading/python/tests/`:

- **`test_run_init.py`** — run_id format + fingerprint determinism; skeleton directory creation; base-config → merged-config with and without a profile; `run_meta.yaml` contents incl. `profile`; `src_snapshot.tar.gz` written.
- **`test_translate_sources.py`** — `<source_name>` derivation (stem, snake_case) and `--name` override; skip-if-present (present+valid → no-op; `--force` → re-translate); PDF page-render wiring; markdown verbatim passthrough + inline-image copy; `finalize_source` `meta.yaml` build + `SourceMeta` validation; error paths (no run folder, source not found, malformed `meta.yaml`).

Reused helpers (`pdf_render`, `snapshot`, `schema`) already have coverage.

### 6.2 PDF fixture

A synthetic 2-page PDF generated in-test via `pymupdf` (`new_page()` + `insert_text()`), the same pattern as the existing `pdf_render` tests. Deterministic; no binary checked into git.

### 6.3 Live verification — final plan task

A manual `/grade:translate` on a tiny real PDF. The produced `content.md` + `meta.yaml` are committed under `tests/fixtures/` as a frozen regression baseline. This is the only exercise of the live `pdf_translator` subagent dispatch; it is run once and frozen.

## 7. Open items resolved by the implementation plan

These need no further decision; the plan addresses them mechanically:

- **`SKILL.md` stub correction** — `plugins/grading/skills/translate-sources/SKILL.md` currently says raw sources live "inside the active run folder." That is wrong; raw inputs are a sibling of `runs/` at `preprocessing/inputs/sources_raw/`. The plan corrects the stub.
- **Init-time fingerprint** — no input-artifact run-ids exist at `/grade:init` time, so the fingerprint is computed as `SHA8(merged_config + git_sha)[:4]`.
- **Markdown front-matter validation** — parent spec §4.1 marks this "optional, configurable." v1 skips it entirely (pure passthrough); revisit when a real source needs it.

## 8. Acceptance criteria

- `/grade:init` creates a self-contained run folder with skeleton, `config.yaml`, `src_snapshot.tar.gz`, and `run_meta.yaml` (incl. `profile`).
- `/grade:init --profile smoke` freezes the merged config and records `profile: smoke`.
- `/grade:translate <pdf>` produces `content.md`, `figures/page_NNN.png`, and a `SourceMeta`-valid `meta.yaml` in the active run.
- `/grade:translate <md>` produces `content.md` + `meta.yaml` with no subagent dispatch.
- Re-running `/grade:translate` on an already-translated source is a no-op; `--force` re-translates.
- `/grade:translate` with no run folder present errors and points to `/grade:init`.
- `test_run_init.py` and `test_translate_sources.py` pass; the full `plugins/grading/python/tests/` suite stays green.
- A frozen live-verification baseline (`content.md` + `meta.yaml` from a real PDF) is committed under `tests/fixtures/`.
