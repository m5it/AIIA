#!/bin/bash
#
# Script used to start OurAI 
#

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script's directory (ensures we're in the program's main directory)
cd "$SCRIPT_DIR" || exit 1

# Verify we're in the correct directory by checking for run.py
if [[ ! -f "run.py" ]]; then
    echo "ERROR: run.py not found in $(pwd)"
    echo "Please ensure you're running from the OurAI project directory"
    echo "or that start.sh is in the correct location."
    exit 1
fi

# Check if directory is a git repository (required for OurAI to start)
if [[ ! -d ".git" ]]; then
    echo "ERROR: Not a git repository. OurAI requires git initialization."
    echo "Please initialize with: git init"
    exit 1
fi

# Parse arguments
VENV_PATH=".venv"
ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --venv)
            VENV_PATH="$2"
            shift 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Check if virtual environment exists
if [[ ! -f "$VENV_PATH/bin/python3" && ! -f "$VENV_PATH/bin/python" ]]; then
    echo "ERROR: Virtual environment not found at $VENV_PATH/bin/python"
    echo "Please create one with: python3 -m venv $VENV_PATH"
    echo "Or specify path with: $0 --venv /path/to/venv"
    exit 1
fi

# Use python3 if exists, else python
if [[ -f "$VENV_PATH/bin/python3" ]]; then
    PYTHON="$VENV_PATH/bin/python3"
else
    PYTHON="$VENV_PATH/bin/python"
fi

# Test if ollama is installed
if ! "$PYTHON" -c "import ollama" 2>/dev/null; then
    echo "WARNING: ollama library not found in $VENV_PATH"
    echo "Please install it with: $PYTHON -m pip install ollama"
fi

# Run the program
"$PYTHON" run.py "${ARGS[@]}"
