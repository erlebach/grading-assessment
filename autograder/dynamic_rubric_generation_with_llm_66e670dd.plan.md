---
name: ""
overview: ""
todos: []
---

---

name: Dynamic Rubric Generation with LLM

overview: Transform the rubric generation script to use LLM-based dynamic rubric creation with configurable prompts, source file context, and dual JSON/YAML output formats.

todos:

  - id: "1"

content: Create prompt template file (rubric_generator_template.txt) with placeholders for question and source file

status: pending

  - id: "2"

content: Add source file loading function using _extract_text_from_pdf from index_builder.py (supports text, markdown, PDF)

status: pending

  - id: "3"

content: Add prompt template loading and formatting functions

status: pending

  - id: "4"

content: Create Pydantic schema (rubric_schema.py) for JSON validation with RubricDimension and RubricJsonResponse models

status: pending

  - id: "5"

content: Add LLM integration function with retry logic (up to 3 attempts) and Pydantic validation

status: pending

  - id: "6"

content: Add JSON to rubric structure conversion function

status: pending

  - id: "7"

content: Add dual format saving function (JSON and YAML subdirectories)

status: pending

  - id: "8"

content: Modify main() function to integrate all components, use module execution format (-m), and default to Ollama gpt-oss:20b

status: pending

  - id: "9"

content: Implement comprehensive CLI argument parsing with argparse including all required and optional arguments

status: pending

  - id: "10"

content: Create detailed --help output with descriptions, examples, and usage notes

status: pending

  - id: "11"

content: Create wrapper script create_dynamics_rubrics.x using module format (python -m gp.create_dynamic_rubrics_for_each_question)

status: pending

  - id: "12"

content: Add argument validation for source file existence, prompt template existence, etc.

status: pending

  - id: "13"

content: Implement --dry-run mode that shows what would be generated without LLM calls

status: pending

  - id: "14"

content: Implement --verbose mode for detailed logging throughout the process

status: pending

  - id: "15"

content: Create comprehensive pytest test suite (test_create_dynamic_rubrics.py) covering all functions, error cases, and integration tests

status: pending  - id: "14"

content: Implement --verbose mode for detailed logging throughout the process

status: pending---

# Dynamic Rubric Generation Implementation Plan

## Overview

Modify `autograder/gp/create_dynamic_rubrics_for_each_question.py` to generate rubrics dynamically using an LLM, with configurable prompts, source file context, and output in both JSON and YAML formats.

## Key Components

### 1. Prompt Template System

- **File**: `autograder/gp/rubric_generator_template.txt`
- Load prompt template from file
- Support placeholders: `{QUESTION_TEXT}` and `{SOURCE_FILE_CONTENT}`
- Template should request JSON output format matching the example structure

### 2. Source File Loading

- Accept `--source-file` argument (path to source file)
- Support text files (.txt, .md) and PDF files (.pdf)
- For PDFs: Use existing PDF loading utilities from `grading_pipeline/index_builder.py`
- Load full file content to attach to prompt

### 3. LLM Integration

- Use existing LLM configuration system (`config/llm_config.py`)
- Call LLM with formatted prompt (question + source file content)
- Request JSON output format
- Handle parsing and validation of JSON response

### 4. JSON to Rubric Structure Conversion

- Parse LLM JSON response with structure:
  ```json
  {
    "dimensions": [
      {
        "title": "Dimension title",
        "points": 3,
        "description": "Full-credit description"
      }
    ],
    "total_points": 10
  }
  ```

- Convert to existing rubric YAML structure:
  - Map dimensions to `criteria` array
  - Generate `criterion_id` from title (slugified)
  - Set `points`, `description`, `evidence_required`, `evaluation_method`
  - Add default `scoring_weights`, `semantic_decay`, `semantic_top_k`
  - Include `metadata` section

### 5. Dual Output Format

- Create subdirectories: `<rubrics_dir>/json/` and `<rubrics_dir>/yaml/`
- Save JSON version in `json/` directory (raw LLM output + converted structure)
- Save YAML version in `yaml/` directory (converted structure for pipeline compatibility)
- Update rubric config to point to YAML files

## Implementation Details

### Modified Functions

#### `load_prompt_template(template_path: Path) -> str`

