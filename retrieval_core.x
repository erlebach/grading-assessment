#!/usr/bin/env bash
# Test and run retrieval_core components
#
# This script:
# 1. Tests index_builder functionality
# 2. Tests retriever functionality  
# 3. Runs the full pipeline in async mode
#
# Usage: bash retrieval_core.x

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
echo -e "${BLUE}Retrieval Core Test & Run Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Change to autograder directory
cd "$AUTOGRADER_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed or not in PATH${NC}"
    echo "Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Test 1: Index Builder
echo -e "${YELLOW}[Test 1/3] Testing index_builder...${NC}"
if uv run python -m retrieval_core.index_builder; then
    echo -e "${GREEN}✓ Index builder test passed${NC}\n"
else
    echo -e "${RED}✗ Index builder test failed${NC}\n"
    exit 1
fi

# Test 2: Retriever
echo -e "${YELLOW}[Test 2/3] Testing retriever...${NC}"
if uv run python -m retrieval_core.retriever; then
    echo -e "${GREEN}✓ Retriever test passed${NC}\n"
else
    echo -e "${RED}✗ Retriever test failed${NC}\n"
    exit 1
fi

# Test 3: Pipeline in async mode
echo -e "${YELLOW}[Test 3/3] Running pipeline in async mode...${NC}"
echo -e "${BLUE}Running: uv run python -m retrieval_core.pipeline --mode async --num-students 2${NC}\n"
if uv run python -m retrieval_core.pipeline --mode async --num-students 2; then
    echo -e "${GREEN}✓ Pipeline async mode test passed${NC}\n"
else
    echo -e "${RED}✗ Pipeline async mode test failed${NC}\n"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All retrieval_core tests passed!${NC}"
echo -e "${GREEN}========================================${NC}"
