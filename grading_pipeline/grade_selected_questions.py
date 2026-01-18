"""Grade selected questions for a student.

This script allows you to select specific questions to grade from the available
submissions. It filters submissions and runs the grading pipeline for only
the selected questions.

Usage:
    python -m grading_pipeline.grade_selected_questions \
        --student-id student_001 \
        --questions q01 q03 q06 \
        --submissions-dir grading_pipeline/submissions \
        --output-dir grading_pipeline/results

"""

import argparse
import subprocess
import sys
from pathlib import Path


def find_submissions_for_questions(
    submissions_dir: Path, student_id: str, question_ids: list[str]
) -> dict[str, list[Path]]:
    """Find submission files for specified questions.

    Args:
        submissions_dir: Directory containing submission files.
        student_id: Student identifier.
        question_ids: List of question IDs to find (e.g., ["q01", "q03", "q06"]).

    Returns:
        Dictionary mapping question_id to list of submission file paths.

    """
    submissions_by_question = {qid: [] for qid in question_ids}

    # Find all submission files for this student
    pattern = f"{student_id}_*.yaml"
    all_files = list(submissions_dir.glob(pattern))

    for file_path in all_files:
        # Parse filename: student_001_q01_good.yaml
        parts = file_path.stem.split("_")
        if len(parts) >= 3:
            file_question_id = parts[1]  # q01
            if file_question_id in question_ids:
                submissions_by_question[file_question_id].append(file_path)

    return submissions_by_question


