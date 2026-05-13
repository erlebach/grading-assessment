"""CLI + library entrypoint: validate every artifact in a run folder.

Usage:

    python -m plugins.grading.python.validate_run --run-dir <path>
    python -m plugins.grading.python.validate_run --runs-root preprocessing/runs --run 2026-05-13
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from plugins.grading.python.run_resolution import (
    most_recent_run,
    resolve_run,
)
from plugins.grading.python.schema import (
    validate_universal_rubric,
    validate_per_question_rubric,
    validate_grade,
    UniversalRubric,
)


@dataclass
class RunValidationReport:
    run_dir: Path
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml_or_record(path: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return None
    try:
        return yaml.safe_load(path.read_text())
    except Exception as exc:
        errors.append(f"YAML parse error in {path}: {exc}")
        return None


def _validate_universal_rubrics(run_dir: Path, errors: list[str]) -> dict[str, UniversalRubric]:
    out: dict[str, UniversalRubric] = {}
    types_dir = run_dir / "types"
    if not types_dir.is_dir():
        return out
    for type_dir in sorted(types_dir.iterdir()):
        rub_path = type_dir / "universal_rubric.yaml"
        raw = _load_yaml_or_record(rub_path, errors)
        if raw is None:
            continue
        try:
            out[type_dir.name] = validate_universal_rubric(raw)
        except Exception as exc:
            errors.append(f"invalid universal_rubric.yaml for {type_dir.name}: {exc}")
    return out


def _validate_per_question_rubrics_and_grades(
    run_dir: Path,
    universals: dict[str, UniversalRubric],
    errors: list[str],
) -> None:
    rub_root = run_dir / "rubrics"
    grades_root = run_dir / "grades"
    if not rub_root.is_dir():
        return
    for course_dir in sorted(rub_root.iterdir()):
        for q_dir in sorted(course_dir.iterdir()):
            rub_path = q_dir / "rubric.yaml"
            raw = _load_yaml_or_record(rub_path, errors)
            if raw is None:
                continue
            type_name = raw.get("type")
            universal = universals.get(type_name)
            if universal is None:
                errors.append(f"{rub_path}: references unknown type {type_name!r}")
                continue
            try:
                pqr = validate_per_question_rubric(raw, universal=universal)
            except Exception as exc:
                errors.append(f"invalid {rub_path}: {exc}")
                continue
            grades_path = grades_root / course_dir.name / q_dir.name / "grades.yaml"
            graw = _load_yaml_or_record(grades_path, errors)
            if graw is None:
                continue
            try:
                validate_grade(graw, rubric=pqr, universal=universal)
            except Exception as exc:
                errors.append(f"invalid {grades_path}: {exc}")


def validate_run_folder(run_dir: Path) -> RunValidationReport:
    report = RunValidationReport(run_dir=run_dir)
    universals = _validate_universal_rubrics(run_dir, report.errors)
    if not universals:
        report.errors.append(f"no universal_rubric.yaml files found under {run_dir}/types/")
    _validate_per_question_rubrics_and_grades(run_dir, universals, report.errors)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_run")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-dir", type=Path, help="absolute path to a single run folder")
    g.add_argument("--runs-root", type=Path, help="parent of runs/ ; pair with --run or default to most recent")
    parser.add_argument("--run", type=str, default=None, help="prefix to resolve under runs-root")
    args = parser.parse_args(argv)

    if args.run_dir is not None:
        run_dir = args.run_dir
    else:
        run_dir = resolve_run(args.run, args.runs_root) if args.run else most_recent_run(args.runs_root)

    report = validate_run_folder(run_dir)
    if report.ok:
        print(f"OK: {run_dir}")
        return 0
    print(f"FAIL: {run_dir}")
    for e in report.errors:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
