#!/bin/bash
#
# Script used to start OurAI 
#

# Get the current directory (where user is running from)
USER_DIR="$(pwd)"

# Check if current directory is a git repository
if [[ ! -d "$USER_DIR/.git" ]]; then
    echo "ERROR: we run only with git project initialized."
    exit 1
fi

# Get the directory where this script is located (resolve symbolic links)
SCRIPT_PATH="$( readlink -f "${BASH_SOURCE[0]}" )"
SCRIPT_DIR="$( dirname "$SCRIPT_PATH" )"

# Parse arguments
VENV_PATH="$SCRIPT_DIR/.venv"
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

# Export the PROJECT directory so tools know where the project is
export OURAI_PROJECT_DIR="$SCRIPT_DIR"

# Create required directories and files in project directory
mkdir -p "$SCRIPT_DIR/history" 2>/dev/null
mkdir -p "$SCRIPT_DIR/.session" 2>/dev/null
if [[ ! -f "$SCRIPT_DIR/sessid.aiia" ]]; then
    echo "1" > "$SCRIPT_DIR/sessid.aiia"
fi

# Add project directories to PYTHONPATH so run.py can find modules
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/src:$SCRIPT_DIR/tools:$PYTHONPATH"

# Run the program from current directory
cd "$USER_DIR" || exit 1
"$PYTHON" "$SCRIPT_DIR/run.py" "${ARGS[@]}"
