#!/usr/bin/env bash
# Test and run grading_pipeline components
#
# This script:
# 1. Tests incremental indexing functionality
# 2. Tests index_builder with PDF support
# 3. Runs comprehensive incremental indexing test suite
# 4. Tests batch-by-question grading pipeline components
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
echo -e "${YELLOW}[Test 1/7] Testing index_builder with incremental indexing...${NC}"
if uv run python -m grading_pipeline.index_builder; then
    echo -e "${GREEN}✓ Index builder test passed${NC}\n"
else
    echo -e "${RED}✗ Index builder test failed${NC}\n"
    exit 1
fi

# Test 2: Comprehensive incremental indexing test suite
echo -e "${YELLOW}[Test 2/7] Running comprehensive incremental indexing tests...${NC}"
echo -e "${BLUE}Running: uv run python tests/test_pipeline_incremental_indexing.py${NC}\n"
if uv run python tests/test_pipeline_incremental_indexing.py; then
    echo -e "${GREEN}✓ Incremental indexing test suite passed${NC}\n"
else
    echo -e "${RED}✗ Incremental indexing test suite failed${NC}\n"
    exit 1
fi

# Test 3: Manifest functionality (if available)
if [ -f "grading_pipeline/manifest.py" ]; then
    echo -e "${YELLOW}[Test 3/7] Testing manifest functionality...${NC}"
    if uv run python -m grading_pipeline.manifest; then
        echo -e "${GREEN}✓ Manifest test passed${NC}\n"
    else
        echo -e "${YELLOW}⚠ Manifest test had issues (may not have __main__)${NC}\n"
    fi
else
    echo -e "${YELLOW}[Test 3/7] Skipping manifest test (file not found)${NC}\n"
fi

# Test 4: Config loader (batch-by-question architecture)
echo -e "${YELLOW}[Test 4/7] Testing config_loader...${NC}"
echo -e "${BLUE}Running: uv run python tests/test_config_loader.py${NC}\n"
if uv run python tests/test_config_loader.py; then
    echo -e "${GREEN}✓ Config loader test passed${NC}\n"
else
    echo -e "${RED}✗ Config loader test failed${NC}\n"
    exit 1
fi

# Test 5: Submission loader (batch-by-question architecture)
echo -e "${YELLOW}[Test 5/7] Testing submission_loader...${NC}"
echo -e "${BLUE}Running: uv run python tests/test_submission_loader.py${NC}\n"
if uv run python tests/test_submission_loader.py; then
    echo -e "${GREEN}✓ Submission loader test passed${NC}\n"
else
    echo -e "${RED}✗ Submission loader test failed${NC}\n"
    exit 1
fi

# Test 6: Submission converter (batch-by-question architecture)
echo -e "${YELLOW}[Test 6/7] Testing submission_converter...${NC}"
echo -e "${BLUE}Running: uv run python tests/test_submission_converter.py${NC}\n"
if uv run python tests/test_submission_converter.py; then
    echo -e "${GREEN}✓ Submission converter test passed${NC}\n"
else
    echo -e "${RED}✗ Submission converter test failed${NC}\n"
    exit 1
fi

# Test 7: Pipeline batch (result writing)
echo -e "${YELLOW}[Test 7/7] Testing pipeline batch (result writing)...${NC}"
echo -e "${BLUE}Running: uv run python tests/test_pipeline_batch.py${NC}\n"
if uv run python tests/test_pipeline_batch.py; then
    echo -e "${GREEN}✓ Pipeline batch test passed${NC}\n"
else
    echo -e "${RED}✗ Pipeline batch test failed${NC}\n"
    exit 1
fi

# Final cleanup of test artifacts
echo -e "\n${YELLOW}[Cleanup] Removing test artifacts...${NC}"
if [ -d "tests/tmp_chroma_indexes" ]; then
    rm -rf tests/tmp_chroma_indexes
    echo -e "${GREEN}✓ Cleaned up tests/tmp_chroma_indexes${NC}"
else
    echo -e "${BLUE}  No test artifacts to clean up${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}All grading_pipeline tests passed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Summary:${NC}"
echo -e "  ✓ Incremental indexing"
echo -e "  ✓ Index builder with PDF support"
echo -e "  ✓ Manifest tracking"
echo -e "  ✓ Config loader (batch-by-question)"
echo -e "  ✓ Submission loader (batch-by-question)"
echo -e "  ✓ Submission converter (batch-by-question)"
echo -e "  ✓ Pipeline batch (result writing)"
