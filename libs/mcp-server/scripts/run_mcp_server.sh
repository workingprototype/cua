#!/bin/bash

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a Python package is installed
package_installed() {
    python3 -c "import importlib.util; print(importlib.util.find_spec('$1') is not None)" | grep -q "True"
}

echo "🚀 CUA MCP Server Setup Script"
echo "============================="

# Check if Python is installed
if ! command_exists python3; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

echo "✅ Python 3 is installed"

# Check if pip is installed
if ! command_exists pip3; then
    echo "❌ pip3 is not installed. Please install pip and try again."
    exit 1
fi

echo "✅ pip3 is installed"

# Check if mcp_server package is installed
if ! package_installed mcp_server; then
    echo "🔄 mcp_server package is not installed. Installing now..."
    pip3 install --user -e .
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install mcp_server. Please check the error messages above."
        exit 1
    fi
    
    echo "✅ mcp_server installed successfully"
else
    echo "✅ mcp_server is already installed"
fi

# Run the Python module directly
echo "🚀 Starting MCP server..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Add the necessary paths to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run the server module directly
python3 -m mcp_server.server 