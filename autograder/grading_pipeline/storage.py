"""
Data storage structure management for the weighted checklist grading system.

Organizes and manages directory structure for:
- Generated rubrics (raw, extracted, categorized, deduped)
- Student grades (evaluation results, final scores)
- Grade appeals (version history)
- Logs (grading runs, errors)
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import json
import os

from .models import Check, Rubric, GradeResult, Appeal


class StorageManager:
    """
    Manages the directory structure for grading system data.

    Naming conventions:
    - Rubrics: {base}/rubrics/{question_id}/rubric_v{version}.json
    - Grades: {base}/grades/{question_id}/{student_id}_v{version}.json
    - Appeals: {base}/appeals/{question_id}/{student_id}_appeal_v{version}.json
    - Logs: {base}/logs/{YYYY-MM-DD}.log
    """

    def __init__(self, base_directory: str = "grading_results"):
        """
        Initialize storage manager.

        Args:
            base_directory: Base directory for all grading data
        """
        self.base_dir = Path(base_directory)
        self.rubrics_dir = self.base_dir / "rubrics"
        self.grades_dir = self.base_dir / "grades"
        self.appeals_dir = self.base_dir / "appeals"
        self.logs_dir = self.base_dir / "logs"

        # Create directory structure
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create all necessary directories."""
        for directory in [self.base_dir, self.rubrics_dir, self.grades_dir, self.appeals_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_rubric_directory(self, question_id: str) -> Path:
        """Get directory for a question's rubrics."""
        rubric_dir = self.rubrics_dir / question_id
        rubric_dir.mkdir(parents=True, exist_ok=True)
        return rubric_dir

    def get_grade_directory(self, question_id: str) -> Path:
        """Get directory for a question's grades."""
        grade_dir = self.grades_dir / question_id
        grade_dir.mkdir(parents=True, exist_ok=True)
        return grade_dir

    def get_appeal_directory(self, question_id: str) -> Path:
        """Get directory for a question's appeals."""
        appeal_dir = self.appeals_dir / question_id
        appeal_dir.mkdir(parents=True, exist_ok=True)
        return appeal_dir

    # Rubric storage methods

    def save_rubric(self, rubric: Rubric) -> Path:
        """
        Save a rubric to disk.

        File: {question_id}/rubric_v{version}.json

        Args:
            rubric: Rubric to save

        Returns:
            Path where rubric was saved
        """
        rubric_dir = self.get_rubric_directory(rubric.question_id)
        file_path = rubric_dir / f"rubric_v{rubric.version}.json"

        with open(file_path, "w") as f:
            f.write(rubric.json(indent=2))

        return file_path

    def load_rubric(self, question_id: str, version: int = 1) -> Optional[Rubric]:
        """
        Load a rubric from disk.

        Args:
            question_id: Question ID
            version: Rubric version (default: latest)

        Returns:
            Rubric object or None if not found
        """
        rubric_dir = self.get_rubric_directory(question_id)

        if version == -1:  # Special case: load latest version
            rubric_files = sorted(rubric_dir.glob("rubric_v*.json"))
            if not rubric_files:
                return None
            file_path = rubric_files[-1]
        else:
            file_path = rubric_dir / f"rubric_v{version}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return Rubric(**data)

    def list_rubric_versions(self, question_id: str) -> list[int]:
        """List all available versions of a rubric."""
        rubric_dir = self.get_rubric_directory(question_id)
        versions = []

        for file_path in rubric_dir.glob("rubric_v*.json"):
            version_str = file_path.stem.replace("rubric_v", "")
            try:
                versions.append(int(version_str))
            except ValueError:
                pass

        return sorted(versions)

    # Grade storage methods

    def save_grade(self, grade: GradeResult) -> Path:
        """
        Save a grade to disk.

        File: {question_id}/{student_id}_v{version}.json

        Args:
            grade: Grade result to save

        Returns:
            Path where grade was saved
        """
        grade_dir = self.get_grade_directory(grade.question_id)
        file_path = grade_dir / f"{grade.student_id}_v{grade.version}.json"

        with open(file_path, "w") as f:
            f.write(grade.json(indent=2))

        return file_path

    def load_grade(self, question_id: str, student_id: str, version: int = 1) -> Optional[GradeResult]:
        """
        Load a grade from disk.

        Args:
            question_id: Question ID
            student_id: Student ID
            version: Grade version (default: latest)

        Returns:
            Grade result object or None if not found
        """
        grade_dir = self.get_grade_directory(question_id)

        if version == -1:  # Special case: load latest version
            grade_files = sorted(grade_dir.glob(f"{student_id}_v*.json"))
            if not grade_files:
                return None
            file_path = grade_files[-1]
        else:
            file_path = grade_dir / f"{student_id}_v{version}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return GradeResult(**data)

    def list_grade_versions(self, question_id: str, student_id: str) -> list[int]:
        """List all available versions of a student's grade."""
        grade_dir = self.get_grade_directory(question_id)
        versions = []

        for file_path in grade_dir.glob(f"{student_id}_v*.json"):
            version_str = file_path.stem.replace(f"{student_id}_v", "")
            try:
                versions.append(int(version_str))
            except ValueError:
                pass

        return sorted(versions)

    def list_grades_for_question(self, question_id: str) -> list[tuple[str, list[int]]]:
        """
        List all grades for a question.

        Returns:
            List of (student_id, [versions]) tuples
        """
        grade_dir = self.get_grade_directory(question_id)
        grades_by_student = {}

        for file_path in grade_dir.glob("*_v*.json"):
            # Parse filename: {student_id}_v{version}.json
            stem = file_path.stem
            parts = stem.rsplit("_v", 1)
            if len(parts) == 2:
                student_id, version_str = parts
                try:
                    version = int(version_str)
                    if student_id not in grades_by_student:
                        grades_by_student[student_id] = []
                    grades_by_student[student_id].append(version)
                except ValueError:
                    pass

        # Sort versions for each student
        result = []
        for student_id in sorted(grades_by_student.keys()):
            versions = sorted(grades_by_student[student_id])
            result.append((student_id, versions))

        return result

    # Appeal storage methods

    def save_appeal(self, appeal: Appeal) -> Path:
        """
        Save an appeal to disk.

        File: {question_id}/{student_id}_appeal_v{appeal_version}.json

        Args:
            appeal: Appeal to save

        Returns:
            Path where appeal was saved
        """
        appeal_dir = self.get_appeal_directory(appeal.question_id)
        # Extract appeal version from appeal ID (e.g., 'appeal_student_001_q01_v1' -> version 1)
        appeal_version = appeal.id.split("_v")[-1] if "_v" in appeal.id else "1"
        file_path = appeal_dir / f"{appeal.student_id}_appeal_v{appeal_version}.json"

        with open(file_path, "w") as f:
            f.write(appeal.json(indent=2))

        return file_path

    def load_appeal(
        self,
        question_id: str,
        student_id: str,
        appeal_version: int = 1
    ) -> Optional[Appeal]:
        """
        Load an appeal from disk.

        Args:
            question_id: Question ID
            student_id: Student ID
            appeal_version: Appeal version (default: latest)

        Returns:
            Appeal object or None if not found
        """
        appeal_dir = self.get_appeal_directory(question_id)

        if appeal_version == -1:  # Special case: load latest version
            appeal_files = sorted(appeal_dir.glob(f"{student_id}_appeal_v*.json"))
            if not appeal_files:
                return None
            file_path = appeal_files[-1]
        else:
            file_path = appeal_dir / f"{student_id}_appeal_v{appeal_version}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return Appeal(**data)

    def list_appeals_for_student(self, question_id: str, student_id: str) -> list[int]:
        """List all appeal versions for a student's question."""
        appeal_dir = self.get_appeal_directory(question_id)
        versions = []

        for file_path in appeal_dir.glob(f"{student_id}_appeal_v*.json"):
            version_str = file_path.stem.replace(f"{student_id}_appeal_v", "")
            try:
                versions.append(int(version_str))
            except ValueError:
                pass

        return sorted(versions)

    # Log file methods

    def get_log_file(self, log_date: Optional[datetime] = None) -> Path:
        """
        Get log file path for a specific date.

        File: {YYYY-MM-DD}.log

        Args:
            log_date: Date for log file (default: today)

        Returns:
            Path to log file
        """
        if log_date is None:
            log_date = datetime.utcnow()

        date_str = log_date.strftime("%Y-%m-%d")
        return self.logs_dir / f"{date_str}.log"

    def write_log(self, message: str, log_date: Optional[datetime] = None) -> None:
        """
        Write a message to the log file.

        Args:
            message: Message to log
            log_date: Date for log file (default: today)
        """
        log_file = self.get_log_file(log_date)

        with open(log_file, "a") as f:
            timestamp = datetime.utcnow().isoformat()
            f.write(f"[{timestamp}] {message}\n")

    # Information methods

    def get_storage_stats(self) -> dict:
        """
        Get statistics about stored data.

        Returns:
            Dictionary with counts of rubrics, grades, appeals
        """
        rubric_count = sum(1 for _ in self.rubrics_dir.rglob("rubric_v*.json"))
        grade_count = sum(1 for _ in self.grades_dir.rglob("*_v*.json"))
        appeal_count = sum(1 for _ in self.appeals_dir.rglob("*_appeal_v*.json"))

        total_size = sum(
            f.stat().st_size
            for f in self.base_dir.rglob("*")
            if f.is_file()
        ) / (1024 * 1024)  # Convert to MB

        return {
            "rubrics": rubric_count,
            "grades": grade_count,
            "appeals": appeal_count,
            "total_size_mb": round(total_size, 2),
            "base_directory": str(self.base_dir),
        }

    def export_config(self) -> dict:
        """
        Export storage configuration.

        Returns:
            Dictionary describing the storage structure
        """
        return {
            "base_directory": str(self.base_dir),
            "structure": {
                "rubrics": str(self.rubrics_dir),
                "grades": str(self.grades_dir),
                "appeals": str(self.appeals_dir),
                "logs": str(self.logs_dir),
            },
            "naming_conventions": {
                "rubrics": "{question_id}/rubric_v{version}.json",
                "grades": "{question_id}/{student_id}_v{version}.json",
                "appeals": "{question_id}/{student_id}_appeal_v{version}.json",
                "logs": "{YYYY-MM-DD}.log",
            },
        }


if __name__ == "__main__":
    # Example usage
    storage = StorageManager("grading_results")

    print("✓ Storage structure initialized")
    print(storage.export_config())

    print("\nStorage statistics:")
    stats = storage.get_storage_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
