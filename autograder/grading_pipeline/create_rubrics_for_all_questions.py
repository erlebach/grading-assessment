"""Create rubrics for all 10 questions from ten_questions.md.

Creates generic rubrics that work for all questions with two-dimensional scoring.

"""

from pathlib import Path

import yaml


def create_generic_rubric(question_id: str, question_text: str) -> dict:
    """Create a generic rubric for a question.

    Args:
        question_id: Question identifier (e.g., "q03").
        question_text: The question text.

    Returns:
        Rubric dictionary.

    """
    return {
        "question_id": question_id,
        "question_text": question_text,
        "total_points": 10,
        "scoring_weights": {
            "correctness": {"keyword": 0.5, "semantic": 0.5},
            "completeness": {"keyword": 0.5, "semantic": 0.5},
        },
        "semantic_decay": "linear",
        "semantic_top_k": 5,
        "criteria": [
            {
                "criterion_id": "correctness",
                "description": "Answer correctly addresses the question and demonstrates understanding of key concepts",
                "points": 6,
                "evidence_required": True,
                "evaluation_method": "semantic",
            },
            {
                "criterion_id": "completeness",
                "description": "Answer includes all required elements and provides sufficient detail",
                "points": 4,
                "evidence_required": True,
                "evaluation_method": "semantic",
            },
        ],
        "metadata": {
            "course": "Data Mining",
            "assignment": "hw01",
            "version": "1.0",
        },
    }


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


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create rubrics for all questions from ten_questions.md. "
        "Generates generic rubrics with two-dimensional scoring (correctness and completeness).",
        epilog=(
            "Examples:\n"
            "  python create_rubrics_for_all_questions.py\n"
            "  python create_rubrics_for_all_questions.py --start-from 1\n"
            "  python create_rubrics_for_all_questions.py --questions-file custom_questions.md --rubrics-dir custom_rubrics\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--questions-file",
        default="ten_questions.md",
        help="Path to questions markdown file (default: ten_questions.md)",
    )
    parser.add_argument(
        "--rubrics-dir",
        default="rubrics",
        help="Directory to write rubric YAML files (default: rubrics)",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=3,
        help="Start creating rubrics from question number (default: 3, creates q03-q10)",
    )

    args = parser.parse_args()

    # Resolve paths
    base_dir = Path(__file__).parent.parent
    questions_file = base_dir / args.questions_file
    rubrics_dir = base_dir / args.rubrics_dir

    # Validate files
    if not questions_file.exists():
        print(f"Error: Questions file not found: {questions_file}", flush=True)
        return

    rubrics_dir.mkdir(parents=True, exist_ok=True)

    # Parse questions
    print("Parsing questions...", flush=True)
    questions = parse_questions(questions_file)
    print(f"✓ Found {len(questions)} questions", flush=True)

    # Create rubrics for questions starting from start_from
    created = 0
    for question in questions:
        question_num = int(question["question_id"][1:])  # Extract number from "q03"
        if question_num < args.start_from:
            continue

        rubric = create_generic_rubric(
            question["question_id"], question["question_text"]
        )

        rubric_file = rubrics_dir / f"{question['question_id']}.yaml"
        with open(rubric_file, "w") as f:
            yaml.dump(rubric, f, default_flow_style=False, sort_keys=False)

        print(f"✓ Created {rubric_file.name}", flush=True)
        created += 1

    print(f"\n✓ Created {created} rubrics in {rubrics_dir}", flush=True)

    # Update rubric config
    config_file = base_dir / "grading_pipeline" / "config" / "rubrics.yaml"
    if config_file.exists():
        print(f"\nUpdating rubric config: {config_file}", flush=True)
        with open(config_file, "r") as f:
            config = yaml.safe_load(f) or {}

        if "rubrics" not in config:
            config["rubrics"] = {}

        for question in questions:
            question_num = int(question["question_id"][1:])
            if question_num >= args.start_from:
                question_id = question["question_id"]
                if question_id not in config["rubrics"]:
                    config["rubrics"][question_id] = {
                        "path": f"../../rubrics/{question_id}.yaml",
                        "description": f"Question {question_num}: {question['question_text'][:50]}...",
                    }

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"✓ Updated rubric config", flush=True)


if __name__ == "__main__":
    main()
