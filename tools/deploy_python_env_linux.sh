#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

VENV_DIR=".venv"
REQ_FILE="requirements.txt"

# Help function
function show_help {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -r, --req FILE      Set requirements file (default: requirements.txt)"
    echo "  -c, --clean         Clean install (remove existing venv)"
    echo "  -h, --help          Show this help message"
}

# Parse arguments
CLEAN=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -r|--req) REQ_FILE="$2"; shift ;;
        -c|--clean) CLEAN=true ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

echo -e "${GREEN}Start to deploy python environment${NC}"

# Check python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    exit 1
fi

# Clean if requested
if [ "$CLEAN" = true ] && [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Removing existing virtual environment...${NC}"
    rm -rf "$VENV_DIR"
fi

# Create venv
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment in $VENV_DIR...${NC}"
    python3 -m venv "$VENV_DIR"
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
fi

# Activate
echo -e "${GREEN}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Install dependencies
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

if [ -f "$REQ_FILE" ]; then
    echo -e "${GREEN}Installing dependencies from $REQ_FILE...${NC}"
    pip install -r "$REQ_FILE"
else
    echo -e "${YELLOW}Warning: $REQ_FILE not found. Skipping dependency installation.${NC}"
fi

echo -e "${GREEN}Deployment finished successfully!${NC}"
