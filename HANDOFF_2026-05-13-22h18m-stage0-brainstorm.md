# Handoff — Stage 0 (`translate-sources`) brainstorming, mid-session pause

**Date:** 2026-05-13 22:18 EDT
**Branch:** `version2-self-contained-benchmark`
**Status:** Mid-brainstorm (not yet at design proposal / spec write)
**Active skill:** `superpowers:brainstorming` — re-invoke it on resume.

## Where we are

The foundation plan (Tasks 1–24) is fully complete — see [`HANDOFF_2026-05-13-plan-complete.md`](HANDOFF_2026-05-13-plan-complete.md). Plugin test suite at **103 passing**. Last plan-work commit: `b0fdb95` (per-task records 16–23 + plan-completion HANDOFF).

We then began brainstorming **Stage 0 — `translate-sources`** (spec §4.1 in `docs/superpowers/specs/2026-05-13-grading-plugin-design.md`). Two of three clarifying questions are answered. One remains.

## Decisions captured so far

| Question | Choice |
|---|---|
| **Plan scope** | **Option 1 — bundle run-folder init into the Stage 0 plan.** Single plan covers a small `init_run()` helper + `/grade:init` (or `--init` flag on translate) + markdown passthrough + PDF subagent dispatch. Init logic small enough that splitting adds more overhead than it removes. |
| **PDF-dispatch test strategy** | **Option 1 — CI tests for Python helpers only + documented live verification.** All Python helpers (init, render, passthrough, finalize, validation) get unit + fixture coverage. Plan's final task is a manual live `/grade:translate` on a tiny real PDF; the produced `content.md` + `meta.yaml` get committed as a frozen regression baseline. No fake subagent in code. |

## Outstanding question (next on resume)

**Active-run convention.** Init creates a new folder; subsequent stages need to know which folder to operate on. Options offered (full text in question history):

1. **Most-recent run (no pointer file)** — keep current convention: `active = most_recent_run()`. `--run <prefix>` overrides. Matches the existing hook + `run_resolution.py`. No new on-disk state. *(Recommended.)*
2. **Explicit `.active` pointer file** — init writes `preprocessing/runs/.active`; helpers prefer it, fall back to lexicographic order. Adds a small helper + stale-pointer invariant.
3. **Explicit `--run` always required** — no active-run concept. Forces clarity, annoying for the common case.

User answered "write a handoff" instead of picking; that's why we paused here.

## Questions still to ask after that

These are queued; some may compress into the design proposal:

- **Bootstrap surface area** — does init also write `src_snapshot.tar.gz` + `config.yaml` snapshot at init time, or only on first stage completion? (Spec §2 says both are run-folder artifacts; only timing is open.)
- **Slash command shape** — `/grade:init` as a separate command, or `--init` flag on `/grade:translate` that auto-creates if no run exists? (10-command stub list does *not* include `init` today; SKILL.md and command stubs for `translate` already exist.)
- **Python helper split** — one new `translate_sources.py` with `prepare_source()` + `finalize_source()` (the subagent boundary), or finer-grained modules? Most likely one module given how small Stage 0 is.
- **Markdown front-matter validation** — spec §4.1 says "optional, configurable". Should v1 of the plan skip it entirely and just passthrough? (Recommended: skip; revisit when a user actually needs it.)
- **Source naming + `--name` collision arg** — already in `commands/translate.md`. Just need to wire it.
- **Live-verification fixture choice** — what tiny real PDF do we use? A 2-page synthetic PDF generated via `pymupdf.new_page() + insert_text()` (same pattern Task 16 used) keeps it deterministic and avoids checking a binary into git.

## Spec / file references (for resume)

- Design spec: `docs/superpowers/specs/2026-05-13-grading-plugin-design.md` §4.1 (Stage 0), §1 (Invocation), §2 (Run isolation), §6.4 (Live end-to-end), §6.6 (Plugin-level tests).
- SKILL.md stub: `plugins/grading/skills/translate-sources/SKILL.md` — already lays out inputs/outputs/algorithm at stub level.
- Command stub: `plugins/grading/commands/translate.md` — has `<source_path>`, `--name`, `--run` args.
- Existing Python helpers Stage 0 will lean on:
  - `plugins/grading/python/pdf_render.py:render_pages` (Task 16, done).
  - `plugins/grading/python/run_resolution.py` (`resolve_run`, `most_recent_run`).
  - `plugins/grading/python/snapshot.py:create_snapshot` (for `src_snapshot.tar.gz`).
  - `plugins/grading/python/schema.py:SourceMeta` + `validate_*` validators.
- Configs:
  - `plugins/grading/config/role_catalog.yaml` (line 6: `pdf_translator` role declared).
  - `plugins/grading/config/tier_dispatch.yaml` (line 8: `pdf_translator: claude-opus-4-7`).
  - `plugins/grading/config/pipeline.yaml` — currently has no `pdf_translator` knobs; spec §4.1 says they exist (`verbosity`, `figure inclusion threshold`). Plan should decide whether to add them now or defer.

## Resume recipe

```bash
git -C /Users/erlebach/src/2026/grading_assessment/autograder checkout version2-self-contained-benchmark
git -C /Users/erlebach/src/2026/grading_assessment/autograder log --oneline -5
.venv/bin/python -m pytest plugins/grading/python/tests/ -q   # expect 103 passed
```

Then in the new Claude Code session: open this file, re-invoke `/superpowers:brainstorming`, and pick up at the **Active-run convention** question (with the recommendation toward Option 1 — most-recent run, no pointer file).

The brainstorming skill's terminal state is invoking `writing-plans`. We are 2–4 questions away from being ready to propose the design and write the spec.