def grade_question(
    question_id: str,
    submissions: list[Path],
    rubrics_config: Path,
    sources_config: Path,
    index_dir: Path,
    output_dir: Path,
    log_dir: Path | None = None,
) -> bool:
    """Grade a single question using the CLI.

    Args:
        question_id: Question identifier.
        submissions: List of submission file paths for this question.
        rubrics_config: Path to rubric configuration.
        sources_config: Path to sources configuration.
        index_dir: Directory for ChromaDB indexes.
        output_dir: Directory for output results.
        log_dir: Optional directory for log files.

    Returns:
        True if grading succeeded, False otherwise.

    """
    if not submissions:
        print(f"⚠ No submissions found for {question_id}, skipping", flush=True)
        return False

    # Create temporary directory with only submissions for this question
    import tempfile
    import shutil

    temp_submissions_dir = Path(tempfile.mkdtemp(prefix=f"submissions_{question_id}_"))
    try:
        # Copy submissions to temp directory
        for submission in submissions:
            shutil.copy(submission, temp_submissions_dir / submission.name)

        # Prepare output paths
        output_file = output_dir / f"{question_id}_results.json"
        log_file = None
        if log_dir:
            log_file = log_dir / f"{question_id}_grading.log"

        # Build CLI command
        cmd = [
            sys.executable,
            "-m",
            "grading_pipeline.cli",
            "grade-question",
            "--question",
            question_id,
            "--rubrics-config",
            str(rubrics_config),
            "--submissions-dir",
            str(temp_submissions_dir),
            "--sources-config",
            str(sources_config),
            "--index-dir",
            str(index_dir),
            "--output",
            str(output_file),
            "--mode",
            "sequential",
        ]

        if log_file:
            cmd.extend(["--log", str(log_file)])

        print(f"\n{'='*60}", flush=True)
        print(f"Grading {question_id} ({len(submissions)} submissions)", flush=True)
        print(f"{'='*60}", flush=True)

        # Run grading
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

        if result.returncode == 0:
            print(f"✓ Successfully graded {question_id}", flush=True)
            print(f"  Results: {output_file}", flush=True)
            if log_file:
                print(f"  Log: {log_file}", flush=True)
            return True
        else:
            print(f"✗ Failed to grade {question_id}", flush=True)
            return False

    finally:
        # Clean up temp directory
        if temp_submissions_dir.exists():
            shutil.rmtree(temp_submissions_dir)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Grade selected questions for a student",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Grade questions q01, q03, and q06
  python -m grading_pipeline.grade_selected_questions \\
      --student-id student_001 \\
      --questions q01 q03 q06

  # Grade with custom paths
  python -m grading_pipeline.grade_selected_questions \\
      --student-id student_001 \\
      --questions q01 q03 q06 \\
      --submissions-dir grading_pipeline/submissions \\
      --output-dir grading_pipeline/results \\
      --log-dir grading_pipeline/logs
        """,
    )

    parser.add_argument(
        "--student-id",
        default="student_001",
        help="Student identifier (default: student_001)",
    )
    parser.add_argument(
        "--questions",
        nargs="+",
        required=True,
        help="Question IDs to grade (e.g., q01 q03 q06)",
    )
    parser.add_argument(
        "--submissions-dir",
        default="grading_pipeline/submissions",
        help="Directory containing submission files",
    )
    parser.add_argument(
        "--rubrics-config",
        default="grading_pipeline/config/rubrics.yaml",
        help="Path to rubric configuration",
    )
    parser.add_argument(
        "--sources-config",
        default="grading_pipeline/config/sources.yaml",
        help="Path to sources configuration",
    )
    parser.add_argument(
        "--index-dir",
        default="grading_pipeline/tmp/chroma_db",
        help="Directory for ChromaDB indexes",
    )
    parser.add_argument(
        "--output-dir",
        default="grading_pipeline/results",
        help="Directory for output results",
    )
    parser.add_argument(
        "--log-dir",
        help="Optional directory for log files",
    )

    args = parser.parse_args()

    # Resolve paths
    base_dir = Path(__file__).parent.parent
    submissions_dir = base_dir / args.submissions_dir
    rubrics_config = base_dir / args.rubrics_config
    sources_config = base_dir / args.sources_config
    index_dir = base_dir / args.index_dir
    output_dir = base_dir / args.output_dir
    log_dir = base_dir / args.log_dir if args.log_dir else None

    # Validate paths
    if not submissions_dir.exists():
        print(f"Error: Submissions directory not found: {submissions_dir}", flush=True)
        sys.exit(1)

    if not rubrics_config.exists():
        print(f"Error: Rubrics config not found: {rubrics_config}", flush=True)
        sys.exit(1)

    if not sources_config.exists():
        print(f"Error: Sources config not found: {sources_config}", flush=True)
        sys.exit(1)

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    # Find submissions for selected questions
    print(f"Finding submissions for {args.student_id}...", flush=True)
    submissions_by_question = find_submissions_for_questions(
        submissions_dir, args.student_id, args.questions
    )

    # Show what we found
    total_submissions = 0
    for qid in args.questions:
        count = len(submissions_by_question[qid])
        total_submissions += count
        if count > 0:
            print(f"  {qid}: {count} submission(s) found", flush=True)
        else:
            print(f"  {qid}: ⚠ No submissions found", flush=True)

    if total_submissions == 0:
        print(f"\nError: No submissions found for any of the selected questions", flush=True)
        print(f"  Student ID: {args.student_id}", flush=True)
        print(f"  Questions: {', '.join(args.questions)}", flush=True)
        print(f"  Submissions directory: {submissions_dir}", flush=True)
        sys.exit(1)

    # Grade each question
    print(f"\nGrading {len(args.questions)} question(s) with {total_submissions} total submission(s)...", flush=True)

    results = []
    for question_id in args.questions:
        submissions = submissions_by_question[question_id]
        if submissions:
            success = grade_question(
                question_id=question_id,
                submissions=submissions,
                rubrics_config=rubrics_config,
                sources_config=sources_config,
                index_dir=index_dir,
                output_dir=output_dir,
                log_dir=log_dir,
            )
            results.append((question_id, success))
        else:
            print(f"⚠ Skipping {question_id} (no submissions)", flush=True)
            results.append((question_id, False))

    # Summary
    print(f"\n{'='*60}", flush=True)
    print("Summary", flush=True)
    print(f"{'='*60}", flush=True)

    successful = [qid for qid, success in results if success]
    failed = [qid for qid, success in results if not success]

    if successful:
        print(f"✓ Successfully graded: {', '.join(successful)}", flush=True)
        print(f"  Results in: {output_dir}", flush=True)

    if failed:
        print(f"✗ Failed or skipped: {', '.join(failed)}", flush=True)

    print(f"\nTotal: {len(successful)}/{len(results)} questions graded successfully", flush=True)


if __name__ == "__main__":
    main()
