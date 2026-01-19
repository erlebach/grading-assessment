"""Command-line interface for grading pipeline.

This module provides CLI commands for grading questions and individual students.

"""

import argparse
from pathlib import Path

from grading_pipeline.config_loader import get_rubric_path
from grading_pipeline.pipeline import (
    grade_question_batch,
    grade_single_student,
    write_results,
)
from grading_pipeline.submission_loader import (
    load_all_submissions_for_question,
    load_submission,
)


def validate_paths(
    rubrics_config: Path,
    rubric_path: Path | None = None,
    submissions_dir: Path | None = None,
    submission_path: Path | None = None,
    sources_config: Path | None = None,
) -> None:
    """Validate that required paths exist.

    Args:
        rubrics_config: Path to rubric configuration file.
        rubric_path: Optional rubric file path.
        submissions_dir: Optional submissions directory.
        submission_path: Optional single submission file.
        sources_config: Optional sources configuration file.

    Raises:
        FileNotFoundError: If any required path doesn't exist.
        ValueError: If path validation fails.

    """
    if not rubrics_config.exists():
        raise FileNotFoundError(f"Rubrics config not found: {rubrics_config}")

    if rubric_path and not rubric_path.exists():
        raise FileNotFoundError(f"Rubric file not found: {rubric_path}")

    if submissions_dir and not submissions_dir.exists():
        raise FileNotFoundError(f"Submissions directory not found: {submissions_dir}")

    if submission_path and not submission_path.exists():
        raise FileNotFoundError(f"Submission file not found: {submission_path}")

    if sources_config and not sources_config.exists():
        raise FileNotFoundError(f"Sources config not found: {sources_config}")


def grade_question_command(args: argparse.Namespace) -> None:
    """Grade all students for a question.

    Args:
        args: Parsed command-line arguments.

    """
    # Validate paths
    rubrics_config = Path(args.rubrics_config)
    submissions_dir = Path(args.submissions_dir)
    sources_config = Path(args.sources_config)
    index_dir = Path(args.index_dir)
    output_path = Path(args.output)

    validate_paths(
        rubrics_config=rubrics_config,
        submissions_dir=submissions_dir,
        sources_config=sources_config,
    )

    # Get rubric path from config
    try:
        rubric_path = get_rubric_path(args.question, rubrics_config)
    except ValueError as e:
        print(f"Error: {e}", flush=True)
        return

    # Load all submissions for this question
    try:
        submissions = load_all_submissions_for_question(submissions_dir, args.question)
        print(
            f"Loaded {len(submissions)} submissions for question {args.question}",
            flush=True,
        )
    except Exception as e:
        print(f"Error loading submissions: {e}", flush=True)
        return

    # Setup log file if specified
    log_file = Path(args.log) if args.log else None

    # Grade batch
    try:
        results = grade_question_batch(
            question_id=args.question,
            rubric_path=rubric_path,
            submissions=submissions,
            persist_dir=index_dir,
            config_path=sources_config,
            index_backend=args.index_backend,
            execution_mode=args.mode,
            log_file=log_file,
        )

        # Write results
        write_results(results, args.question, output_path, per_student=False)

        successful = len([r for r in results if "error" not in r])
        failed = len([r for r in results if "error" in r])
        print(
            f"\n✓ Grading complete: {successful} successful, {failed} failed",
            flush=True,
        )
        print(f"  Results written to: {output_path}", flush=True)

    except Exception as e:
        print(f"Error during grading: {e}", flush=True)
        raise


