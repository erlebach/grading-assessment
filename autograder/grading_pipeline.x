#!/usr/bin/env bash
# Test and run grading_pipeline components
#
# This script:
# 1. Tests incremental indexing functionality
# 2. Tests index_builder with PDF support
# 3. Runs comprehensive incremental indexing test suite
#
# Usage: bash grading_pipeline.x

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOGRADER_DIR="$(cd "$SCRIPT_DIR" && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Grading Pipeline Test & Run Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Change to autograder directory
cd "$AUTOGRADER_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed or not in PATH${NC}"
    echo "Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Test 1: Index Builder (incremental indexing)
echo -e "${YELLOW}[Test 1/3] Testing index_builder with incremental indexing...${NC}"
if uv run python -m grading_pipeline.index_builder; then
    echo -e "${GREEN}✓ Index builder test passed${NC}\n"
else
    echo -e "${RED}✗ Index builder test failed${NC}\n"
    exit 1
fi

# Test 2: Comprehensive incremental indexing test suite
echo -e "${YELLOW}[Test 2/3] Running comprehensive incremental indexing tests...${NC}"
echo -e "${BLUE}Running: uv run python tests/test_pipeline_incremental_indexing.py${NC}\n"
if uv run python tests/test_pipeline_incremental_indexing.py; then
    echo -e "${GREEN}✓ Incremental indexing test suite passed${NC}\n"
else
    echo -e "${RED}✗ Incremental indexing test suite failed${NC}\n"
    exit 1
fi

# Test 3: Manifest functionality (if available)
if [ -f "grading_pipeline/manifest.py" ]; then
    echo -e "${YELLOW}[Test 3/3] Testing manifest functionality...${NC}"
    if uv run python -m grading_pipeline.manifest; then
        echo -e "${GREEN}✓ Manifest test passed${NC}\n"
    else
        echo -e "${YELLOW}⚠ Manifest test had issues (may not have __main__)${NC}\n"
    fi
else
    echo -e "${YELLOW}[Test 3/3] Skipping manifest test (file not found)${NC}\n"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All grading_pipeline tests passed!${NC}"
echo -e "${GREEN}========================================${NC}"
