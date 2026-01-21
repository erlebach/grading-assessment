"""Command-line interface for dynamic rubrics grading pipeline.

This CLI is simplified compared to grading_pipeline.cli:
- Always uses in-memory indexes (no --index-dir or --index-backend flags)
- Uses dynamic rubrics from rubrics_dynamic/yaml/
- Implements two-dimensional scoring (keyword + semantic)

"""

import argparse
from pathlib import Path

from grading_dynamic_rubrics.config_loader import get_rubric_path
from grading_dynamic_rubrics.pipeline import (
    grade_question_batch,
    grade_single_student,
    write_results,
)
from grading_dynamic_rubrics.submission_loader import (
    load_all_submissions_for_question,
    load_submission,
)
from grading_pipeline.cli import validate_paths


def grade_question_command(args: argparse.Namespace) -> None:
    """Grade all students for a question using dynamic rubrics.

    Args:
        args: Parsed command-line arguments.

    """
    # Validate paths
    rubrics_config = Path(args.rubrics_config)
    submissions_dir = Path(args.submissions_dir)
    sources_config = Path(args.sources_config)
    output_path = Path(args.output)

    # Ensure output filename matches question_id
    if output_path.is_dir() or (not output_path.suffix and not output_path.exists()):
        output_path = output_path / f"{args.question}_results.json"
    else:
        expected_filename = f"{args.question}_results.json"
        if output_path.name != expected_filename:
            print(
                f"Warning: Output filename '{output_path.name}' does not match question_id '{args.question}'. "
                f"Using '{expected_filename}' instead.",
                flush=True,
            )
            output_path = output_path.parent / expected_filename

    # Clear results directory at the beginning of the run
    results_dir = output_path.parent
    if results_dir.exists() and results_dir.is_dir():
        print(f"Clearing results directory: {results_dir}", flush=True)
        for file_path in results_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                print(f"  Removed: {file_path.name}", flush=True)
    else:
        results_dir.mkdir(parents=True, exist_ok=True)

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

    # Setup logging paths
    log_path = Path(args.log_path)
    log_file_name = args.log_file
    enable_transparent = args.log

    # Set debug mode via environment variable
    if args.debug:
        import os

        os.environ["GRADING_DEBUG"] = "1"
        print(
            "[DEBUG] Debug mode enabled - detailed scoring information will be printed",
            flush=True,
        )

    # Grade batch (always in-memory)
    try:
        results = grade_question_batch(
            question_id=args.question,
            rubric_path=rubric_path,
            submissions=submissions,
            config_path=sources_config,
            execution_mode=args.mode,
            log_path=log_path,
            log_file_name=log_file_name,
            enable_transparent=enable_transparent,
            output_path=output_path,
        )

        # Final write
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
    """Grade a single student using dynamic rubrics.

    Args:
        args: Parsed command-line arguments.

    """
    # Validate paths
    rubrics_config = Path(args.rubrics_config)
    submission_path = Path(args.submission)
    sources_config = Path(args.sources_config)
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

    # Setup logging paths
    log_path = Path(args.log_path)
    log_file_name = args.log_file
    enable_transparent = args.log

    # Set debug mode via environment variable
    if args.debug:
        import os

        os.environ["GRADING_DEBUG"] = "1"
        print(
            "[DEBUG] Debug mode enabled - detailed scoring information will be printed",
            flush=True,
        )

    # Grade single student (always in-memory)
    try:
        result = grade_single_student(
            question_id=question_id,
            rubric_path=rubric_path,
            submission=submission,
            config_path=sources_config,
            log_path=log_path,
            log_file_name=log_file_name,
            enable_transparent=enable_transparent,
        )

        # Write result
        if "error" in result:
            print(f"✗ Grading failed: {result['error']}", flush=True)
        else:
            # Write single result as JSON
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", buffering=1) as f:
                import json

                json.dump(result, f, indent=2)
                f.flush()
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
    """Main CLI entry point for dynamic rubrics grading."""
    parser = argparse.ArgumentParser(
        description="Dynamic Rubrics Grading Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This CLI uses LLM-generated dynamic rubrics with two-dimensional scoring
(keyword + semantic). All indexes are in-memory (no persistence).

Examples:
  # Grade question q01
  python -m grading_dynamic_rubrics.cli grade-question \\
      --question q01 \\
      --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \\
      --submissions-dir grading_dynamic_rubrics/submissions \\
      --sources-config grading_dynamic_rubrics/config/sources.yaml \\
      --output grading_dynamic_rubrics/results/q01_results.json

  # Grade single student
  python -m grading_dynamic_rubrics.cli grade-student \\
      --submission grading_dynamic_rubrics/submissions/student_001_q01.yaml \\
      --rubrics-config grading_dynamic_rubrics/config/rubrics.yaml \\
      --sources-config grading_dynamic_rubrics/config/sources.yaml \\
      --output grading_dynamic_rubrics/results/student_001_q01.json
        """,
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
        "--log-path",
        dest="log_path",
        default="logs",
        help=(
            "Directory where log files are written. If relative (e.g., 'logs'), it is "
            "interpreted relative to the autograder/ directory (default: logs)"
        ),
    )
    grade_question_parser.add_argument(
        "--log-file",
        dest="log_file",
        default="grading.log",
        help="Name of the main log file (default: grading.log)",
    )
    grade_question_parser.add_argument(
        "--log",
        action="store_true",
        default=True,
        help="Enable transparency logging (default: True)",
    )
    grade_question_parser.add_argument(
        "--no-log",
        dest="log",
        action="store_false",
        help="Disable transparency logging",
    )
    grade_question_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (shows detailed scoring information)",
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
        "--output",
        required=True,
        help="Path to output JSON file",
    )
    grade_student_parser.add_argument(
        "--log-path",
        dest="log_path",
        default="logs",
        help=(
            "Directory where log files are written. If relative (e.g., 'logs'), it is "
            "interpreted relative to the autograder/ directory (default: logs)"
        ),
    )
    grade_student_parser.add_argument(
        "--log-file",
        dest="log_file",
        default="grading.log",
        help="Name of the main log file (default: grading.log)",
    )
    grade_student_parser.add_argument(
        "--log",
        action="store_true",
        default=True,
        help="Enable transparency logging (default: True)",
    )
    grade_student_parser.add_argument(
        "--no-log",
        dest="log",
        action="store_false",
        help="Disable transparency logging",
    )
    grade_student_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (shows detailed scoring information)",
    )
    grade_student_parser.set_defaults(func=grade_student_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Refer to ....set_defaults(func=grade_question_command) for more information
    args.func(args)


if __name__ == "__main__":
    main()
