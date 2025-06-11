#!/usr/bin/env bash

WORKSPACE="/workspaces/cua"

# Setup .env.local
echo "PYTHON_BIN=python" > /workspaces/cua/.env.local

# Run /scripts/build.sh
./scripts/build.sh

# check for dependencies
if ! command -v xxd &> /dev/null; then
    echo "xxd command not found, install with"
    echo "sudo apt install xxd"
    exit 1
fi

CODE_WS_FILE="$WORKSPACE/.vscode/py.code-workspace"
export code="$(ls /vscode/vscode-server/bin/*/*/bin/remote-cli/code 2>/dev/null | head -n 1)"

"$code" $CODE_WS_FILE &
