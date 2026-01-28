# Plan Update: CLI Arguments and Wrapper Script

## Additional Requirements

### 1. Comprehensive CLI Arguments

The `create_dynamic_rubrics_for_each_question.py` script must support the following command-line arguments with proper `--help` output:

#### Required Arguments:
- `--source-file`: Path to source file (text, markdown, or PDF) to include in prompt context
- `--questions-file`: Path to questions markdown file (default: `ten_questions.md`)

#### Optional Arguments:
- `--prompt-template`: Path to prompt template file (default: `rubric_generator_template.txt` in same directory)
- `--rubrics-dir`: Directory to write rubric files (default: `rubrics`)
- `--start-from`: Start creating rubrics from question number (default: 3, creates q03-q10)
- `--llm-provider`: LLM provider - "openai", "anthropic", "gemini", or "ollama" (default: from config)
- `--llm-model`: LLM model name (default: from config)
- `--dry-run`: Show what would be generated without calling LLM
- `--verbose`: Enable verbose output

#### Help Output Format:
The `--help` output should include:
- Clear description of the script's purpose
- Detailed argument descriptions
- Example usage commands
- Notes about output directories (json/ and yaml/ subdirectories)

### 2. Wrapper Script

Create `autograder/create_dynamics_rubrics.x` (bash script) that:
- Uses `#!/bin/bash` shebang
- Sets `set -e` for error handling
- Gets script directory and changes to it
- Uses `uv run python` to execute the Python module
- Passes all arguments through with `"$@"`
- Provides helpful output messages
- Follows the pattern of existing `.x` scripts in the codebase

#### Script Location:
- File: `autograder/create_dynamics_rubrics.x`
- Executable permissions should be set

#### Script Content Pattern:
```bash
#!/bin/bash
# Script to create dynamic rubrics using LLM generation
#
# Usage:
#   ./create_dynamics_rubrics.x --source-file path/to/source.pdf --questions-file ten_questions.md
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

## Updated Implementation Tasks

Add to existing todos:

1. **Add comprehensive CLI argument parsing** with argparse including all required and optional arguments
2. **Implement `--help` output** with detailed descriptions and examples
3. **Create wrapper script** `create_dynamics_rubrics.x` in `autograder/` directory
4. **Add argument validation** for source file existence, prompt template existence, etc.
5. **Add `--dry-run` mode** that shows what would be generated without LLM calls
6. **Add `--verbose` mode** for detailed logging

## CLI Usage Examples

The help output should show examples like:

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
```
