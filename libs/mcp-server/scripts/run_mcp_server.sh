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
    echo "Python 3 is not installed. Please install Python 3."
    exit 1
fi

# Check if pip is installed
if ! command_exists pip3; then
    echo "pip3 is not installed. Please install pip3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment for CUA MCP Server..."
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
        echo "Installing cua-mcp-server in virtual environment..."
        pip install "cua-mcp-server"
    fi
    
    # Check if torch is installed in the virtual environment
    if ! python3 -c "import importlib.util; print(importlib.util.find_spec('torch') is not None)" 2>/dev/null | grep -q "True" 2>/dev/null; then
        echo "Installing torch in virtual environment..."
        pip install torch
    fi
fi

# Run the server in the virtual environment
echo "Starting MCP Server..."
python3 -c "from mcp_server.server import main; main()"
