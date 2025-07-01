#!/bin/bash

set -e

# Set the CUA repository path based on script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CUA_REPO_DIR="$( cd "$SCRIPT_DIR/../../.." &> /dev/null && pwd )"
PYTHON_PATH="${CUA_REPO_DIR}/.venv/bin/python"

# Set Python path to include all necessary libraries
export PYTHONPATH="${CUA_REPO_DIR}/libs/mcp-server:${CUA_REPO_DIR}/libs/agent:${CUA_REPO_DIR}/libs/computer:${CUA_REPO_DIR}/libs/core:${CUA_REPO_DIR}/libs/pylume"

# Run the MCP server directly as a module
$PYTHON_PATH -m mcp_server.server