import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = PLUGIN_ROOT / "commands"

EXPECTED = {
    "init": None,             # no skill — direct python helper
    "translate": "translate-sources",
    "seeds": "prepare-seed-questions",
    "review-seeds": "review-seeds",
    "calibrate": "calibrate-types",
    "test-universal": "test-universal",
    "question": "generate-rubric",
    "gold-grade": "gold-grade",
    "course": "run-course",
    "status": None,           # no skill — direct python helper
    "diff": None,             # no skill — direct python helper
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    assert m, "missing frontmatter"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def test_all_command_files_present():
    actual = {p.stem for p in COMMANDS_DIR.glob("*.md")}
    assert actual == set(EXPECTED)


def test_each_command_has_description():
    for name in EXPECTED:
        fm = _frontmatter((COMMANDS_DIR / f"{name}.md").read_text())
        assert fm.get("description"), name


def test_each_command_references_its_skill_or_helper():
    for name, skill in EXPECTED.items():
        body = (COMMANDS_DIR / f"{name}.md").read_text()
        if skill:
            assert f"grading:{skill}" in body, f"{name} -> {skill}"
        else:
            assert "plugins/grading/python/" in body, name
