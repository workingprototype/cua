#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print step information
print_step() {
    echo -e "${BLUE}==> $1${NC}"
}

# Function to print success message
print_success() {
    echo -e "${GREEN}==> Success: $1${NC}"
}

# Function to print error message
print_error() {
    echo -e "${RED}==> Error: $1${NC}" >&2
}

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Change to project root
cd "$PROJECT_ROOT"

print_step "Starting cleanup of all caches and virtual environments..."

# Remove all virtual environments
print_step "Removing virtual environments..."
find . -type d -name ".venv" -exec rm -rf {} +
print_success "Virtual environments removed"

# Remove all Python cache files and directories
print_step "Removing Python cache files and directories..."
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name ".mypy_cache" -exec rm -rf {} +
find . -type d -name ".ruff_cache" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete
print_success "Python cache files removed"

# Remove all build artifacts
print_step "Removing build artifacts..."
find . -type d -name "build" -exec rm -rf {} +
find . -type d -name "dist" -exec rm -rf {} +
find . -type d -name "*.egg-info" -exec rm -rf {} +
find . -type d -name "*.egg" -exec rm -rf {} +
print_success "Build artifacts removed"

# Remove PDM-related files and directories
print_step "Removing PDM-related files and directories..."
find . -name "pdm.lock" -delete
find . -type d -name ".pdm-build" -exec rm -rf {} +
find . -name ".pdm-python" -delete  # .pdm-python is a file, not a directory
print_success "PDM-related files removed"

# Remove MCP-related files
print_step "Removing MCP-related files..."
find . -name "mcp_server.log" -delete
print_success "MCP-related files removed"

# Remove .env file
print_step "Removing .env file..."
rm -f .env
print_success ".env file removed"

# Remove typings directory
print_step "Removing typings directory..."
rm -rf .vscode/typings
print_success "Typings directory removed"

# Clean up any temporary files
print_step "Removing temporary files..."
find . -name "*.tmp" -delete
find . -name "*.bak" -delete
find . -name "*.swp" -delete
print_success "Temporary files removed"

print_success "Cleanup complete! All caches and virtual environments have been removed."
print_step "To rebuild the project, run: bash scripts/build.sh"
