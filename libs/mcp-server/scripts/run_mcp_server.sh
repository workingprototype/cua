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
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check if pip is installed
if ! command_exists pip3; then
    echo "Error: pip3 is not installed."
    exit 1
fi

# Check if cua-mcp-server command is available
if ! command_exists cua-mcp-server; then
    echo "Installing cua-mcp-server..."
    pip3 install cua-mcp-server
fi

# Run the installed command directly
exec cua-mcp-server

