import json
from pathlib import Path

import yaml

from plugins.grading.python.schema import (
    validate_universal_rubric,
    validate_per_question_rubric,
    validate_grade,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "run_smoke"


def test_fixture_layout_present():
    for rel in [
        "inputs/type_catalog.yaml",
        "inputs/questions/fixture/Qfix01.yaml",
        "sources/fixture_source/content.md",
        "sources/fixture_source/meta.yaml",
        "types/MECHANISM/universal_rubric.yaml",
        "types/MECHANISM/calibration_meta.yaml",
        "rubrics/fixture/Qfix01/rubric.yaml",
        "synthetic_answers/fixture/Qfix01/answers.yaml",
        "synthetic_answers/fixture/Qfix01/gold_concept_coverage.yaml",
        "grades/fixture/Qfix01/grades.yaml",
        "run_meta.yaml",
        "config.yaml",
        "REPRODUCE.md",
        "traces/calibrate_types/trace_summary.yaml",
        "traces/calibrate_types/timeline.jsonl",
    ]:
        assert (FIXTURE / rel).is_file(), rel


def test_fixture_universal_rubric_validates():
    raw = yaml.safe_load((FIXTURE / "types/MECHANISM/universal_rubric.yaml").read_text())
    validate_universal_rubric(raw)


def test_fixture_per_question_rubric_validates():
    universal = validate_universal_rubric(
        yaml.safe_load((FIXTURE / "types/MECHANISM/universal_rubric.yaml").read_text())
    )
    pqr_raw = yaml.safe_load((FIXTURE / "rubrics/fixture/Qfix01/rubric.yaml").read_text())
    validate_per_question_rubric(pqr_raw, universal=universal)


def test_fixture_grades_validate():
    universal = validate_universal_rubric(
        yaml.safe_load((FIXTURE / "types/MECHANISM/universal_rubric.yaml").read_text())
    )
    pqr = validate_per_question_rubric(
        yaml.safe_load((FIXTURE / "rubrics/fixture/Qfix01/rubric.yaml").read_text()),
        universal=universal,
    )
    grades_raw = yaml.safe_load((FIXTURE / "grades/fixture/Qfix01/grades.yaml").read_text())
    validate_grade(grades_raw, rubric=pqr, universal=universal)


def test_fixture_timeline_well_formed():
    p = FIXTURE / "traces/calibrate_types/timeline.jsonl"
    lines = [ln for ln in p.read_text().splitlines() if ln.strip()]
    starts = ends = 0
    names_start: set[str] = set()
    names_end: set[str] = set()
    for ln in lines:
        ev = json.loads(ln)
        assert {"ts", "event_type", "actor", "name", "phase"} <= set(ev.keys())
        if ev["phase"] == "start":
            starts += 1
            names_start.add(ev["name"])
        else:
            ends += 1
            names_end.add(ev["name"])
    assert starts == ends and names_start == names_end
