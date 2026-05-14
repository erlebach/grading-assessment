# Stage 0 — `translate-sources` + run-folder init — Design

**Status:** DRAFT — design approved 2026-05-14.
**Author/Driver:** erlebach (with Claude)
**Parent spec:** `docs/superpowers/specs/2026-05-13-grading-plugin-design.md` (the ratified Option D grading-plugin design). This document is a **specification**, not an implementation plan — it expands §4.1 (Stage 0) and the run-init half of §2 into enough detail that an implementation plan can be derived from it.
**Produces:** the Stage 0 implementation plan, written next via the `writing-plans` skill into `docs/superpowers/plans/`.

**Divergence from parent spec §4.1:** the parent spec describes PDF translation as a `pdf_translator` *subagent* dispatch over rendered page images. This spec replaces that with **`marker` (`marker-pdf`), a deterministic local PDF→markdown tool** — no subagent, no LLM call. Consequently **Stage 0 is entirely deterministic Python**: no subagent dispatch anywhere, neither for PDFs nor markdown. If `marker` cannot handle a source, Stage 0 **hard-errors** rather than falling back to an LLM path — the assumption is modern born-digital PDFs (or markdown prepared by other means). An LLM fallback is explicitly *not* built now; if real sources prove it necessary, it is added as a follow-up. The `pdf_translator` role in `role_catalog.yaml` / `tier_dispatch.yaml` is left in place but unused by Stage 0 (see §7).

## 1. Scope

This document specifies the entry point of the grading pipeline: creating a run folder and translating the first source into it. Concretely:

- Two slash commands: `/grade:init` and `/grade:translate`.
- Two new Python helper modules: `run_init.py` and `translate_sources.py`.
- A new project dependency: `marker-pdf` (provides the `marker_single` CLI).
- Config additions to `plugins/grading/config/pipeline.yaml`: a `marker:` knob block and a `profiles:` block.
- One additive schema field: `RunMeta.profile`.
- A CI test suite for the Python helpers plus one frozen live-verification baseline.

Out of scope: Stages 1–4, the content-addressed source cache (parent spec §2 "Future enhancement"), an LLM translation fallback, markdown front-matter validation.

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

### `/grade:translate <source_path> [--name <n>] [--run <prefix>] [--force]`

Pure Stage 0: translate one source file into the active run folder. Never creates a run folder — errors if none exists, with a message that names `/grade:init`.

Arguments:

- `<source_path>` — path to a `.pdf` or `.md` file under `preprocessing/inputs/sources_raw/`.
- `--name <n>` — override the auto-derived `<source_name>` on collision.
- `--run <prefix>` — target a specific run folder (git-style prefix match via `run_resolution.resolve_run`); defaults to the most-recent run (`run_resolution.most_recent_run`).
- `--force` — re-translate even if a valid translation already exists (see §3.3).

## 3. Components and data flow

### 3.1 Module layout

The plugin lives at `plugins/grading/` and conforms to the Claude Code plugin layout: `.claude-plugin/plugin.json` for the manifest, with `commands/`, `skills/`, and `hooks/` at the plugin root. `python/` and `config/` are custom support directories (the documented convention for utility scripts is `scripts/`); `python/` is a deliberate importable package the foundation test suite already depends on, so it is kept as-is — renaming it is a foundation-wide refactor out of scope for Stage 0. Stage 0 adds two modules to the existing `python/` package.

All under `plugins/grading/python/`:

| Module | Status | Responsibility |
|---|---|---|
| `run_init.py` | new | `init_run(runs_dir, config, profile=None) -> Path` — run_id generation, skeleton creation, config merge, snapshot, `run_meta.yaml`. |
| `translate_sources.py` | new | `translate_source(...)` plus private helpers — fully deterministic PDF (via `marker`) and markdown translation. |
| `run_resolution.py` | reused | `resolve_run`, `most_recent_run` — `--run` prefix resolution. |
| `snapshot.py` | reused | `create_snapshot` — `src_snapshot.tar.gz`. |
| `schema.py` | reused (+1 field) | `SourceMeta` validation; `RunMeta` gains `profile`. |

`pdf_render.py` (Task 16) is **not** used by Stage 0 under this design — page rendering was only needed to feed the now-removed `pdf_translator` subagent. It is left in place; see §7.

### 3.2 `translate_sources.py` structure

Stage 0 has no subagent boundary, so the module is a single public function dispatching to deterministic helpers:

