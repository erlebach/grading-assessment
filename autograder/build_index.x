#!/bin/bash
# Simple script to build or rebuild grading pipeline indexes
#
# Usage:
#   ./build_index.x                    # Incremental build (default)
#   ./build_index.x --force            # Force complete rebuild
#   ./build_index.x --force-word       # Rebuild word index only
#   ./build_index.x --force-sentence   # Rebuild sentence index only
#   ./build_index.x --help             # Show all options

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building grading pipeline indexes..."
echo ""

# Pass all arguments to the Python script
uv run python -m grading_pipeline.build_index "$@"

echo ""
echo "✓ Index build complete!"
echo "  Indexes: grading_pipeline/tmp/chroma_db/"
