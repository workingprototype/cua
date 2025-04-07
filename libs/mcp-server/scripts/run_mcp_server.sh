#!/bin/bash

set -e

# Function to check if a directory is writable
is_writable() {
    [ -w "$1" ]
}

# Function to check if a command exists (silent)
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Find a writable directory for the virtual environment
if is_writable "$HOME"; then
    VENV_DIR="$HOME/.cua-mcp-venv"
elif is_writable "/tmp"; then
    VENV_DIR="/tmp/.cua-mcp-venv"
else
    # Try to create a directory in the current working directory
    TEMP_DIR="$(pwd)/.cua-mcp-venv"
    if is_writable "$(pwd)"; then
        VENV_DIR="$TEMP_DIR"
    else
        echo "Error: Cannot find a writable directory for the virtual environment." >&2
        exit 1
    fi
fi

# Check if Python is installed
if ! command_exists python3; then
    exit 1
fi

# Check if pip is installed
if ! command_exists pip3; then
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install the required packages
    pip install "cua-mcp-server"
else
    # Activate existing virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Check if mcp_server package is installed in the virtual environment
    if ! python3 -c "import importlib.util; print(importlib.util.find_spec('mcp_server') is not None)" 2>/dev/null | grep -q "True" 2>/dev/null; then
        pip install "cua-mcp-server"
    fi
fi

# Run the server in the virtual environment
python3 -c "from mcp_server.server import main; main()"