- Load prompt template from file
- Validate template contains required placeholders

#### `load_source_file(source_path: Path) -> str`

- Load text files directly
- For PDFs: Use `_load_file_source_with_pdf()` logic or PyPDF2/pypdf
- Return file content as string

#### `format_prompt(template: str, question_text: str, source_content: str) -> str`

- Replace `{QUESTION_TEXT}` and `{SOURCE_FILE_CONTENT}` placeholders
- Return formatted prompt string

#### `generate_rubric_with_llm(prompt: str, llm: LLM) -> dict`

- Call LLM with prompt
- Parse JSON response
- Validate structure (2-5 dimensions, total = 10 points)
- Return parsed JSON dict

#### `convert_json_to_rubric_structure(json_rubric: dict, question_id: str, question_text: str) -> dict`

- Convert LLM JSON to grading pipeline rubric structure
- Generate criterion_ids from dimension titles
- Set default values for scoring_weights, semantic_decay, etc.
- Return full rubric dict matching existing YAML structure

#### `save_rubric_dual_format(rubric_dict: dict, rubric_json: dict, question_id: str, rubrics_dir: Path) -> None`

- Create `json/` and `yaml/` subdirectories
- Save JSON version: `rubrics_dir/json/{question_id}.json`
- Save YAML version: `rubrics_dir/yaml/{question_id}.yaml`
- Update rubric config to reference YAML path

### Command-Line Arguments

- `--source-file`: Path to source file (required)
- `--prompt-template`: Path to prompt template (default: `rubric_generator_template.txt`)
- `--llm-provider`: LLM provider (default: from config)
- `--llm-model`: LLM model name (default: from config)

### Error Handling

- Validate prompt template exists and has placeholders
- Validate source file exists and is readable
- Handle LLM API errors with retries
- Validate JSON structure and point totals
- Handle PDF parsing errors gracefully

## Files to Modify

1. **`autograder/gp/create_dynamic_rubrics_for_each_question.py`**

   - Replace `create_generic_rubric()` with LLM-based generation
   - Add new functions for prompt loading, source file loading, LLM calls
   - Modify `main()` to accept source file argument
   - Update output to save both JSON and YAML

2. **`autograder/gp/rubric_generator_template.txt`** (NEW)

   - Create prompt template file
   - Include placeholders for question and source file
   - Request JSON output format

## Example JSON Structure (LLM Output)

```json
{
  "dimensions": [
    {
      "title": "Object definition and role",
      "points": 3,
      "description": "Clearly defines an object as the entity/instance represented by a row (or record) in the table, i.e., the unit of analysis being described by measured/recorded values."
    },
    {
      "title": "Attribute definition and role",
      "points": 3,
      "description": "Clearly defines an attribute as a variable/feature represented by a column, i.e., a named property/dimension used to describe objects and taking values across rows."
    }
  ],
  "total_points": 10
}
```

## Testing Considerations

- Test with various source file formats (text, PDF)
- Test prompt template variations
- Validate JSON parsing and conversion
- Verify output files are created in correct directories
- Test rubric config updates

## CLI Arguments and Wrapper Script

### Comprehensive Command-Line Interface

The script must support full CLI execution with proper `--help` output:

#### Required Arguments:

- `--source-file`: Path to source file (text, markdown, or PDF) to include in prompt context
- `--questions-file`: Path to questions markdown file (default: `ten_questions.md`)

#### Optional Arguments:

- `--prompt-template`: Path to prompt template file (default: `rubric_generator_template.txt` in same directory as script)
- `--rubrics-dir`: Directory to write rubric files (default: `rubrics`)
- `--start-from`: Start creating rubrics from question number (default: 3, creates q03-q10)
- `--llm-provider`: LLM provider - "openai", "anthropic", "gemini", or "ollama" (default: from config)
- `--llm-model`: LLM model name (default: from config)
- `--dry-run`: Show what would be generated without calling LLM (for testing)
- `--verbose`: Enable verbose output with detailed logging

#### Help Output Requirements:

- Clear description of script purpose
- Detailed argument descriptions with defaults
- Example usage commands
- Notes about output structure (json/ and yaml/ subdirectories)
- Use `argparse.RawDescriptionHelpFormatter` for formatted help

### Wrapper Script

