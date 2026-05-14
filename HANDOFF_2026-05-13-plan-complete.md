# Handoff — grading-plugin foundation plan **complete** (Tasks 1–24)

**Branch:** `version2-self-contained-benchmark`
**Plan:** [`docs/superpowers/plans/2026-05-13-grading-plugin-foundation.md`](docs/superpowers/plans/2026-05-13-grading-plugin-foundation.md)
**Status:** ✅ All 24 tasks complete
**Last commit on plan work:** `e96beef` — `docs: extend Test Pipeline to include grading-plugin foundation tests`
**Plugin test suite:** **103 passing** (`.venv/bin/python -m pytest plugins/grading/python/tests/ -v`)

## Quick verify

```bash
git -C /Users/erlebach/src/2026/grading_assessment/autograder checkout version2-self-contained-benchmark
git -C /Users/erlebach/src/2026/grading_assessment/autograder log --oneline -25
.venv/bin/python -m pytest plugins/grading/python/tests/ -v
ls plugins/grading/.claude-plugin/plugin.json plugins/grading/config/ plugins/grading/skills/ plugins/grading/commands/ plugins/grading/hooks/ plugins/grading/python/
```

## What landed (Tasks 1–24)

| # | Subject | Final commit |
|---|---|---|
| 1 | deps + pytest config | `92a44e1` + `fa05f54` (uv.lock fix) |
| 2 | plugin scaffold + manifest | `7c5a6be` |
| 3 | role_catalog.yaml | `52e2f77` |
| 4 | tier_dispatch.yaml | `f8a6b22` |
| 5 | pipeline.yaml | `ae2910e` |
| 6 | TypeName + TypeCatalog schema | `5fbfb7a` |
| 7 | UniversalRubric + validator | `ddbc48e` (+ cleanup `1dd1f8f`) |
| 8 | PerQuestionRubric + validator | `fe29590` |
| 9 | Grades + validator | `5082a42` |
| 10 | SeedQuestion / Question / SourceMeta | `11be348` |
| 11 | RunMeta + Calibration + Answers + Coverage + Timeline | `8217627` |
| 12 | Aggregation §3.3 formula | `c2725a9` |
| 13 | Aggregation property tests (hypothesis) | `6c895b9` |
| 14 | Run resolution (`--run <prefix>`) | `4ba7783` |
| 15 | Source snapshot (`src_snapshot.tar.gz`) | `aa0f629` |
| 16 | PDF render (pymupdf) | `009f226` |
| 17 | Semantic diff between run folders | `fda8021` |
| 18 | Subagent output contract schemas | `0946f29` |
| 19 | validate_run CLI + smoke fixture | `c4d861e` |
| 20 | 8 SKILL.md stubs | `f201815` |
| 21 | 10 slash-command stubs | `49591ad` |
| 22 | Hooks scaffold | `ae94bb2` |
| 23 | CLAUDE.md test pipeline | `e96beef` |
| 24 | Final green-suite verification | (this handoff) |

Per-task records under `docs/superpowers/tasks/2026-05-13-task-NN-*.md`.

## What's now in the plugin

```
plugins/grading/
├── .claude-plugin/plugin.json
├── config/
│   ├── pipeline.yaml
│   ├── role_catalog.yaml
│   └── tier_dispatch.yaml
├── skills/                       # 8 SKILL.md stubs
│   ├── translate-sources/        prepare-seed-questions/
│   ├── review-seeds/             calibrate-types/
│   ├── test-universal/           generate-rubric/
│   ├── gold-grade/               run-course/
├── commands/                     # 10 slash-command stubs
│   ├── translate.md  seeds.md  review-seeds.md  calibrate.md  test-universal.md
│   ├── question.md  gold-grade.md  course.md  status.md  diff.md
├── hooks/
│   ├── hooks.json                # PostToolUse on Task tool → post_subagent_validate.sh
│   └── post_subagent_validate.sh # mode 100755
└── python/
    ├── aggregation.py   # §3.3 formula + worked example + hypothesis property tests
    ├── contracts.py     # judge / critic / materialize_seed / seed_gen output schemas
    ├── diff.py          # semantic diff between two run folders
    ├── pdf_render.py    # pymupdf one-PNG-per-page
    ├── run_resolution.py# git-style --run <prefix>
    ├── schema.py        # all run-folder model + validators (rubrics, grades, seeds, …)
    ├── snapshot.py      # src_snapshot.tar.gz creation
    ├── validate_run.py  # CLI + library entrypoint, plus smoke fixture under tests/
    └── tests/
        ├── fixtures/run_smoke/   # 15-file hand-crafted run-folder fixture
        └── contracts/            # 4 contract-test modules
```

