#!/usr/bin/env bash

# Setup .env.local
echo "PYTHON_BIN=python" > /workspaces/cua/.env.local

# Run /scripts/build.sh
./scripts/build.sh

# Open VSCode .code-workspace file
# https://gist.github.com/Kaptensanders/79da7c1547751fb43c75904e3110bbf9

# check for dependencies
if ! command -v xxd &> /dev/null; then
    echo "xxd command not found, install with"
    echo "sudo apt install xxd"
    exit 1
fi

DEVCONTAINER_JSON="$PWD/.devcontainer/devcontainer.json"
CODE_WS_FILE=$(ls $PWD/*.code-workspace 2>/dev/null)

if [ ! -f "$DEVCONTAINER_JSON" ];then

    # open code without container

    if [ -f "$CODE_WS_FILE" ]; then
        echo "Opening vscode workspace from $CODE_WS_FILE"
        code $CODE_WS_FILE
    else
        echo "Opening vscode in current directory"
        code .
    fi
    exit 0
fi

# open devcontainer
if command -v wslpath >/dev/null 2>&1; then
    HOST_PATH=$(echo $(wslpath -w $PWD) | sed -e 's,\\,\\\\,g')
else
    # Not on WSL, fallback for macOS/Linux
    HOST_PATH="$PWD"
fi
WORKSPACE="/workspaces/$(basename $PWD)"

URI_SUFFIX=
if [ -f "$CODE_WS_FILE" ]; then
    # open workspace file
    URI_TYPE="--file-uri"
    URI_SUFFIX="$WORKSPACE/$(basename $CODE_WS_FILE)"
    echo "Opening vscode workspace file within devcontainer"
else
    URI_TYPE="--folder-uri"
    URI_SUFFIX="$WORKSPACE"
    echo "Opening vscode within devcontainer"
fi

URI="{\"hostPath\":\"$HOST_PATH\",\"configFile\":{\"\$mid\":1,\"path\":\"$DEVCONTAINER_JSON\",\"scheme\":\"vscode-fileHost\"}}"
URI_HEX=$(echo "${URI}" | xxd -c 0 -p)
code ${URI_TYPE}="vscode-remote://dev-container%2B${URI_HEX}${URI_SUFFIX}" &