**File**: `autograder/create_dynamics_rubrics.x`

Create a bash wrapper script following the pattern of existing `.x` scripts:

```bash
#!/bin/bash
# Script to create dynamic rubrics using LLM generation
#
# Usage:
#   ./create_dynamics_rubrics.x --source-file path/to/source.pdf
#   ./create_dynamics_rubrics.x --help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating dynamic rubrics with LLM..."
echo ""

# Pass all arguments to the Python script
uv run python gp/create_dynamic_rubrics_for_each_question.py "$@"

echo ""
echo "✓ Rubric generation complete!"
```

**Requirements**:

- Executable permissions (`chmod +x`)
- Uses `uv run python` to execute the module
- Passes all arguments through with `"$@"`
- Provides helpful output messages
- Follows existing `.x` script patterns in codebase

### Updated Implementation Tasks

Add to existing todos:

9. **Implement comprehensive CLI argument parsing** with argparse including all required and optional arguments
10. **Create detailed `--help` output** with descriptions, examples, and usage notes
11. **Create wrapper script** `create_dynamics_rubrics.x` in `autograder/` directory
12. **Add argument validation** for source file existence, prompt template existence, etc.
13. **Implement `--dry-run` mode** that shows what would be generated without LLM calls
14. **Implement `--verbose` mode** for detailed logging throughout the process

### CLI Usage Examples

The help output should include examples like:

```bash
# Basic usage
python create_dynamic_rubrics_for_each_question.py \
  --source-file grading_pipeline/sources/slides.pdf \
  --questions-file ten_questions.md

# Custom prompt template and output directory
python create_dynamic_rubrics_for_each_question.py \
  --source-file sources/textbook.pdf \
  --prompt-template custom_template.txt \
  --rubrics-dir custom_rubrics \
  --start-from 1

# Using wrapper script
./create_dynamics_rubrics.x \
  --source-file grading_pipeline/sources/slides.pdf \
  --questions-file ten_questions.md \
  --verbose

# Dry run to test without LLM calls
./create_dynamics_rubrics.x \
  --source-file sources/slides.pdf \
  --dry-run
```

## Additional Requirements and Updates

### 1. Use index_builder_in_memory.py for PDF Loading

**Change**: Instead of using `index_builder.py`, use `index_builder_in_memory.py` for source file loading.

