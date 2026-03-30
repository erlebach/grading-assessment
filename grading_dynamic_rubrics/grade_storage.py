"""T3.4 — Grade storage and appeal tracking.

Public API
----------
store_grade(grade: GradeResult, data_dir: Path) -> Path
store_grade_appeal(appeal: Appeal, data_dir: Path) -> Path
get_grade_history(student_id: str, question_id: str, data_dir: Path) -> list[GradeResult]
validate_grade_increase(original_score: float, new_score: float) -> None
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from grading_pipeline.models import Appeal, GradeResult


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _grades_final_dir(data_dir: Path) -> Path:
    d = data_dir / "grades" / "final"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _appeals_dir(data_dir: Path) -> Path:
    d = data_dir / "appeals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _grade_filename(student_id: str, question_id: str, version: int) -> str:
    return f"{student_id}_{question_id}_grade_v{version}.json"


def _appeal_filename(student_id: str, question_id: str, version: int, timestamp: str) -> str:
    # Normalise timestamp: strip microseconds and keep ISO format with T separator
    ts = timestamp.replace(" ", "T").split(".")[0]
    return f"appeal_{student_id}_{question_id}_v{version}_{ts}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_grade_increase(original_score: float, new_score: float) -> None:
    """Raise ValueError if new_score is less than original_score.

    Parameters
    ----------
    original_score:
        The grade being superseded.
    new_score:
        The proposed replacement grade.

    Raises
    ------
    ValueError
        When ``new_score < original_score``.
    """
    if new_score < original_score:
        raise ValueError(
            f"Grade adjustment must be upward: new_score ({new_score}) < "
            f"original_score ({original_score})"
        )


def store_grade(
    grade: GradeResult,
    data_dir: Union[str, Path],
) -> Path:
    """Persist a GradeResult to disk.

    The file is written to ``data_dir/grades/final/`` following the naming
    convention ``{student_id}_{question_id}_grade_v{N}.json``.  An existing
    file at that path is **never** overwritten — a FileExistsError is raised
    instead so the caller can decide how to proceed.

    Parameters
    ----------
    grade:
        The fully-populated GradeResult to store.
    data_dir:
        Root data directory (contains ``grades/``, ``appeals/``, etc.)

    Returns
    -------
    Path
        Absolute path to the written file.

    Raises
    ------
    FileExistsError
        If a file for this student/question/version already exists.
    """
    data_dir = Path(data_dir)
    target_dir = _grades_final_dir(data_dir)
    filename = _grade_filename(grade.student_id, grade.question_id, grade.version)
    path = target_dir / filename

    if path.exists():
        raise FileExistsError(
            f"Grade file already exists (never overwrite): {path}"
        )

    path.write_text(grade.model_dump_json(indent=2), encoding="utf-8")
    return path


def store_grade_appeal(
    appeal: Appeal,
    data_dir: Union[str, Path],
) -> Path:
    """Persist an Appeal record to disk.

    The file is written to ``data_dir/appeals/`` following the naming
    convention ``appeal_{student_id}_{question_id}_v{N}_{ISO_timestamp}.json``.

    Parameters
    ----------
    appeal:
        The fully-populated Appeal to store.
    data_dir:
        Root data directory.

    Returns
    -------
    Path
        Absolute path to the written file.

    Raises
    ------
    ValueError
        If the appeal's new_score is less than original_score (enforced by
        the Appeal model validator, but also checked here for clarity).
    """
    data_dir = Path(data_dir)

    # Extract version from appeal id, e.g. "appeal_student_001_q01_v1"
    # Fall back to counting existing files + 1 if id format differs.
    version = _extract_appeal_version(appeal)

    timestamp = appeal.requested_at.strftime("%Y-%m-%dT%H:%M:%S")
    filename = _appeal_filename(
        appeal.student_id, appeal.question_id, version, timestamp
    )
    target_dir = _appeals_dir(data_dir)
    path = target_dir / filename

    if path.exists():
        raise FileExistsError(
            f"Appeal file already exists (never overwrite): {path}"
        )

    path.write_text(appeal.model_dump_json(indent=2), encoding="utf-8")
    return path


def get_grade_history(
    student_id: str,
    question_id: str,
    data_dir: Union[str, Path],
) -> list[GradeResult]:
    """Return all stored GradeResult versions for a student/question pair.

    Results are returned in ascending version order (v1 first).

    Parameters
    ----------
    student_id:
        Student identifier.
    question_id:
        Question identifier.
    data_dir:
        Root data directory.

    Returns
    -------
    list[GradeResult]
        All stored grades, sorted by ``version`` ascending.  Empty list if
        none exist.
    """
    data_dir = Path(data_dir)
    target_dir = _grades_final_dir(data_dir)

    prefix = f"{student_id}_{question_id}_grade_v"
    files = sorted(target_dir.glob(f"{prefix}*.json"))

    results: list[GradeResult] = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        results.append(GradeResult.model_validate(data))

    results.sort(key=lambda g: g.version)
    return results


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------

def _extract_appeal_version(appeal: Appeal) -> int:
    """Try to parse the version number from the appeal id field.

    Expected format: ``appeal_{student_id}_{question_id}_v{N}`` or any string
    ending with ``_v{N}``.  Falls back to 1 on parse failure.
    """
    parts = appeal.id.rsplit("_v", 1)
    if len(parts) == 2:
        try:
            return int(parts[1])
        except ValueError:
            pass
    return 1
