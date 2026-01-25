#!/usr/bin/env python3
"""CLI script to grade students using preprocessed evidence context.

This script demonstrates how to use the grade_student_with_evidence function
to grade a student answer given:
1. Evidence context from reranking (questions and criteria with evidence)
2. Student submission (answer to the question)

Usage:
    python grade_from_evidence.py --question q02 --student student_001 --answer_type good
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

from grading_dynamic_rubrics.grade_with_evidence import grade_student_with_evidence


def load_evidence_context(question_id: str) -> dict:
    """Load evidence context from reranker results.

    Args:
        question_id: Question ID (e.g., "q02")

    Returns:
        Evidence context dictionary.

    Raises:
        FileNotFoundError: If evidence file not found.
    """
    evidence_path = Path(f"reranker_results/{question_id}_results.json")
    if not evidence_path.exists():
        raise FileNotFoundError(f"Evidence file not found: {evidence_path}")

    with open(evidence_path) as f:
        data = json.load(f)

    # Return the evidence context from the first student's data
    # (evidence is student-agnostic, just carries criteria and evidence)
    if "students" in data and len(data["students"]) > 0:
        return data["students"][0]
    else:
        return {
            "question_id": question_id,
            "grading_context": [],
        }


def load_student_submission(student_id: str, question_id: str, answer_type: str) -> dict:
    """Load student submission from YAML file.

    Args:
        student_id: Student ID (e.g., "student_001")
        question_id: Question ID (e.g., "q02")
        answer_type: Answer type (e.g., "good", "less_good", "wrong")

    Returns:
        Student submission dictionary.

    Raises:
        FileNotFoundError: If submission file not found.
    """
    submission_path = (
        Path("grading_dynamic_rubrics/submissions") /
        f"{student_id}_{question_id}_{answer_type}.yaml"
    )
    if not submission_path.exists():
        raise FileNotFoundError(f"Submission file not found: {submission_path}")

    with open(submission_path) as f:
        submission = yaml.safe_load(f)

    return submission


def main():
    """Main entry point for the grading script."""
    parser = argparse.ArgumentParser(
        description="Grade a student using LLM with preprocessed evidence"
    )
    parser.add_argument("--question", default="q02", help="Question ID (e.g., q02)")
    parser.add_argument(
        "--student", default="student_001", help="Student ID (e.g., student_001)"
    )
    parser.add_argument(
        "--answer_type",
        default="good",
        choices=["good", "less_good", "wrong"],
        help="Answer type to grade",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (default: results/{student}_{question}_{answer_type}_grades.json)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed output"
    )

    args = parser.parse_args()

    try:
        # Load evidence context
        if args.verbose:
            print(f"Loading evidence for {args.question}...", file=sys.stderr)
        evidence_context = load_evidence_context(args.question)

        # Load student submission
        if args.verbose:
            print(
                f"Loading submission for {args.student} {args.question} ({args.answer_type})...",
                file=sys.stderr,
            )
        submission = load_student_submission(
            args.student, args.question, args.answer_type
        )

        # Grade the student
        if args.verbose:
            print("Grading student (this may take a moment)...", file=sys.stderr)

        result = grade_student_with_evidence(
            student_id=submission.get("student_id", args.student),
            student_answer=submission.get("answer", ""),
            question_text=submission.get("question_text", ""),
            rubric={},  # Not used in this approach
            evidence_context=evidence_context,
            answer_type=args.answer_type,
        )

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            # Default to results/ directory
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            output_path = (
                results_dir /
                f"{args.student}_{args.question}_{args.answer_type}_grades.json"
            )

        # Output results
        if args.verbose:
            print("\n" + "=" * 80, file=sys.stderr)
            print("GRADING RESULTS", file=sys.stderr)
            print("=" * 80, file=sys.stderr)

        result_json = json.dumps(result, indent=2)

        # Always save to file (either specified or default)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result_json)
        if args.verbose:
            print(f"Results saved to {output_path}", file=sys.stderr)
            print(f"\nIncluded in output:", file=sys.stderr)
            print(f"  - question_text: ✓", file=sys.stderr)
            print(f"  - student_answer: ✓", file=sys.stderr)
            print(f"  - total_score: {result['total_score']}/{result['max_score']}", file=sys.stderr)
        else:
            print(result_json)

        # Print summary to stderr if verbose
        if args.verbose:
            print("\nSUMMARY:", file=sys.stderr)
            print(f"  Student: {result['student_id']}", file=sys.stderr)
            print(f"  Question: {result['question_id']}", file=sys.stderr)
            print(f"  Answer Type: {result['answer_type']}", file=sys.stderr)
            print(f"  Total Score: {result['total_score']}/{result['max_score']}", file=sys.stderr)
            print(f"  Criteria Graded: {len(result['criterion_results'])}", file=sys.stderr)
            for crit in result["criterion_results"]:
                print(
                    f"    - {crit['criterion_id']}: "
                    f"{crit['llm_score']}/10 (weighted: {crit['weighted_score']:.1f})",
                    file=sys.stderr,
                )

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during grading: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
