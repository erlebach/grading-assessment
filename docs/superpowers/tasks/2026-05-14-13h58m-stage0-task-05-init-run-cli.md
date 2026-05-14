# Stage 0 Task 5 — `run_init.py` `init_run()` + CLI

**Plan:** `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` §Task 5 — **Status:** Complete — **Date:** 2026-05-14 13:58

> Part of the **Stage 0** plan (15 tasks). Distinct from the 23-task foundation plan recorded as `2026-05-13-task-NN-*.md`.

## Commits

| SHA | Message |
|---|---|
| `85d1bc9` | `feat(grading-plugin): init_run bootstrap + run_init CLI` |

## Files

- Modified: `plugins/grading/python/run_init.py` (+96 — `init_run`, git helpers, `main`)
- Modified: `plugins/grading/python/tests/test_run_init.py` (+73 — imports + 5 tests)

## Symbols introduced

- `_RUN_SUBDIRS` — the 7 stage subdirectory names.
- `_git_sha(repo_root) -> str | None`, `_git_dirty(repo_root) -> bool` — graceful (return `None`/`False` outside a git repo).
- `init_run(runs_dir, repo_root, pipeline_config, profile=None, now=None) -> Path` — creates the run-folder skeleton, writes frozen `config.yaml` (`profiles:` stripped, `--profile` overrides deep-merged), `src_snapshot.tar.gz`, and a `RunMeta`-validated `run_meta.yaml`.
- `main(argv=None) -> int` — `argparse` CLI following the `validate_run.py` pattern.

## Tests

- `test_init_run_creates_skeleton`, `test_init_run_config_excludes_profiles_key`, `test_init_run_applies_profile`, `test_init_run_meta_validates`, `test_init_run_unknown_profile_raises`.
- `test_run_init.py`: 9 passing. Full plugin suite: 116 passing.

## Reviewers

- Spec compliance: ✅ — diff matches the plan's Task 5 blocks verbatim; Task 4 helpers untouched; `profiles` stripped from `config.yaml`; test-file imports consolidated cleanly.
- Code quality: ✅ Approved — `init_run` cohesive, git degradation correct, `main()` matches `validate_run.py` pattern. Minor non-blocking notes carried forward: unused `import tarfile` in the test file; `status` written as raw string rather than `RunStatus.SUCCESS.value`; `_fake_repo` has no `.git` so the real-SHA path is untested; no test for the `--runs-dir` CLI flag.

## Notes

- `init_run` signature refines the spec's `init_run(runs_dir, config, profile=None)` by adding `repo_root` (for snapshot + git) and an injectable `now` (deterministic tests) — a deliberate plan-level refinement.
- TDD: the 5 new tests failed with `ImportError: cannot import name 'init_run'` before the implementation was appended.
