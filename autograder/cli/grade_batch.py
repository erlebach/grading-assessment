"""Command-line interface for batch grading."""

import argparse
from pathlib import Path

from grader.pipeline import run_grading_pipeline


def main() -> None:
    """Main entry point for batch grading CLI."""
    parser = argparse.ArgumentParser(
        description="Grade student submissions against rubrics"
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Question ID (e.g., q01)",
    )
    parser.add_argument(
        "--submission",
        type=Path,
        help="Path to a single submission file",
    )
    parser.add_argument(
        "--submissions-dir",
        type=Path,
        help="Path to directory containing multiple submissions",
    )
    parser.add_argument(
        "--rubrics-dir",
        type=Path,
        default=Path("rubrics"),
        help="Path to rubrics directory (default: rubrics/)",
    )
    parser.add_argument(
        "--evidence-index",
        type=Path,
        help="Path to evidence index (optional)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (default: stdout)",
    )

    args = parser.parse_args()

    # Determine rubric path
    rubric_path = args.rubrics_dir / f"{args.question}.yaml"
    if not rubric_path.exists():
        print(f"Error: Rubric not found at {rubric_path}")
        return

    # Process single submission or directory
    if args.submission:
        submissions = [args.submission]
    elif args.submissions_dir:
        submissions = list(args.submissions_dir.glob("*.py"))
    else:
        print("Error: Must provide either --submission or --submissions-dir")
        return

    # Grade each submission
    results = []
    for submission_path in submissions:
        result = run_grading_pipeline(
            submission_path=submission_path,
            rubric_path=rubric_path,
            evidence_index_path=args.evidence_index,
        )
        results.append({
            "submission": str(submission_path),
            "result": result,
        })

    # Output results
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
    else:
        import json
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
