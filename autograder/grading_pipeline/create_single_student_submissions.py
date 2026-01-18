"""Create submissions for a single student with 30 questions (10 questions × 3 answers each).

This script reads questions from ten_questions.md and answers from ten_answers.md,
creating 30 submission files (one per question-answer pair).

"""

from pathlib import Path
import yaml
from datetime import datetime

from grading_pipeline.submission_converter import create_self_contained_submission


def parse_questions(questions_file: Path) -> list[dict[str, str]]:
    """Parse questions from ten_questions.md.

    Args:
        questions_file: Path to ten_questions.md.

    Returns:
        List of question dictionaries with question_id and question_text.

    """
    questions = []
    with open(questions_file, "r") as f:
        lines = f.readlines()

    current_question = None
    question_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line starts with a number (question number)
        if line and line[0].isdigit() and "." in line:
            # Save previous question if exists
            if current_question is not None:
                questions.append(
                    {
                        "question_id": f"q{current_question:02d}",
                        "question_text": " ".join(question_text).strip(),
                    }
                )

            # Start new question
            current_question = int(line.split(".")[0])
            question_text = [line]
        else:
            # Continue current question
            if current_question is not None:
                question_text.append(line)

    # Add last question
    if current_question is not None:
        questions.append(
            {
                "question_id": f"q{current_question:02d}",
                "question_text": " ".join(question_text).strip(),
            }
        )

    return questions


def parse_answers(answers_file: Path) -> dict[str, list[str]]:
    """Parse answers from ten_answers.md.

    Args:
        answers_file: Path to ten_answers.md.

    Returns:
        Dictionary mapping question_id to list of [good_answer, less_good_answer, wrong_answer].

    """
    answers_by_question = {}
    with open(answers_file, "r") as f:
        content = f.read()

    # Split by question number
    import re

    question_blocks = re.split(r"(\d+)\.", content)

    for i in range(1, len(question_blocks), 2):
        question_num = int(question_blocks[i])
        question_id = f"q{question_num:02d}"
        block_text = question_blocks[i + 1] if i + 1 < len(question_blocks) else ""

        # Extract three answer types
        good_match = re.search(r"Good answer:\s*(.*?)(?=Less good answer:|$)", block_text, re.DOTALL)
        less_good_match = re.search(
            r"Less good answer:\s*(.*?)(?=Wrong answer:|$)", block_text, re.DOTALL
        )
        wrong_match = re.search(r"Wrong answer:\s*(.*?)(?=\d+\.|$)", block_text, re.DOTALL)

        answers = []
        if good_match:
            answers.append(good_match.group(1).strip())
        if less_good_match:
            answers.append(less_good_match.group(1).strip())
        if wrong_match:
            answers.append(wrong_match.group(1).strip())

        if len(answers) == 3:
            answers_by_question[question_id] = answers
        elif len(answers) > 0:
            # If we have some answers but not all, still use them
            answers_by_question[question_id] = answers

    return answers_by_question


def create_submissions(
    student_id: str,
    questions: list[dict[str, str]],
    answers_by_question: dict[str, list[str]],
    rubrics_config_path: Path,
    output_dir: Path,
) -> None:
    """Create submission files for a single student.

    Args:
        student_id: Student identifier.
        questions: List of question dictionaries.
        answers_by_question: Dictionary mapping question_id to list of answers.
        rubrics_config_path: Path to rubric configuration.
        output_dir: Directory to write submission files.

    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for question in questions:
        question_id = question["question_id"]
        question_text = question["question_text"]

        # Get answers for this question
        answers = answers_by_question.get(question_id, [])

        if not answers:
            print(
                f"⚠ Warning: No answers found for {question_id}, skipping",
                flush=True,
            )
            continue

        # Create one submission per answer (good, less good, wrong)
        answer_types = ["good", "less_good", "wrong"]
        for i, answer in enumerate(answers):
            if i >= len(answer_types):
                answer_type = f"answer_{i+1}"
            else:
                answer_type = answer_types[i]

            try:
                submission = create_self_contained_submission(
                    student_id=student_id,
                    question_id=question_id,
                    answer=answer,
                    rubrics_config_path=rubrics_config_path,
                )

                # Override question_text with the parsed one (more accurate)
                submission["question_text"] = question_text

                # Add answer type to metadata
                submission["metadata"]["answer_type"] = answer_type

                # Write submission file
                output_file = (
                    output_dir / f"{student_id}_{question_id}_{answer_type}.yaml"
                )
                with open(output_file, "w") as f:
                    yaml.dump(submission, f, default_flow_style=False, sort_keys=False)

                print(
                    f"✓ Created {output_file.name} ({answer_type} answer)",
                    flush=True,
                )

            except Exception as e:
                print(
                    f"✗ Error creating submission for {question_id} ({answer_type}): {e}",
                    flush=True,
                )


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create submissions for single student with 30 questions"
    )
    parser.add_argument(
        "--student-id",
        default="student_001",
        help="Student identifier (default: student_001)",
    )
    parser.add_argument(
        "--questions-file",
        default="ten_questions.md",
        help="Path to ten_questions.md (default: ten_questions.md)",
    )
    parser.add_argument(
        "--answers-file",
        default="ten_answers.md",
        help="Path to ten_answers.md (default: ten_answers.md)",
    )
    parser.add_argument(
        "--rubrics-config",
        default="grading_pipeline/config/rubrics.yaml",
        help="Path to rubric configuration",
    )
    parser.add_argument(
        "--output-dir",
        default="grading_pipeline/submissions",
        help="Output directory for submission files",
    )

    args = parser.parse_args()

    # Resolve paths
    base_dir = Path(__file__).parent.parent
    questions_file = base_dir / args.questions_file
    answers_file = base_dir / args.answers_file
    rubrics_config = base_dir / args.rubrics_config
    output_dir = base_dir / args.output_dir

    # Validate files
    if not questions_file.exists():
        print(f"Error: Questions file not found: {questions_file}", flush=True)
        return

    if not answers_file.exists():
        print(f"Error: Answers file not found: {answers_file}", flush=True)
        return

    if not rubrics_config.exists():
        print(f"Error: Rubrics config not found: {rubrics_config}", flush=True)
        return

    # Parse questions and answers
    print("Parsing questions...", flush=True)
    questions = parse_questions(questions_file)
    print(f"✓ Found {len(questions)} questions", flush=True)

    print("Parsing answers...", flush=True)
    answers_by_question = parse_answers(answers_file)
    print(
        f"✓ Found answers for {len(answers_by_question)} questions",
        flush=True,
    )

    # Create submissions
    print(f"\nCreating submissions for {args.student_id}...", flush=True)
    create_submissions(
        student_id=args.student_id,
        questions=questions,
        answers_by_question=answers_by_question,
        rubrics_config_path=rubrics_config,
        output_dir=output_dir,
    )

    print(f"\n✓ Done! Submissions created in {output_dir}", flush=True)


if __name__ == "__main__":
    main()