Plugin test breakdown (103 total):
- schema/validator/aggregation: 41
- run_resolution: 6
- snapshot + pdf_render + diff: 10
- contract schemas: 10
- smoke fixture + validate_run: 7
- SKILL.md + command + hooks stubs: 11
- aggregation hypothesis: 3
- plugin manifest + role/tier/pipeline configs: 15

## What is *not* in scope (deferred to per-stage plans)

The plan's self-review section (lines 4570–4593 in the plan) enumerates these explicitly:

- Stage 0 — `translate-sources` orchestration + `pdf_translator` role wiring
- Stage 1 — `prepare-seed-questions` + `review-seeds` flows
- Stage 2 — calibration loop, iter_NN persistence, criterion logic on real judge output
- Stage 3 — per-question workup + overlay refinement loop
- Stage 4 — per-question batched judge dispatch + summary computation
- Orchestrator — `run-course` parallel dispatch + summary writing
- Stage-level `trace_summary.yaml` aggregation + `timeline.jsonl` emission helpers
- `REPRODUCE.md` generation
- Active-run pointer for the hook script (so `post_subagent_validate.sh` validates the *active* run rather than the most-recent one)
- Source content-addressed cache (§2 "Future enhancement")

All 8 `SKILL.md` files and 10 command stubs include a `Status: stub` marker and a pointer to the relevant spec section, so each per-stage plan starts from a named anchor.

## Pre-existing repo state notes (NOT caused by this plan)

- `tests/test_dynamic_pipeline.py`, `tests/test_mwe4.py`, and 7 other legacy tests have **collection errors** (`ModuleNotFoundError: grader.grade_question`). The renamed/deleted module pre-dates this plan (last touched in `be97575`, well before the plan started). These are not regressions from this work; they are legacy tech debt for a future cleanup.
- `git status` shows many pre-existing untracked files (`.agents/`, `.continue/`, `.specstory/`, `a*`, `*.err`, `grading_pipeline/results/`, `grading_dynamic_rubrics/...`, etc.) — all present at session start, none touched by this plan.
- The parent repo (`/Users/erlebach/src/2026/grading_assessment/.git`) also has many unrelated in-flight changes (its `CLAUDE.md`, `pyproject.toml`, `STATE.md`, several `__pycache__/*.pyc` files). Task 23 edited the parent's untracked `CLAUDE.md` for documentation parity but did not commit in that repo (per user direction).

## Next steps for the user

1. **Decide which Stage to tackle first.** Stage 0 (`translate-sources`) is the most natural entry point: it produces the `sources/` artifact that everything downstream consumes, has the simplest contract (PDF/markdown → canonical `content.md`), and exercises both `pdf_render.py` (deterministic) and a single `pdf_translator` subagent dispatch.
2. **Write the Stage 0 plan** in the same style as this foundation plan (single TDD-ordered task list with verbatim code/tests). The plan's `SKILL.md`-pointed anchors give you a starting outline.
3. **Use `subagent-driven-development` again** to execute it — the workflow has now been exercised end-to-end through 24 tasks and consistently catches both spec drift and minor code-quality issues.
4. **Consider** addressing the legacy `tests/test_dynamic_pipeline.py` import failure as a small cleanup task before the next plan, so the full-repo regression check (`pytest tests/ plugins/grading/python/tests/`) can run cleanly end-to-end.
