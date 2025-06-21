#!/usr/bin/env bash

WORKSPACE="/workspaces/cua"

# Run /scripts/build.sh
./scripts/build.sh

# ---
# Build is complete. Show user a clear message to open the workspace manually.
# ---

cat << 'EOM'

============================================
  🚀 Build complete!

  👉 Next steps:

    1. Open '.vscode/py.code-workspace'
    2. Press 'Open Workspace'

  Happy coding!
============================================

EOM