def grade_student_command(args: argparse.Namespace) -> None:
    """Grade a single student.

    Args:
        args: Parsed command-line arguments.

    """
    # Validate paths
    rubrics_config = Path(args.rubrics_config)
    submission_path = Path(args.submission)
    sources_config = Path(args.sources_config)
    index_dir = Path(args.index_dir)
    output_path = Path(args.output)

    validate_paths(
        rubrics_config=rubrics_config,
        submission_path=submission_path,
        sources_config=sources_config,
    )

    # Load submission
    try:
        submission = load_submission(submission_path)
        question_id = submission["question_id"]
        print(
            f"Loaded submission for {submission['student_id']}, question {question_id}",
            flush=True,
        )
    except Exception as e:
        print(f"Error loading submission: {e}", flush=True)
        return

    # Get rubric path from config
    try:
        rubric_path = get_rubric_path(question_id, rubrics_config)
    except ValueError as e:
        print(f"Error: {e}", flush=True)
        return

    # Setup log file if specified
    log_file = Path(args.log) if args.log else None

    # Grade single student
    try:
        result = grade_single_student(
            question_id=question_id,
            rubric_path=rubric_path,
            submission=submission,
            persist_dir=index_dir,
            config_path=sources_config,
            index_backend=args.index_backend,
            log_file=log_file,
        )

        # Write result
        if "error" in result:
            print(f"✗ Grading failed: {result['error']}", flush=True)
        else:
            # Write single result as JSON
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                import json

                json.dump(result, f, indent=2)
            print("✓ Grading complete", flush=True)
            print(
                f"  Score: {result.get('score', 0)}/{result.get('max_score', 0)}",
                flush=True,
            )
            print(f"  Results written to: {output_path}", flush=True)

    except Exception as e:
        print(f"Error during grading: {e}", flush=True)
        raise


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Grading Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Grade question command
    grade_question_parser = subparsers.add_parser(
        "grade-question", help="Grade all students for a question"
    )
    grade_question_parser.add_argument(
        "--question",
        required=True,
        help="Question ID (e.g., q01)",
    )
    grade_question_parser.add_argument(
        "--rubrics-config",
        required=True,
        help="Path to rubric configuration YAML file",
    )
    grade_question_parser.add_argument(
        "--submissions-dir",
        required=True,
        help="Directory containing submission YAML files",
    )
    grade_question_parser.add_argument(
        "--sources-config",
        required=True,
        help="Path to sources configuration YAML file",
    )
    grade_question_parser.add_argument(
        "--index-dir",
        required=True,
        help="Directory for persistent indexes",
    )
    grade_question_parser.add_argument(
        "--index-backend",
        default="chromadb",
        choices=["chromadb", "in-memory"],
        help="Index backend to use (default: chromadb)",
    )
    grade_question_parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSON file",
    )
    grade_question_parser.add_argument(
        "--mode",
        default="sequential",
        choices=["sequential", "batched", "async"],
        help="Execution mode (default: sequential)",
    )
    grade_question_parser.add_argument(
        "--log",
        help="Optional path to log file",
    )
    grade_question_parser.set_defaults(func=grade_question_command)

    # Grade student command
    grade_student_parser = subparsers.add_parser(
        "grade-student", help="Grade a single student"
    )
    grade_student_parser.add_argument(
        "--question",
        help="Question ID (optional, will be read from submission if not provided)",
    )
    grade_student_parser.add_argument(
        "--rubrics-config",
        required=True,
        help="Path to rubric configuration YAML file",
    )
    grade_student_parser.add_argument(
        "--submission",
        required=True,
        help="Path to submission YAML file",
    )
    grade_student_parser.add_argument(
        "--sources-config",
        required=True,
        help="Path to sources configuration YAML file",
    )
    grade_student_parser.add_argument(
        "--index-dir",
        required=True,
        help="Directory for persistent indexes",
    )
    grade_student_parser.add_argument(
        "--index-backend",
        default="chromadb",
        choices=["chromadb", "in-memory"],
        help="Index backend to use (default: chromadb)",
    )
    grade_student_parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSON file",
    )
    grade_student_parser.add_argument(
        "--log",
        help="Optional path to log file",
    )
    grade_student_parser.set_defaults(func=grade_student_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
