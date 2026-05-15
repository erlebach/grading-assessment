# Handoff — Stage 0 complete; branch integration blocked on a git-topology decision

**Date:** 2026-05-14 21:30 EDT
**Branch:** `version2-self-contained-benchmark`
**HEAD:** `2e1ff20`
**Status:** Stage 0 plan is **fully complete** (15/15 tasks + final review + fixes, all committed). The remaining work is **integrating the branch** — and that surfaced a tangled git-remote topology. A plan is decided; execution is paused on a `gh auth` check that timed out in the sandbox.

---

## Part 1 — Stage 0: DONE

The `superpowers:subagent-driven-development` execution of `docs/superpowers/plans/2026-05-14-stage0-translate-sources.md` is complete.

- All 15 tasks done; per-task records in `docs/superpowers/tasks/2026-05-14-*-stage0-task-*.md` (records 1–15).
- Final whole-implementation review (opus, range `7aec57b..`) → **ready-to-merge-with-fixes, no Critical**. 3 Important items, all fixed:
  - **#2** — `_invoke_marker_single` now catches `FileNotFoundError` → clean `RuntimeError` pointing at `README_preprocessing.md`. (commit `776499d`)
  - **doc bug** — `translate.md` no longer claims marker is "installed via the marker-pdf dependency". (commit `776499d`)
  - **#1** — baseline fixture re-frozen so `meta.yaml` records `tier: marker-pdf==1.10.2` not `unknown`. (commit `d960ad1`)
  - **#3** (partial `sources/<name>/` dir on failed translation) — deferred as a follow-up per the reviewer's own call. NOT done.
- Re-review of the 3 fixes → all confirmed resolved, clean.
- Plugin suite green at **147** (`.venv/bin/python -m pytest plugins/grading/python/tests/ -q`).
- Final-review **Minor** items NOT actioned (not requested): unhandled `_pdf_page_count` failure, thin `timeline.jsonl` payload, scattered mid-file test imports, minimal `marker_single` config knobs, optional `test_baseline_meta_validates` tier-pattern assertion.

### This session's commits (all on `version2-self-contained-benchmark`, after the prior handoff `cd28bb6`)

```
2e1ff20 docs: JOURNAL — Stage 0 plan complete; final review + fixes
d960ad1 test(grading-plugin): re-freeze Stage 0 baseline with resolved marker-pdf version
776499d fix(grading-plugin): clean error when marker_single is not on PATH
03f9508 docs(grading-plugin): Stage 0 per-task record 15
ddd33c1 docs: JOURNAL — Stage 0 Task 14 done; _marker_pdf_version external resolution
b208349 fix(grading-plugin): resolve marker-pdf version from external install
35f1731 docs(grading-plugin): Stage 0 per-task record 14
c461221 test(grading-plugin): frozen Stage 0 live-verification baseline
b45ed7c docs: JOURNAL — dropped marker-pdf from project deps
707702b build: drop marker-pdf from project deps; require external marker_single
```

Also early in the session: the **cancelled prior-session Task 14 subagent commit `5eec789` was reverted** (`git reset --soft HEAD~1` + file removal) and the venv restored to locked versions. `marker-pdf` was then deliberately **dropped from `pyproject.toml`** — it is an external `uv tool` install (`~/.local/bin/marker_single`, 1.10.2); the project only shells out to the CLI, never imports the package. `README_preprocessing.md` (new, top-level) documents the external prerequisite.

---

## Part 2 — Branch integration: the git-topology problem

The user invoked `superpowers:finishing-a-development-branch` and chose to **merge to `dynamic_rubrics`**. That uncovered a tangled topology. Hard-won findings (a fresh session would not know any of this):

### Two local repos, one shared remote

- **`autograder/.git`** — repo rooted at `autograder/`. Current branch `version2-self-contained-benchmark` (HEAD `2e1ff20`). This is the "new" repo, the result of a past "transfer git history to autograder/" operation.
- **`/Users/erlebach/src/2026/grading_assessment/.git`** (i.e. `../.git`) — repo rooted at the **parent** `grading_assessment/` dir (everything nested under an `autograder/` subdir). Currently on branch `v2-concept-rubrics`. This is the "old" repo.
- **Both share the same remote:** `origin = https://github.com/erlebach/grading-assessment.git`.

### `dynamic_rubrics` is disjoint between local and origin

- Local `dynamic_rubrics` (`faea094`) and `origin/dynamic_rubrics` (`e318edc`) have **NO common ancestor** — `git merge-base` returns nothing.
- Cause: local is `autograder/`-rooted, `origin/dynamic_rubrics` is `grading_assessment/`-rooted (top-level tree: `.gitignore`, `Claude.md per Project_6968ef86.md`, `autograder/`).
- The "88 local-ahead / 89 origin-ahead" commits are the **same logical commits** (matching messages + timestamps, different SHAs from the re-root). The **only** origin-unique commit is `3adb4da` "Add root .gitignore…" — parent-rooted, structurally obsolete for an `autograder/`-rooted repo.
- `version2-self-contained-benchmark` is 137 commits ahead of local `dynamic_rubrics`; it branched cleanly from local `dynamic_rubrics` at `faea094`, so a local merge would **fast-forward**.

