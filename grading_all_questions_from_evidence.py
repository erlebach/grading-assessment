#!/usr/bin/env python3
"""Batch grading script for all questions using preprocessed evidence.

Scans submission folder, finds all unique questions, and grades each one
across all answer types (good, less_good, wrong).

Usage:
    python grading_all_questions_from_evidence.py \
        --submission_folder_path grading_dynamic_rubrics/submissions \
        --output_dir output

Output:
    Creates output files: q01_good_output.json, q01_less_good_output.json, etc.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def extract_questions_from_submissions(submission_folder: Path) -> set[str]:
    """Extract unique question IDs from submission files.

    Args:
        submission_folder: Path to submissions folder.

    Returns:
        Set of question IDs (e.g., {'q01', 'q02', ...}).
    """
    if not submission_folder.exists():
        raise FileNotFoundError(f"Submission folder not found: {submission_folder}")

    questions = set()
    pattern = re.compile(r"student_\d+_([qQ]\d{2})_[a-z_]+\.yaml")

    for file in submission_folder.glob("*.yaml"):
        match = pattern.match(file.name)
        if match:
            questions.add(match.group(1).lower())

    return sorted(questions)


def grade_all_questions(
    submission_folder: Path,
    output_dir: Path,
    student_id: str = "student_001",
    verbose: bool = False,
    include_question: bool = True,
    include_criterion_description: bool = True,
    save_prompts: bool = False,
) -> dict:
    """Grade all questions across all answer types using subprocess.

    Args:
        submission_folder: Path to submissions folder.
        output_dir: Path to output directory.
        student_id: Student ID to grade (default: student_001).
        verbose: Print verbose output.
        include_question: Include question text in LLM prompt.
        include_criterion_description: Include criterion description in prompt.
        save_prompts: Save full LLM prompts to JSON files for analysis.

    Returns:
        Summary dictionary with results.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all questions
    questions = extract_questions_from_submissions(submission_folder)
    if not questions:
        raise ValueError(f"No questions found in {submission_folder}")

    if verbose:
        print(f"Found {len(questions)} questions: {', '.join(questions)}", file=sys.stderr)

    answer_types = ["good", "less_good", "wrong"]
    summary = {
        "timestamp": datetime.now().isoformat(),
        "student_id": student_id,
        "questions_processed": 0,
        "total_attempts": 0,
        "successful": 0,
        "failed": 0,
        "results": {},
    }

    for question_id in questions:
        if verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Processing: {question_id}", file=sys.stderr)
            print('='*60, file=sys.stderr)

        summary["results"][question_id] = {}

        # Process each answer type
        for answer_type in answer_types:
            summary["total_attempts"] += 1
            output_key = f"{question_id}_{answer_type}"
            output_file = output_dir / f"{output_key}_output.json"

            try:
                if verbose:
                    print(f"  Grading {answer_type} answer...", file=sys.stderr)

                # Call grade_from_evidence via subprocess
                cmd = [
                    sys.executable,
                    "-m",
                    "grading_dynamic_rubrics.grade_from_evidence",
                    "--question", question_id,
                    "--student", student_id,
                    "--answer_type", answer_type,
                    "--output", str(output_file),
                    "--include_question", str(include_question),
                    "--include_criterion_description", str(include_criterion_description),
                    "--save_prompts", str(save_prompts),
                    "--verbose",
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout
                    raise RuntimeError(f"Grading failed: {error_msg}")

                # Load the output file to extract score information
                if output_file.exists():
                    with open(output_file) as f:
                        result_data = json.load(f)

                    summary["results"][question_id][answer_type] = {
                        "status": "success",
                        "output_file": str(output_file),
                        "total_score": result_data.get("total_score"),
                        "max_score": result_data.get("max_score"),
                    }
                    summary["successful"] += 1

                    if verbose:
                        print(
                            f"    ✓ {answer_type}: Score {result_data.get('total_score')}/{result_data.get('max_score')}",
                            file=sys.stderr,
                        )
                else:
                    raise RuntimeError(f"Output file not created: {output_file}")

            except subprocess.TimeoutExpired:
                error_msg = f"Timeout after 300 seconds"
                print(f"  ✗ {answer_type}: {error_msg}", file=sys.stderr)
                summary["results"][question_id][answer_type] = {
                    "status": "failed",
                    "error": error_msg,
                }
                summary["failed"] += 1
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                print(f"  ✗ {answer_type}: {error_msg}", file=sys.stderr)
                summary["results"][question_id][answer_type] = {
                    "status": "failed",
                    "error": error_msg,
                }
                summary["failed"] += 1

        summary["questions_processed"] += 1

    return summary


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch grade all questions using preprocessed evidence",
        epilog="""
Examples:
  python grading_all_questions_from_evidence.py \\
      --submission_folder_path grading_dynamic_rubrics/submissions

  python grading_all_questions_from_evidence.py \\
      --submission_folder_path grading_dynamic_rubrics/submissions \\
      --output_dir my_results \\
      --student_id student_001 \\
      --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--submission_folder_path",
        type=Path,
        default=Path("grading_dynamic_rubrics/submissions"),
        help="Path to submissions folder (default: grading_dynamic_rubrics/submissions)",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("output"),
        help="Output directory for results (default: output)",
    )
    parser.add_argument(
        "--student_id",
        default="student_001",
        help="Student ID to grade (default: student_001)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )
    parser.add_argument(
        "--include_question",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        default=True,
        help="Include question text in LLM prompt (default: True)",
    )
    parser.add_argument(
        "--include_criterion_description",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        default=True,
        help="Include criterion description in LLM prompt (default: True)",
    )
    parser.add_argument(
        "--save_prompts",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        default=False,
        help="Save full LLM prompts to JSON files for analysis (default: False)",
    )

    args = parser.parse_args()

    try:
        # Run batch grading
        summary = grade_all_questions(
            submission_folder=args.submission_folder_path,
            output_dir=args.output_dir,
            student_id=args.student_id,
            verbose=args.verbose,
            include_question=args.include_question,
            include_criterion_description=args.include_criterion_description,
            save_prompts=args.save_prompts,
        )

        # Save summary report
        summary_file = args.output_dir / "grading_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # Print summary
        print(f"\n{'='*60}", file=sys.stderr)
        print("BATCH GRADING SUMMARY", file=sys.stderr)
        print('='*60, file=sys.stderr)
        print(f"Timestamp: {summary['timestamp']}", file=sys.stderr)
        print(f"Student: {summary['student_id']}", file=sys.stderr)
        print(f"Questions Processed: {summary['questions_processed']}", file=sys.stderr)
        print(f"Total Attempts: {summary['total_attempts']}", file=sys.stderr)
        print(f"Successful: {summary['successful']}", file=sys.stderr)
        print(f"Failed: {summary['failed']}", file=sys.stderr)
        print(f"Output Directory: {args.output_dir}", file=sys.stderr)
        print(f"Summary File: {summary_file}", file=sys.stderr)
        print('='*60, file=sys.stderr)

        return 0 if summary["failed"] == 0 else 1

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
