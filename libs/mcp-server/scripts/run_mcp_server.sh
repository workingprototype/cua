#!/bin/bash

set -e

# Directory for virtual environment
VENV_DIR="$HOME/.cua-mcp-venv"

# Function to check if a command exists (silent)
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

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
    pip install "cua-mcp-server" torch
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