### The parent repo `../.git` holds nothing unique

Verified read-only: 3 branches (`main` `4b9b516`, `v2-concept-rubrics` `992bf60`, `dynamic_rubrics` `e318edc`), **0 tags, no stashes**. All 3 branch tips are on `origin` (`dynamic_rubrics`=`e318edc` is *identical* to `origin/dynamic_rubrics`). So `../.git` could be deleted with **no loss of git history** — everything is on the remote.

### `origin/version2-self-contained-benchmark` is clean

Exists at `4298caa`, `autograder/`-rooted, shares history with local — local is **76 ahead, 0 behind** → a plain fast-forward push is available any time.

---

## Part 3 — The DECIDED plan (paused on a `gh` check)

The user settled on this approach (chosen over both "merge locally only" and "delete `../.git`" — it is **non-destructive** and keeps the parent repo alive as its own independent repo):

1. **Create a separate remote for the parent repo:** `https://github.com/erlebach/grading-assessment_parent.git` via `gh repo create`.
2. **Re-link `../.git`** so its `origin` points at `grading-assessment_parent.git` instead of the shared `grading-assessment.git`; push its 3 branches there (`git push -u origin --all`). This fully decouples the two repos.
   - ⚠️ `git remote set-url` writes to `.git/config`. The project `CLAUDE.md` says "NEVER update the git config." Get explicit user OK for that one command, or hand the user the exact command to run themselves.
3. **Local merge in `autograder/.git`:** `git stash` → `git checkout dynamic_rubrics` → `git merge version2-self-contained-benchmark` (fast-forward) → `.venv/bin/python -m pytest plugins/grading/python/tests/ -q` (expect **147**) → `git stash pop`.
   - ⚠️ A plain `git checkout dynamic_rubrics` is **blocked** by uncommitted working-tree changes — must stash first. See "Working tree state" below.
4. **Option C — replace the shared remote's `dynamic_rubrics`:** `git push --force-with-lease origin dynamic_rubrics`. Now safe because `../.git` no longer uses this remote. User has accepted that this intentionally drops `3adb4da` (obsolete parent `.gitignore`) and `Claude.md per Project_6968ef86.md` (a 3871-line exported ChatGPT transcript the user already deleted from disk).
5. **Cleanup:** `git branch -d version2-self-contained-benchmark` after the merge, and/or `git push origin version2-self-contained-benchmark` (clean ff). User has NOT yet picked which — ask.

### BLOCKER / where it stopped

Step 1's prerequisite check (`gh auth status`, and `gh repo view erlebach/grading-assessment_parent`) **timed out in the sandbox**: `"Timeout trying to log in to github.com account erlebach (keyring)"` and `"Post https://api.github.com/graphql: context deadline exceeded"`. Likely a sandbox keyring/network restriction.

**Resume by:** retrying the `gh` checks with `dangerouslyDisableSandbox: true` (keyring + GitHub API access). Confirm `gh` is authenticated and whether `grading-assessment_parent` already exists. Then proceed through steps 1–5, confirming with the user at the `git remote set-url` step and the force-push step.

---

## Working tree state (`autograder/.git`)

- **`v2/judge.py`** — modified, uncommitted (8 insertions / 4 deletions of real source). **Predates this session — leave it.** It is carried through the merge via stash/pop.
- **3 tracked `.pyc` files** (`tests/__pycache__/test_mwe{1,2,4}*.pyc`) — modified by test runs; also blocks `git checkout`. Stashed/popped with the rest.
- Large pile of untracked scratch files (`a`, `a.sh`, `err`, `.agents/`, etc.) — pre-existing noise, ignore. (`3adb4da` on origin was the commit that would have gitignored these — it is being intentionally dropped.)

## Environment gotchas hit this session

- **`cp` is aliased to `cp -i`** — it silently defaulted to "no" on overwrite **twice** this session. Use `/bin/cp` or `cp -f`.
- **`grep` errors** in this shell (`grep:9: permission denied: …/claude.exe`) — use `git grep` instead.
- **Sandbox:** `marker_single` runs and `uv`/`gh` cache+network operations need `dangerouslyDisableSandbox: true` (model weights under `~/Library/Caches/datalab`, uv cache under `~/.cache/uv`, gh keyring).
- The broader `tests/` suite has 9 collection errors + 26 failures — **all pre-existing or environmental, verified NOT regressions** from this work. Do not be alarmed; out of scope.

## Resume recipe

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
git log --oneline -1                                          # expect 2e1ff20 (or this handoff commit on top)
.venv/bin/python -m pytest plugins/grading/python/tests/ -q    # expect 147 passed
gh auth status                                                # retry with sandbox disabled if it times out
```

Then resume Part 3 from step 1.