- Import `_load_file_source_with_pdf` from `grading_pipeline.index_builder` (it's already imported by `index_builder_in_memory.py`)
- Or import directly: `from grading_pipeline.index_builder import _load_file_source_with_pdf`
- This function handles PDF, text, and markdown files
- For single file loading (not from YAML config), create a wrapper that uses the same PDF extraction logic

### 2. JSON Validation with Pydantic

**Requirement**: Validate LLM JSON output using Pydantic with retry logic.

#### Pydantic Schema:

```python
from pydantic import BaseModel, Field, field_validator

class RubricDimension(BaseModel):
    title: str = Field(..., description="Dimension title")
    points: int = Field(..., ge=1, le=10, description="Points for this dimension")
    description: str = Field(..., description="Full-credit description")

class RubricJsonResponse(BaseModel):
    dimensions: list[RubricDimension] = Field(..., min_length=2, max_length=5)
    total_points: int = Field(default=10, const=True)
    
    @field_validator('dimensions')
    @classmethod
    def validate_total_points(cls, v):
        total = sum(d.points for d in v)
        if total != 10:
            raise ValueError(f"Total points must equal 10, got {total}")
        return v
```

#### Retry Logic:

- Attempt LLM call up to 3 times
- On each failure, parse error and provide feedback to LLM
- After 3 failures, abort with clear error message:
  ```
  Error: Failed to generate valid rubric after 3 attempts.
  Last error: [specific validation error]
  LLM response (last attempt): [truncated response]
  ```


### 3. LLM Configuration

**Requirement**: Use the same LLM as the grader (OSS-20b with Ollama).

- Default to Ollama provider with `gpt-oss:20b` model
- Use `configure_llm()` from `config.llm_config` with defaults
- Allow override via `--llm-provider` and `--llm-model` arguments
- Configuration should match grader setup (from `~/.env`)

### 4. Module Execution Support

**Requirement**: Script should be executable as a module using `-m` option.

- Ensure `gp/__init__.py` exists (already present)
- Script should be runnable as: `python -m gp.create_dynamic_rubrics_for_each_question`
- Wrapper script should use: `uv run python -m gp.create_dynamic_rubrics_for_each_question`
- Update all documentation and examples to use module format

### 5. Testing with pytest

**Requirement**: Add comprehensive tests in `tests/` directory using pytest.

#### Test File: `tests/test_create_dynamic_rubrics.py`

Test cases to include:

1. **Test prompt template loading**

   - Valid template with placeholders
   - Missing placeholders
   - Invalid file path

2. **Test source file loading**

   - Text file loading
   - Markdown file loading
   - PDF file loading
   - Invalid file path
   - Unsupported file type

3. **Test prompt formatting**

   - Correct placeholder replacement
   - Multiple questions
   - Long source file content

4. **Test JSON validation**

   - Valid JSON structure
   - Invalid JSON (malformed)
   - Invalid structure (missing fields)
   - Wrong point totals
   - Too few/many dimensions

5. **Test retry logic**

   - Mock LLM failures
   - Verify retry attempts
   - Verify final failure handling

6. **Test rubric conversion**

   - JSON to YAML structure conversion
   - Criterion ID generation
   - Default values application

7. **Test dual format saving**

   - JSON file creation
   - YAML file creation
   - Directory structure
   - Config file updates

8. **Integration test**

   - End-to-end with mock LLM
   - Verify output files
   - Verify config updates

#### Test Structure:

```python
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from gp.create_dynamic_rubrics_for_each_question import (
    load_prompt_template,
    load_source_file,
    format_prompt,
    generate_rubric_with_llm,
    convert_json_to_rubric_structure,
    save_rubric_dual_format,
)
```

### Updated Implementation Details

#### Source File Loading Function:

```python
def load_source_file(source_path: Path) -> str:
    """Load source file content (text, markdown, or PDF).
    
    Uses _load_file_source_with_pdf logic from index_builder.py
    """
    from grading_pipeline.index_builder import _extract_text_from_pdf
    
    if source_path.suffix.lower() == '.pdf':
        return _extract_text_from_pdf(source_path)
    else:
        with open(source_path, 'r', encoding='utf-8') as f:
            return f.read()
```

#### LLM Generation with Retry:

```python
def generate_rubric_with_llm(
    prompt: str, 
    llm: LLM, 
    max_retries: int = 3,
    verbose: bool = False
) -> dict:
    """Generate rubric JSON with validation and retry logic."""
    from pydantic import ValidationError
    from gp.rubric_schema import RubricJsonResponse
    
    for attempt in range(max_retries):
        try:
            response = llm.complete(prompt)
            json_text = extract_json_from_response(response.text)
            rubric_data = json.loads(json_text)
            
            # Validate with Pydantic
            validated = RubricJsonResponse.model_validate(rubric_data)
            return validated.model_dump()
            
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt < max_retries - 1:
                if verbose:
                    print(f"Attempt {attempt + 1} failed: {e}")
                # Add feedback to prompt for next attempt
                prompt += f"\n\nPrevious attempt failed validation: {str(e)}"
            else:
                raise ValueError(
                    f"Failed to generate valid rubric after {max_retries} attempts.\n"
                    f"Last error: {str(e)}\n"
                    f"LLM response (last attempt): {response.text[:500]}..."
                ) from e
```

### Updated Files to Create/Modify

1. **`autograder/gp/create_dynamic_rubrics_for_each_question.py`**

   - Update source file loading to use `_extract_text_from_pdf` from `index_builder.py`
   - Add Pydantic validation with retry logic
   - Use module execution format
   - Default to Ollama with gpt-oss:20b

2. **`autograder/gp/rubric_schema.py`** (NEW)

   - Pydantic models for JSON validation
   - `RubricDimension` and `RubricJsonResponse` models

3. **`autograder/tests/test_create_dynamic_rubrics.py`** (NEW)

   - Comprehensive pytest test suite
   - Mock LLM responses
   - Test all functions and error cases

4. **`autograder/create_dynamics_rubrics.x`** (UPDATE)

   - Use module format: `uv run python -m gp.create_dynamic_rubrics_for_each_question`