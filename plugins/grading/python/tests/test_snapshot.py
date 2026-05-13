import tarfile
from pathlib import Path

from plugins.grading.python.snapshot import create_snapshot, EXCLUDED_TOP_LEVEL


def _build_fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
    (repo / ".python-version").write_text("3.11\n")
    (repo / "plugins" / "grading" / "python").mkdir(parents=True)
    (repo / "plugins" / "grading" / "python" / "schema.py").write_text("x = 1\n")
    # Excluded top-level dirs:
    (repo / ".git" / "objects").mkdir(parents=True)
    (repo / ".git" / "objects" / "stuff").write_text("...")
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "python").write_text("...")
    (repo / "runs" / "2026-05-13_00-00-00Z__test").mkdir(parents=True)
    (repo / "runs" / "2026-05-13_00-00-00Z__test" / "f").write_text("...")
    (repo / ".specstory" / "history").mkdir(parents=True)
    (repo / ".specstory" / "history" / "log.md").write_text("...")
    # Excluded nested __pycache__:
    (repo / "plugins" / "grading" / "python" / "__pycache__").mkdir()
    (repo / "plugins" / "grading" / "python" / "__pycache__" / "x.pyc").write_bytes(b"bytecode")
    return repo


def test_excluded_top_level_set():
    assert EXCLUDED_TOP_LEVEL == frozenset({".git", ".venv", ".specstory", "runs"})


def test_snapshot_contains_expected_files(tmp_path):
    repo = _build_fake_repo(tmp_path)
    out = tmp_path / "snapshot.tar.gz"
    create_snapshot(repo, out)
    assert out.is_file()
    with tarfile.open(out, "r:gz") as tf:
        names = set(tf.getnames())
    assert any(n.endswith("pyproject.toml") for n in names)
    assert any(n.endswith(".python-version") for n in names)
    assert any(n.endswith("plugins/grading/python/schema.py") for n in names)


def test_snapshot_excludes_top_level(tmp_path):
    repo = _build_fake_repo(tmp_path)
    out = tmp_path / "snapshot.tar.gz"
    create_snapshot(repo, out)
    with tarfile.open(out, "r:gz") as tf:
        names = tf.getnames()
    for ex in EXCLUDED_TOP_LEVEL:
        assert not any(f"/{ex}/" in n or n.endswith(f"/{ex}") for n in names), ex


def test_snapshot_excludes_pycache(tmp_path):
    repo = _build_fake_repo(tmp_path)
    out = tmp_path / "snapshot.tar.gz"
    create_snapshot(repo, out)
    with tarfile.open(out, "r:gz") as tf:
        names = tf.getnames()
    assert not any("__pycache__" in n for n in names)
