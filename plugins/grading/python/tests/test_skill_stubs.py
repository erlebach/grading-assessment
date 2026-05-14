import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PLUGIN_ROOT / "skills"

EXPECTED_SKILLS = {
    "translate-sources",
    "prepare-seed-questions",
    "review-seeds",
    "calibrate-types",
    "test-universal",
    "generate-rubric",
    "gold-grade",
    "run-course",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    assert m, "missing frontmatter"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def test_all_skill_dirs_present():
    actual = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    assert actual == EXPECTED_SKILLS


def test_every_skill_has_SKILL_md():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        assert path.is_file(), name


def test_frontmatter_name_matches_dir():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        fm = _frontmatter(path.read_text())
        assert fm.get("name") == name, f"{name}: frontmatter name = {fm.get('name')!r}"


def test_frontmatter_has_description():
    for name in EXPECTED_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        fm = _frontmatter(path.read_text())
        assert fm.get("description"), name


def test_body_marks_stub_status():
    for name in EXPECTED_SKILLS - {"translate-sources"}:
        path = SKILLS_DIR / name / "SKILL.md"
        text = path.read_text()
        assert "Status: stub" in text, name
