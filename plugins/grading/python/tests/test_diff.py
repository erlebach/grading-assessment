from pathlib import Path

import yaml

from plugins.grading.python.diff import (
    diff_runs,
    RunDiff,
    RubricDiff,
    GradesDiff,
)


def _write_universal(path: Path, weights: dict[str, float]):
    path.parent.mkdir(parents=True, exist_ok=True)
    axes = [
        {
            "name": name,
            "description": "",
            "weight": w,
            "score_levels": {
                "full":    {"value": 1.0, "criterion": "x"},
                "partial": {"value": 0.5, "criterion": "x"},
                "none":    {"value": 0.0, "criterion": "x"},
            },
        }
        for name, w in weights.items()
    ]
    yaml.safe_dump(
        {
            "type": "MECHANISM",
            "status": "frozen",
            "axes": axes,
            "aggregate": {"method": "weighted_mean", "out_of": 10.0},
        },
        path.open("w"),
    )


def _write_grades(path: Path, aggregates: dict[str, float]):
    path.parent.mkdir(parents=True, exist_ok=True)
    grades = [
        {
            "answer_id": aid,
            "per_concept": {"c1": {"a": "full"}},
            "aggregate": agg,
            "aggregate_x10": agg * 10,
        }
        for aid, agg in aggregates.items()
    ]
    yaml.safe_dump(
        {
            "question_id": "Q",
            "rubric_ref": "rubrics/c/Q/rubric.yaml",
            "universal_rubric_ref": "types/MECHANISM/universal_rubric.yaml",
            "grades": grades,
            "summary": {
                "mean_by_quality": {"good": 1.0, "less_good": 0.5, "wrong": 0.0},
                "ordering_preserved": True,
                "bands_satisfied": True,
                "axis_discrimination_passed": True,
            },
        },
        path.open("w"),
    )


def test_diff_identical_runs(tmp_path):
    for label in ("a", "b"):
        root = tmp_path / label
        _write_universal(root / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 0.5, "b": 0.5})
        _write_grades(root / "grades" / "c" / "Q" / "grades.yaml", {"good_1": 1.0})
    d = diff_runs(tmp_path / "a", tmp_path / "b")
    assert isinstance(d, RunDiff)
    assert d.is_identical()


def test_diff_axis_weight_change(tmp_path):
    _write_universal(tmp_path / "a" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 0.5, "b": 0.5})
    _write_universal(tmp_path / "b" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 0.7, "b": 0.3})
    d = diff_runs(tmp_path / "a", tmp_path / "b")
    rubric_diff = d.universal_rubrics["MECHANISM"]
    assert isinstance(rubric_diff, RubricDiff)
    assert rubric_diff.weight_deltas == {"a": 0.2, "b": -0.2}


def test_diff_grade_score_change(tmp_path):
    _write_universal(tmp_path / "a" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 1.0})
    _write_universal(tmp_path / "b" / "types" / "MECHANISM" / "universal_rubric.yaml", {"a": 1.0})
    _write_grades(tmp_path / "a" / "grades" / "c" / "Q" / "grades.yaml", {"good_1": 1.0, "less_good_1": 0.5})
    _write_grades(tmp_path / "b" / "grades" / "c" / "Q" / "grades.yaml", {"good_1": 0.9, "less_good_1": 0.5})
    d = diff_runs(tmp_path / "a", tmp_path / "b")
    gd = d.grades["c/Q"]
    assert isinstance(gd, GradesDiff)
    assert gd.aggregate_deltas == {"good_1": -0.1, "less_good_1": 0.0}
