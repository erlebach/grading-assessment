"""Create dynamic rubrics for questions using LLM generation.

Generates rubrics dynamically using an LLM with source file context,
configurable prompts, and output in both JSON and YAML formats.

"""

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from config.llm_config import configure_llm, load_env_config
from grading_pipeline.index_builder import _extract_text_from_pdf
from grading_pipeline.rubric_schema import RubricJsonResponse


def load_prompt_template(template_path: Path) -> str:
    """Load prompt template from file.

    Args:
        template_path: Path to the prompt template file.

    Returns:
        Template content as string.

    Raises:
        FileNotFoundError: If template file doesn't exist.
        ValueError: If template is missing required placeholders.

    """
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Validate placeholders
    required_placeholders = ["{QUESTION_TEXT}", "{SOURCE_FILE_CONTENT}"]
    for placeholder in required_placeholders:
        if placeholder not in template:
            raise ValueError(f"Template missing required placeholder: {placeholder}")

    return template


def load_source_file(source_path: Path) -> str:
    """Load source file content (text, markdown, or PDF).

    Args:
        source_path: Path to the source file.

    Returns:
        File content as string.

    Raises:
        FileNotFoundError: If source file doesn't exist.
        ValueError: If file type is not supported.

    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    suffix = source_path.suffix.lower()

    if suffix == ".pdf":
        return _extract_text_from_pdf(source_path)
    elif suffix in (".txt", ".md", ".markdown"):
        with open(source_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(
            f"Unsupported file type: {suffix}. " "Supported: .pdf, .txt, .md, .markdown"
        )


def format_prompt(template: str, question_text: str, source_content: str) -> str:
    """Format prompt template with question and source content.

    Args:
        template: Prompt template with placeholders.
        question_text: Question text to insert.
        source_content: Source file content to insert.

    Returns:
        Formatted prompt string.

    """
    return template.replace("{QUESTION_TEXT}", question_text).replace(
        "{SOURCE_FILE_CONTENT}", source_content
    )


def extract_json_from_response(response_text: str) -> str:
    """Extract JSON from LLM response text.

    Handles cases where LLM includes markdown code blocks or extra text.

    Args:
        response_text: Raw LLM response text.

    Returns:
        Extracted JSON string.

    Raises:
        ValueError: If no JSON found in response.

    """
    # Try to find JSON in markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Try to find JSON object directly (greedy match to get full object)
    # Find the first { and match until balanced braces
    brace_count = 0
    start_idx = response_text.find("{")
    if start_idx == -1:
        raise ValueError("No JSON found in LLM response")

    for i in range(start_idx, len(response_text)):
        if response_text[i] == "{":
            brace_count += 1
        elif response_text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                return response_text[start_idx : i + 1]

    raise ValueError("No JSON found in LLM response")


def generate_rubric_with_llm(
    prompt: str,
    llm: Any,
    max_retries: int = 3,
    verbose: bool = False,
) -> dict:
    """Generate rubric JSON with validation and retry logic.

    Args:
        prompt: Formatted prompt for LLM.
        llm: LLM instance to use.
        max_retries: Maximum number of retry attempts.
        verbose: Enable verbose output.

    Returns:
        Validated rubric dictionary.

    Raises:
        ValueError: If generation fails after max_retries.

    """
    for attempt in range(max_retries):
        try:
            if verbose:
                print(f"  LLM call attempt {attempt + 1}/{max_retries}...", flush=True)

            response = llm.complete(prompt)
            json_text = extract_json_from_response(response.text)
            rubric_data = json.loads(json_text)

            # Validate with Pydantic
            validated = RubricJsonResponse.model_validate(rubric_data)
            return validated.model_dump()

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            if attempt < max_retries - 1:
                if verbose:
                    print(f"  Attempt {attempt + 1} failed: {e}", flush=True)
                # Add feedback to prompt for next attempt
                error_msg = str(e)
                prompt += (
                    f"\n\nPrevious attempt failed validation: {error_msg}\n"
                    "Please ensure the JSON structure is correct and points sum to 10."
                )
            else:
                response_preview = (
                    response.text[:500] if "response" in locals() else "No response"
                )
                raise ValueError(
                    f"Failed to generate valid rubric after {max_retries} attempts.\n"
                    f"Last error: {str(e)}\n"
                    f"LLM response (last attempt): {response_preview}..."
                ) from e

    raise ValueError("Unexpected error in retry loop")


def slugify(text: str) -> str:
    """Convert text to a slug suitable for criterion_id.

    Args:
        text: Text to slugify.

    Returns:
        Slugified string.

    """
    # Convert to lowercase and replace spaces/special chars with underscores
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug.strip("_")


def convert_json_to_rubric_structure(
    json_rubric: dict, question_id: str, question_text: str
) -> dict:
    """Convert LLM JSON to grading pipeline rubric structure.

    Args:
        json_rubric: Validated JSON rubric from LLM.
        question_id: Question identifier (e.g., "q03").
        question_text: The question text.

    Returns:
        Full rubric dict matching existing YAML structure.

    """
    criteria = []
    for dimension in json_rubric["dimensions"]:
        criterion_id = slugify(dimension["title"])
        criteria.append(
            {
                "criterion_id": criterion_id,
                "description": dimension["description"],
                "points": dimension["points"],
                "evidence_required": True,
                "evaluation_method": "semantic",
            }
        )

    # Calculate scoring weights (equal for all criteria)
    scoring_weights = {}
    for criterion in criteria:
        scoring_weights[criterion["criterion_id"]] = {
            "keyword": 0.5,
            "semantic": 0.5,
        }

    return {
        "question_id": question_id,
        "question_text": question_text,
        "total_points": json_rubric["total_points"],
        "scoring_weights": scoring_weights,
        "semantic_decay": "linear",
        "semantic_top_k": 5,
        "criteria": criteria,
        "metadata": {
            "course": "Data Mining",
            "assignment": "hw01",
            "version": "1.0",
            "generated_by": "llm",
        },
    }


def save_rubric_dual_format(
    rubric_dict: dict,
    rubric_json: dict,
    question_id: str,
    rubrics_dir: Path,
) -> None:
    """Save rubric in separate raw and converted JSON files, plus YAML format.

    Creates four files:
    - {question_id}_raw.json: Raw LLM output (for human review)
    - {question_id}_converted.json: Converted rubric structure (for grading)
    - {question_id}_title_description_converted.json: Criterion titles and descriptions (for postprocessing)
    - {question_id}.yaml: YAML format (for pipeline compatibility)

    Args:
        rubric_dict: Converted rubric dictionary for YAML and converted JSON.
        rubric_json: Original JSON from LLM (raw output).
        question_id: Question identifier.
        rubrics_dir: Base directory for rubrics.

    """
    # Create subdirectories
    json_dir = rubrics_dir / "json"
    yaml_dir = rubrics_dir / "yaml"
    json_dir.mkdir(parents=True, exist_ok=True)
    yaml_dir.mkdir(parents=True, exist_ok=True)

    # Save raw JSON (LLM output only)
    raw_json_file = json_dir / f"{question_id}_raw.json"
    with open(raw_json_file, "w", encoding="utf-8") as f:
        json.dump(rubric_json, f, indent=2, ensure_ascii=False)
        f.flush()  # Ensure immediate write to disk

    # Save converted JSON (grading structure only)
    converted_json_file = json_dir / f"{question_id}_converted.json"
    with open(converted_json_file, "w", encoding="utf-8") as f:
        json.dump(rubric_dict, f, indent=2, ensure_ascii=False)
        f.flush()  # Ensure immediate write to disk

    # Save title_description JSON (criterion titles and descriptions)
    # Extract original titles and descriptions from rubric_json and match with criterion_ids
    title_description_data = {
        "question_id": question_id,
        "criterion_titles": [
            {
                "criterion_id": criterion["criterion_id"],
                "title": dimension["title"],
                "description": dimension["description"],
            }
            for criterion, dimension in zip(
                rubric_dict["criteria"], rubric_json.get("dimensions", [])
            )
        ],
    }
    title_description_json_file = (
        json_dir / f"{question_id}_title_description_converted.json"
    )
    with open(title_description_json_file, "w", encoding="utf-8") as f:
        json.dump(title_description_data, f, indent=2, ensure_ascii=False)
        f.flush()  # Ensure immediate write to disk

    # Save YAML version (for pipeline compatibility)
    yaml_file = yaml_dir / f"{question_id}.yaml"
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(rubric_dict, f, default_flow_style=False, sort_keys=False)
        f.flush()  # Ensure immediate write to disk


def parse_questions(questions_file: Path) -> list[dict[str, str]]:
    """Parse questions from ten_questions.md.

    Args:
        questions_file: Path to ten_questions.md.

    Returns:
        List of question dictionaries with question_id and question_text.

    """
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
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
    parser = argparse.ArgumentParser(
        description=(
            "Create dynamic rubrics for questions using LLM generation. "
            "Generates rubrics with source file context and outputs in both "
            "JSON and YAML formats."
        ),
        epilog=(
            "Examples:\n"
            "  python -m grading_pipeline.create_dynamic_rubrics_for_each_question \\\n"
            "    --source-file grading_pipeline/sources/slides.pdf \\\n"
            "    --questions-file ten_questions.md\n"
            "\n"
            "  python -m grading_pipeline.create_dynamic_rubrics_for_each_question \\\n"
            "    --source-file sources/textbook.pdf \\\n"
            "    --prompt-template custom_template.txt \\\n"
            "    --rubrics-dir custom_rubrics \\\n"
            "    --start-from 1\n"
            "\n"
            "  python -m grading_pipeline.create_dynamic_rubrics_for_each_question \\\n"
            "    --source-file sources/slides.pdf \\\n"
            "    --dry-run --verbose\n"
            "\n"
            "Output Structure:\n"
            "  Rubrics are saved in four files:\n"
            "    - Raw JSON: <rubrics-dir>/json/<question_id>_raw.json (raw LLM output)\n"
            "    - Converted JSON: <rubrics-dir>/json/<question_id>_converted.json (grading structure)\n"
            "    - Title Description JSON: <rubrics-dir>/json/<question_id>_title_description_converted.json (criterion titles and descriptions)\n"
            "    - YAML: <rubrics-dir>/yaml/<question_id>.yaml (pipeline format)\n"
            "\n"
            "  Note: Output directories are emptied before creating new rubrics.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--source-file",
        required=True,
        type=Path,
        help="Path to source file (text, markdown, or PDF) to include in prompt context",
    )
    parser.add_argument(
        "--questions-file",
        default="ten_questions.md",
        type=Path,
        help="Path to questions markdown file (default: ten_questions.md)",
    )

    # Optional arguments
    parser.add_argument(
        "--prompt-template",
        type=Path,
        default=None,
        help=(
            "Path to prompt template file "
            "(default: rubric_generator_template.txt in script directory)"
        ),
    )
    parser.add_argument(
        "--rubrics-dir",
        default="rubrics_dynamic",
        type=Path,
        help="Directory to write rubric files (default: rubrics_dynamic)",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help=(
            "Start creating rubrics from question number "
            "(default: 1, creates q01-q10)"
        ),
    )
    parser.add_argument(
        "--llm-provider",
        choices=["openai", "anthropic", "gemini", "ollama"],
        default=None,
        help="LLM provider (default: from config)",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model name (default: from config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without calling LLM",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed logging",
    )

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent

    source_file = args.source_file
    if not source_file.is_absolute():
        source_file = base_dir / source_file

    questions_file = args.questions_file
    if not questions_file.is_absolute():
        questions_file = base_dir / questions_file

    prompt_template_path = args.prompt_template
    if prompt_template_path is None:
        prompt_template_path = script_dir / "rubric_generator_template.txt"
    elif not prompt_template_path.is_absolute():
        prompt_template_path = base_dir / prompt_template_path

    rubrics_dir = args.rubrics_dir
    if not rubrics_dir.is_absolute():
        rubrics_dir = base_dir / rubrics_dir

    # Show where files will be written
    json_dir = rubrics_dir / "json"
    yaml_dir = rubrics_dir / "yaml"
    print(f"Output directory: {rubrics_dir}", flush=True)
    print(f"  JSON files: {json_dir}", flush=True)
    print(f"  YAML files: {yaml_dir}", flush=True)

    # Empty output directories before creating new data (without deleting the folders)
    if json_dir.exists() and not args.dry_run:
        if args.verbose:
            print(f"Emptying JSON directory: {json_dir}", flush=True)
        for file_path in json_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
    if yaml_dir.exists() and not args.dry_run:
        if args.verbose:
            print(f"Emptying YAML directory: {yaml_dir}", flush=True)
        for file_path in yaml_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)

    # Validate files
    if not source_file.exists():
        print(f"Error: Source file not found: {source_file}", flush=True)
        return

    if not questions_file.exists():
        print(f"Error: Questions file not found: {questions_file}", flush=True)
        return

    if not prompt_template_path.exists():
        print(
            f"Error: Prompt template not found: {prompt_template_path}",
            flush=True,
        )
        return

    # Load prompt template
    if args.verbose:
        print(f"Loading prompt template: {prompt_template_path}", flush=True)
    try:
        template = load_prompt_template(prompt_template_path)
    except Exception as e:
        print(f"Error loading prompt template: {e}", flush=True)
        return

    # Load source file
    if args.verbose:
        print(f"Loading source file: {source_file}", flush=True)
    try:
        source_content = load_source_file(source_file)
        if args.verbose:
            print(f"  Loaded {len(source_content)} characters", flush=True)
    except Exception as e:
        print(f"Error loading source file: {e}", flush=True)
        return

    # Configure LLM
    config = load_env_config()
    llm_provider = args.llm_provider or config["lmql_backend"]
    llm_model = args.llm_model or config.get("lmql_model", "gpt-oss:20b")

    if args.verbose:
        print(
            f"Configuring LLM: provider={llm_provider}, model={llm_model}",
            flush=True,
        )

    try:
        llm = configure_llm(llm_provider, llm_model)
    except Exception as e:
        print(f"Error configuring LLM: {e}", flush=True)
        return

    # Parse questions
    if args.verbose:
        print(f"Parsing questions from: {questions_file}", flush=True)
    questions = parse_questions(questions_file)
    print(f"✓ Found {len(questions)} questions", flush=True)

    # Create rubrics for questions starting from start_from
    created = 0
    for question in questions:
        question_num = int(question["question_id"][1:])  # Extract from "q03"
        if question_num < args.start_from:
            continue

        print(f"\nProcessing {question['question_id']}...", flush=True)

        if args.dry_run:
            print(
                f"  [DRY RUN] Would generate rubric for: {question['question_text'][:50]}...",
                flush=True,
            )
            created += 1
            continue

        # Format prompt
        prompt = format_prompt(template, question["question_text"], source_content)

        # Generate rubric with LLM
        try:
            rubric_json = generate_rubric_with_llm(prompt, llm, verbose=args.verbose)
        except Exception as e:
            print(f"  ✗ Error generating rubric: {e}", flush=True)
            continue

        # Convert to rubric structure
        rubric_dict = convert_json_to_rubric_structure(
            rubric_json, question["question_id"], question["question_text"]
        )

        # Save in dual format
        save_rubric_dual_format(
            rubric_dict, rubric_json, question["question_id"], rubrics_dir
        )

        print(f"  ✓ Created rubric files in {rubrics_dir}", flush=True)
        json_dir = rubrics_dir / "json"
        yaml_dir = rubrics_dir / "yaml"
        question_id = question["question_id"]
        raw_file = json_dir / f"{question_id}_raw.json"
        converted_file = json_dir / f"{question_id}_converted.json"
        title_desc_file = json_dir / f"{question_id}_title_description_converted.json"
        yaml_file = yaml_dir / f"{question_id}.yaml"
        print(f"    - {raw_file}", flush=True)
        print(f"    - {converted_file}", flush=True)
        print(f"    - {title_desc_file}", flush=True)
        print(f"    - {yaml_file}", flush=True)
        created += 1

    print(f"\n✓ Created {created} rubrics in {rubrics_dir}", flush=True)

    # Update rubric config
    config_file = base_dir / "grading_pipeline" / "config" / "rubrics.yaml"
    if config_file.exists() and not args.dry_run:
        print(f"\nUpdating rubric config: {config_file}", flush=True)
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        if "rubrics" not in config:
            config["rubrics"] = {}

        # Compute relative path from config file to rubrics directory
        config_dir = config_file.parent
        rubrics_yaml_dir = rubrics_dir / "yaml"
        try:
            # Get relative path from config_dir to rubrics_yaml_dir
            relative_path = rubrics_yaml_dir.relative_to(config_dir)
        except ValueError:
            # If paths are on different drives or can't be made relative, use absolute
            relative_path = rubrics_yaml_dir

        for question in questions:
            question_num = int(question["question_id"][1:])
            if question_num >= args.start_from:
                question_id = question["question_id"]
                if question_id not in config["rubrics"]:
                    rubric_path = relative_path / f"{question_id}.yaml"
                    # Convert to forward-slash string for YAML (works on all platforms)
                    path_str = str(rubric_path).replace("\\", "/")
                    config["rubrics"][question_id] = {
                        "path": path_str,
                        "description": (
                            f"Question {question_num}: "
                            f"{question['question_text'][:50]}..."
                        ),
                    }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            f.flush()  # Ensure immediate write to disk

        print("✓ Updated rubric config", flush=True)


if __name__ == "__main__":
    main()
