#!/bin/bash

set -e

# Function to check if a command exists (silent)
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a Python package is installed (silent)
package_installed() {
    python3 -c "import importlib.util; print(importlib.util.find_spec('$1') is not None)" 2>/dev/null | grep -q "True" 2>/dev/null
}

# Check if Python is installed
if ! command_exists python3; then
    exit 1
fi

# Check if pip is installed
if ! command_exists pip3; then
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Add the necessary paths to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Change to project directory
cd "$PROJECT_ROOT" 2>/dev/null

# Check if mcp_server package is installed
if ! package_installed mcp_server; then
    # Check if setup.py or pyproject.toml exists
    if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
        pip3 install --quiet --user -e . >/dev/null 2>&1
    fi
fi

# Run the server module directly - this is the only thing that should produce output
exec python3 -m mcp_server.server 