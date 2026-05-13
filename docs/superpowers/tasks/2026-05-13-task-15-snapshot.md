# Task 15 — Source snapshot (`src_snapshot.tar.gz`)

**Plan:** §Task 15 — **Status:** Complete — **Date:** 2026-05-13

## Commits

| SHA | Message |
|---|---|
| `aa0f629` | `feat(grading-plugin): src_snapshot.tar.gz creation with exclusions` |

## Files

- Created: `plugins/grading/python/snapshot.py`
- Created: `plugins/grading/python/tests/test_snapshot.py`

## Symbols introduced

- `EXCLUDED_TOP_LEVEL: frozenset[str]` — `{".git", ".venv", ".specstory", "runs"}`. Skipped only when they sit at the repo root.
- `EXCLUDED_ANY: frozenset[str]` — `{"__pycache__"}`. Skipped at any depth.
- `_should_skip(member_relpath) -> bool` — internal predicate.
- `create_snapshot(repo_root, output) -> None` — writes a gzip tar of the tree at `repo_root` to `output`, applying both exclusion sets via a `tarfile` filter function. Arcname uses `repo_root.name` so the archive contains a single top-level directory.

## Tests

4 passing:
- `test_excluded_top_level_set` — sanity check on the constant.
- `test_snapshot_contains_expected_files` — `pyproject.toml`, `.python-version`, and a plugin source file end up in the archive.
- `test_snapshot_excludes_top_level` — none of the excluded top-level dirs leak in.
- `test_snapshot_excludes_pycache` — nested `__pycache__/` is filtered at any depth.

Full plugin suite: 69 passing.

## Reviewers

Implementation predated this session; no in-session reviewers were dispatched. Record written retroactively after discovering commit `aa0f629` already on branch but no task record / HANDOFF update.

## Notes

Reproduction recipe (per module docstring):

```
tar xzf src_snapshot.tar.gz -C /tmp/rerun
cd /tmp/rerun && uv sync
```

The filter strips the repo-root component from the relative path before checking exclusions, so the top-level deny-list matches even though `tarfile.add(arcname=repo_root.name)` prepends that component to every member name.