```
translate_source(source_path, run_dir, *, name=None, force=False) -> Path
  1. resolve <source_name>: input filename stem, lowercased + snake_cased; --name overrides
  2. skip-if-present check (see §3.3)
  3. dispatch on suffix:
       .pdf → _translate_pdf(source_path, dest_dir)
       .md  → _translate_markdown(source_path, dest_dir)
  4. _finalize(dest_dir, source_name, fmt, page_count, figure_count, extraction)
  5. append a python_helper_call event to traces/translate_sources/timeline.jsonl
  returns sources/<source_name>/

_translate_pdf(source_path, dest_dir) -> (page_count, figure_count, extraction)
  • run `marker_single` via subprocess into a temp output dir (flags from the marker: config block)
  • _ingest_marker_output: relocate marker's <stem>.md → content.md; relocate extracted
    images → figures/; rewrite content.md image links to point at figures/
  • hard-error if marker exits non-zero or produces no / empty content.md
  • page_count via pymupdf (fitz.open(path).page_count — no full render); figure_count = images relocated
  • extraction = {role: "marker", tier: "marker-pdf==<version>", ts: <iso8601>}

_translate_markdown(source_path, dest_dir) -> (0, figure_count, None)
  • copy file verbatim → content.md; copy inline-linked images → figures/
  • no extraction tool ran, so extraction = None

_finalize(dest_dir, name, fmt, page_count, figure_count, extraction) -> Path
  • compute content_sha over content.md
  • build + validate schema.SourceMeta; write meta.yaml
```

Every step is deterministic Python and unit-testable; `marker_single` is the one external process and is stubbed in CI (see §6).

### 3.3 Skip-if-present

Within a single run, a source is never re-translated once done — the parent spec's standing principle is "nothing inside a run folder is ever overwritten."

- If `runs/<id>/sources/<name>/content.md` exists **and** its `meta.yaml` validates, `/grade:translate` is a no-op that prints "already translated" and exits success.
- `--force` re-translates, writing into the same path — the one sanctioned overwrite.
- The check is cheap (existence + schema validation), so it never burns a `marker` run needlessly, and re-running `/grade:translate` after an earlier hard failure is safe.

Cross-run de-duplication is **not** handled here — a new run folder re-translates from scratch. That is what the deferred content-addressed source cache (parent spec §2) is for. With `marker` as the engine a re-translation costs local wall-clock time, not API tokens, so the cache stays a deferred enhancement — but its value rises with source-library size, noted for when it is picked up.

### 3.4 Data flow summary

- **PDF:** `translate_source` → `_translate_pdf` runs `marker_single` → `_ingest_marker_output` relocates markdown + figures and rewrites links → `_finalize` writes `meta.yaml`. No subagent, no LLM.
- **Markdown:** `translate_source` → `_translate_markdown` copies verbatim (+ inline images) → `_finalize` writes `meta.yaml`. No subagent, no LLM.
- **Source location:** raw sources live at `preprocessing/inputs/sources_raw/` — a sibling of `runs/`, **not** inside a run folder. They are captured by `src_snapshot.tar.gz` (which excludes only `.git/`, `.venv/`, `__pycache__/`, `.specstory/`, `runs/`), so reproducibility holds. Translated artifacts are written into `runs/<id>/sources/<name>/`.

### 3.5 Outputs

Per `/grade:translate` invocation, into the active run folder:

- `sources/<name>/content.md`
- `sources/<name>/figures/<marker-figure-name>` — `marker`'s extracted cropped figures (PDFs), referenced inline from `content.md`; or inline-linked images copied verbatim (markdown). Figure files keep `marker`'s own names; no renaming.
- `sources/<name>/meta.yaml` — `format`, `courses`, `topics`, `extraction` (`{role, tier, ts}`; `None` for markdown), `content_sha`, `figure_count`, `page_count`. Validated against `schema.SourceMeta`.
- `traces/translate_sources/timeline.jsonl` — append-only; one `python_helper_call` event per invocation (parent spec §4.0 invariant). No `<subagent_id>.json` record — Stage 0 dispatches no subagent.

## 4. Config additions

To `plugins/grading/config/pipeline.yaml`:

### `marker:` block

`marker` invocation knobs. Defaults match the user's proven `marker_single` flag set (OCR disabled — born-digital PDFs; image extraction on):

```yaml
marker:
  ocr: false               # --disable_ocr when false; enable for scanned PDFs
  extract_images: true     # extract + inline-reference figures
```

This replaces the parent spec's `pdf_translator` knob block (`verbosity`, `figure_inclusion`) — those described an LLM translator that no longer exists.

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

Stage 0 itself does not branch on the profile — `translate_source` translates one file regardless. `/grade:init` is simply where the profile is resolved, merged, and frozen into `runs/<id>/config.yaml`; the profile name is also recorded in `run_meta.yaml` so a scoped test run is self-describing.

## 5. Schema delta

`schema.RunMeta` gains one additive field:

```python
profile: str | None = None
```

Records the active profile name in `run_meta.yaml` so it is visible without parsing the merged config. Additive, no migration.

`schema.SourceMeta` / `ExtractionMeta` are reused unchanged: for `marker` PDFs, `extraction` is `{role: "marker", tier: "marker-pdf==<version>", ts: <iso8601>}`. The `role` / `tier` field names were coined for LLM dispatch and are a mild semantic stretch here; reused as-is to avoid schema churn (see §7).

## 6. Testing

Strategy: CI tests for the Python helpers only, with `marker_single` stubbed; plus one documented live verification (real `marker`) frozen as a regression baseline.

