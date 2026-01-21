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
uv run python -m gp.create_dynamic_rubrics_for_each_question "$@"

echo ""
echo "✓ Rubric generation complete!"
