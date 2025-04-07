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

# Check if cua-mcp-server is installed
if ! package_installed mcp_server || ! command_exists cua-mcp-server; then
    echo "🔄 cua-mcp-server is not installed. Installing now..."
    pip3 install --user cua-mcp-server
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install cua-mcp-server. Please check the error messages above."
        exit 1
    fi
    
    echo "✅ cua-mcp-server installed successfully"
else
    echo "✅ cua-mcp-server is already installed"
fi

# Create scripts directory if it doesn't exist
mkdir -p ~/.cua/scripts

# Update PATH to include user's local bin directory where pip might have installed the script
export PATH="$HOME/.local/bin:$PATH"

echo "🚀 Starting cua-mcp-server..."
exec cua-mcp-server 