### 6.1 CI — Python helpers

New test files under `plugins/grading/python/tests/`:

- **`test_run_init.py`** — run_id format + fingerprint determinism; skeleton directory creation; base-config → merged-config with and without a profile; `run_meta.yaml` contents incl. `profile`; `config.yaml` written; `src_snapshot.tar.gz` written.
- **`test_translate_sources.py`** — `<source_name>` derivation (stem, snake_case) and `--name` override; skip-if-present (present+valid → no-op; `--force` → re-translate); `_translate_pdf` invokes `marker_single` with the flags implied by the `marker:` config; `_ingest_marker_output` relocates markdown + figures and rewrites image links correctly; hard-error when the stubbed `marker_single` exits non-zero or yields empty `content.md`; `_translate_markdown` verbatim passthrough + inline-image copy; `_finalize` `meta.yaml` build + `SourceMeta` validation; `timeline.jsonl` `python_helper_call` event appended; error paths (no run folder — and the error message names `/grade:init`; source not found).

`marker_single` is stubbed: a fake executable / monkeypatched subprocess that writes a known `marker`-style output directory (a `<stem>.md` with image links plus image files). This lets CI verify all ingestion and link-rewriting logic without `marker`'s ML model weights.

Reused helpers (`snapshot`, `schema`, `run_resolution`) already have coverage.

### 6.2 PDF fixture

A synthetic PDF generated in-test via `pymupdf` (`new_page()` + `insert_text()`, and `insert_image()` so the live baseline exercises figure extraction). Deterministic; no binary checked into git. Whether the live baseline instead uses a small committed real-world PDF is a plan-level fixture decision (§7).

### 6.3 Live verification — final plan task

A manual `/grade:translate` on a real PDF with at least one figure, running `marker` for real. The produced `content.md`, `figures/`, and `meta.yaml` are committed under `tests/fixtures/` as a frozen regression baseline. This is the only exercise of real `marker`; it is run once and frozen.

## 7. Open items resolved by the implementation plan

These need no further design decision; the plan addresses them mechanically:

- **`SKILL.md` stub correction** — `plugins/grading/skills/translate-sources/SKILL.md` currently says raw sources live "inside the active run folder" and describes a `pdf_translator` subagent. Both are now wrong; the plan rewrites the stub for the `marker`, no-subagent flow with raw inputs at `preprocessing/inputs/sources_raw/`.
- **`pdf_translator` role / `pdf_render.py`** — both are now unused by Stage 0. Left in place (Task 16 / parent-spec artifacts); whether to remove the `pdf_translator` entries from `role_catalog.yaml` / `tier_dispatch.yaml` and retire `pdf_render.py` is a separate cleanup, not Stage 0's concern.
- **`marker-pdf` version pinning** — `marker` is an ML pipeline; reproducibility requires the `marker-pdf` version pinned in the project lockfile (the model weights themselves are external, like the Claude model weights). The exact version is a plan/dependency decision.
- **`ExtractionMeta` field naming** — `role` / `tier` are LLM-dispatch terms; reused as-is for `marker`. A rename is deferred unless it proves confusing.
- **Init-time fingerprint** — no input-artifact run-ids exist at `/grade:init` time, so the fingerprint is computed as `SHA8(merged_config + git_sha)[:4]`.
- **Markdown front-matter validation** — parent spec §4.1 marks this "optional, configurable." v1 skips it entirely (pure passthrough); revisit when a real source needs it.
- **Live-baseline fixture choice** — synthetic `pymupdf` PDF with an embedded image vs. a small committed real PDF (§6.2).

## 8. Acceptance criteria

- `/grade:init` creates a self-contained run folder with skeleton, `config.yaml`, `src_snapshot.tar.gz`, and `run_meta.yaml` (incl. `profile`).
- `/grade:init --profile smoke` freezes the merged config and records `profile: smoke`.
- `/grade:translate <pdf>` runs `marker`, producing `content.md`, `marker`'s extracted figures under `figures/` (with `content.md` image links pointing into `figures/`), and a `SourceMeta`-valid `meta.yaml`.
- `/grade:translate <md>` produces `content.md` + `meta.yaml` (verbatim passthrough, inline images copied).
- A source `marker` cannot translate (non-zero exit or empty `content.md`) causes a hard error surfaced to the user — no LLM fallback.
- Re-running `/grade:translate` on an already-translated source is a no-op; `--force` re-translates.
- `/grade:translate` with no run folder present errors with a message that names `/grade:init`.
- Each `/grade:translate` invocation appends a `python_helper_call` event to `traces/translate_sources/timeline.jsonl`.
- `test_run_init.py` and `test_translate_sources.py` pass (with `marker_single` stubbed); the full `plugins/grading/python/tests/` suite stays green.
- A frozen live-verification baseline (`content.md`, `figures/`, `meta.yaml` from a real `marker` run on a real PDF) is committed under `tests/fixtures/`.
