#!/bin/bash
# Simple script to run the grading pipeline for q01 with 2 students

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Running grading pipeline for q01 with 2 students..."
echo ""

# Run the grading pipeline
uv run python -m grading_pipeline.cli grade-question \
  --question q01 \
  --rubrics-config grading_pipeline/config/rubrics.yaml \
  --submissions-dir grading_pipeline/submissions \
  --sources-config grading_pipeline/config/sources.yaml \
  --index-dir grading_pipeline/tmp/in_memory_indexes \
  --index-backend in-memory \
  --output grading_pipeline/results/q01_results.json \
  --mode sequential \
  --log grading_pipeline/results/q01_grading.log

echo ""
echo "✓ Grading complete!"
echo "  Results: grading_pipeline/results/q01_results.json"
echo "  Log: grading_pipeline/results/q01_grading.log"
