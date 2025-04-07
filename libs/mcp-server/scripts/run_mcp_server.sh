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

# Check if mcp_server package is installed
if ! package_installed mcp_server; then
    pip3 install -e "cua-mcp-server"
fi

exec python3 -c "from mcp_server.server import main; main()"

