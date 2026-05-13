"""--run <prefix> resolution per spec §2.

Resolution semantics:
- Exact match wins.
- Otherwise, prefix-match against directory names sorted descending.
- Exactly one match: return it.
- Zero matches: NoRunMatch.
- Two or more matches: AmbiguousRunPrefix with the candidate list.
"""

from __future__ import annotations

from pathlib import Path


class NoRunMatch(LookupError):
    pass


class AmbiguousRunPrefix(LookupError):
    def __init__(self, prefix: str, candidates: list[str]) -> None:
        self.prefix = prefix
        self.candidates = candidates
        super().__init__(
            f"prefix {prefix!r} matches {len(candidates)} runs: "
            + ", ".join(candidates)
        )


def _list_run_dirs(runs_dir: Path) -> list[Path]:
    if not runs_dir.is_dir():
        return []
    return sorted([p for p in runs_dir.iterdir() if p.is_dir()])


def resolve_run(prefix: str, runs_dir: Path) -> Path:
    candidates = _list_run_dirs(runs_dir)
    exact = [p for p in candidates if p.name == prefix]
    if exact:
        return exact[0]

    prefix_hits = [p for p in candidates if p.name.startswith(prefix)]
    if not prefix_hits:
        raise NoRunMatch(f"no run matched prefix {prefix!r} under {runs_dir}")
    if len(prefix_hits) > 1:
        raise AmbiguousRunPrefix(prefix, [p.name for p in prefix_hits])
    return prefix_hits[0]


def most_recent_run(runs_dir: Path) -> Path:
    candidates = _list_run_dirs(runs_dir)
    if not candidates:
        raise NoRunMatch(f"no runs in {runs_dir}")
    return candidates[-1]
