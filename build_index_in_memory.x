#!/bin/bash
# Simple script to build or rebuild grading pipeline indexes in memory
#
# Usage:
#   ./build_index_in_memory.x                    # Incremental build (default)
#   ./build_index_in_memory.x --force            # Force complete rebuild
#   ./build_index_in_memory.x --force-word       # Rebuild word index only
#   ./build_index_in_memory.x --force-sentence   # Rebuild sentence index only
#   ./build_index_in_memory.x --help             # Show all options

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building grading pipeline indexes..."
echo ""

# Pass all arguments to the Python script
uv run python -m grading_pipeline.build_index_in_memory "$@"

echo ""
echo "✓ Index build complete!"
echo "  Indexes (in memory): grading_pipeline/tmp/chroma_db/"
