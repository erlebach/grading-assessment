"""Source snapshot helper per spec §2.

Produces a `src_snapshot.tar.gz` of the working tree at run time, excluding
runtime/build artifacts. Reproduction:

    tar xzf src_snapshot.tar.gz -C /tmp/rerun
    cd /tmp/rerun && uv sync
"""

from __future__ import annotations

import tarfile
from pathlib import Path


EXCLUDED_TOP_LEVEL: frozenset[str] = frozenset({
    ".git", ".venv", ".specstory", "runs",
})

EXCLUDED_ANY: frozenset[str] = frozenset({"__pycache__"})


def _should_skip(member_relpath: Path) -> bool:
    parts = member_relpath.parts
    if not parts:
        return False
    if parts[0] in EXCLUDED_TOP_LEVEL:
        return True
    return any(p in EXCLUDED_ANY for p in parts)


def create_snapshot(repo_root: Path, output: Path) -> None:
    repo_root = repo_root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    def filter_fn(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        rel = Path(tarinfo.name)
        if rel.parts and rel.parts[0] == repo_root.name:
            rel = Path(*rel.parts[1:])
        if _should_skip(rel):
            return None
        return tarinfo

    with tarfile.open(output, "w:gz") as tf:
        tf.add(repo_root, arcname=repo_root.name, filter=filter_fn)
