#!/usr/bin/env bash

if [ "$1" == "--help" ]; then
    
    cat << EOF
Run from project folder, auto opens vscode in some mode depending on folder contents:

* Folder contains .devcontainer/devcontainer.json and <name>.code-workspace file: vscode opens in devcontainer, workspace file is loaded
* Folder contains .devcontainer/devcontainer.json: vscode opens in devcontainer
* Folder contains <name>.code-workspace file: Workspace is opened in vscode
* Folder contains no <name>.code-workspace and no devcontainer: vscode is opened, loading contents of the current folder

This script was created for WSL2, probably works the same way for native Linux, but untested

Assumes the following filestructure:

<some folder>
| 
| -- <name>.code-workspace
| -- ./devcontainer/devcontainer.json
| -- ...

Note: If you set workspaceFolder or workspaceMount in devcontainer.json this may cause issues
      Also, if .devcontainer/devcontainer.json is not in the root of your repository, you may get in trouble
      refer to https://code.visualstudio.com/remote/advancedcontainers/change-default-source-mount 

EOF
    exit 0
fi

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