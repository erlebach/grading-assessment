"""Semantic diff between two run folders per spec §2.

Compares like artifacts (universal rubrics, per-question rubrics, grades, …)
and returns a structured RunDiff. Stage-level coverage in this initial
implementation: universal rubrics, per-question rubrics, grades. Other
artifact types (sources, seed questions, synthetic answers) raise NotImplementedError
for now; they get added as the per-stage plans need them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RubricDiff:
    type_name: str
    weight_deltas: dict[str, float]            # axis_name -> delta
    axes_added: list[str] = field(default_factory=list)
    axes_removed: list[str] = field(default_factory=list)
    status_changed: tuple[str, str] | None = None

    def is_identical(self) -> bool:
        return (
            not self.weight_deltas
            and not self.axes_added
            and not self.axes_removed
            and self.status_changed is None
        )


@dataclass(frozen=True)
class GradesDiff:
    question_path: str
    aggregate_deltas: dict[str, float]         # answer_id -> delta

    def is_identical(self) -> bool:
        return all(d == 0.0 for d in self.aggregate_deltas.values())


@dataclass(frozen=True)
class RunDiff:
    run_a: Path
    run_b: Path
    universal_rubrics: dict[str, RubricDiff]
    grades: dict[str, GradesDiff]

    def is_identical(self) -> bool:
        return (
            all(r.is_identical() for r in self.universal_rubrics.values())
            and all(g.is_identical() for g in self.grades.values())
        )


def _load_yaml(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text())


def _diff_universal(a: dict, b: dict, type_name: str) -> RubricDiff:
    axes_a = {x["name"]: x for x in a["axes"]}
    axes_b = {x["name"]: x for x in b["axes"]}
    added = sorted(set(axes_b) - set(axes_a))
    removed = sorted(set(axes_a) - set(axes_b))
    weight_deltas: dict[str, float] = {}
    for name in set(axes_a) | set(axes_b):
        wa = axes_a.get(name, {}).get("weight", 0.0)
        wb = axes_b.get(name, {}).get("weight", 0.0)
        delta = round(wb - wa, 9)
        if delta != 0.0 or name in added or name in removed:
            weight_deltas[name] = delta
    status_changed = None
    if a.get("status") != b.get("status"):
        status_changed = (a.get("status"), b.get("status"))
    return RubricDiff(
        type_name=type_name,
        weight_deltas=weight_deltas,
        axes_added=added,
        axes_removed=removed,
        status_changed=status_changed,
    )


def _diff_grades(a: dict, b: dict, qpath: str) -> GradesDiff:
    by_a = {g["answer_id"]: g["aggregate"] for g in a["grades"]}
    by_b = {g["answer_id"]: g["aggregate"] for g in b["grades"]}
    deltas: dict[str, float] = {}
    for aid in set(by_a) | set(by_b):
        deltas[aid] = round(by_b.get(aid, 0.0) - by_a.get(aid, 0.0), 9)
    return GradesDiff(question_path=qpath, aggregate_deltas=deltas)


def diff_runs(run_a: Path, run_b: Path) -> RunDiff:
    universal_rubrics: dict[str, RubricDiff] = {}
    types_a = run_a / "types"
    types_b = run_b / "types"
    type_dirs = set()
    for base in (types_a, types_b):
        if base.is_dir():
            type_dirs.update(p.name for p in base.iterdir() if p.is_dir())
    for t in sorted(type_dirs):
        a = _load_yaml(types_a / t / "universal_rubric.yaml") or {"axes": [], "status": None}
        b = _load_yaml(types_b / t / "universal_rubric.yaml") or {"axes": [], "status": None}
        universal_rubrics[t] = _diff_universal(a, b, t)

    grades: dict[str, GradesDiff] = {}
    grades_a = run_a / "grades"
    grades_b = run_b / "grades"
    seen_qs: set[str] = set()
    for base in (grades_a, grades_b):
        if base.is_dir():
            for course_dir in base.iterdir():
                if not course_dir.is_dir():
                    continue
                for q_dir in course_dir.iterdir():
                    if (q_dir / "grades.yaml").is_file():
                        seen_qs.add(f"{course_dir.name}/{q_dir.name}")
    for qpath in sorted(seen_qs):
        course, q = qpath.split("/", 1)
        a = _load_yaml(grades_a / course / q / "grades.yaml") or {"grades": []}
        b = _load_yaml(grades_b / course / q / "grades.yaml") or {"grades": []}
        grades[qpath] = _diff_grades(a, b, qpath)

    return RunDiff(
        run_a=run_a, run_b=run_b,
        universal_rubrics=universal_rubrics, grades=grades,
    )
