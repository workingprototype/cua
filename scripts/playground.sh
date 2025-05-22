#!/bin/bash

set -e

echo "🚀 Setting up CUA playground environment..."

# Check for Apple Silicon Mac
if [[ $(uname -s) != "Darwin" || $(uname -m) != "arm64" ]]; then
  echo "❌ This script requires an Apple Silicon Mac (M1/M2/M3/M4)."
  exit 1
fi

# Check for macOS 15 (Sequoia) or newer
OSVERSION=$(sw_vers -productVersion)
if [[ $(echo "$OSVERSION 15.0" | tr " " "\n" | sort -V | head -n 1) != "15.0" ]]; then
  echo "❌ This script requires macOS 15 (Sequoia) or newer. You have $OSVERSION."
  exit 1
fi

# Create a temporary directory for our work
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

# Function to clean up on exit
cleanup() {
  cd ~
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# Install Lume if not already installed
if ! command -v lume &> /dev/null; then
  echo "📦 Installing Lume CLI..."
  curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh | bash
  
  # Add lume to PATH for this session if it's not already there
  if ! command -v lume &> /dev/null; then
    export PATH="$PATH:$HOME/.local/bin"
  fi
fi

# Pull the macOS CUA image if not already present
if ! lume ls | grep -q "macos-sequoia-cua"; then
  # Check available disk space
  IMAGE_SIZE_GB=30
  AVAILABLE_SPACE_KB=$(df -k $HOME | tail -1 | awk '{print $4}')
  AVAILABLE_SPACE_GB=$(($AVAILABLE_SPACE_KB / 1024 / 1024))
  
  echo "📊 The macOS CUA image will use approximately ${IMAGE_SIZE_GB}GB of disk space."
  echo "   You currently have ${AVAILABLE_SPACE_GB}GB available on your system."
  
  # Prompt for confirmation
  read -p "   Continue? [y]/n: " CONTINUE
  CONTINUE=${CONTINUE:-y}
  
  if [[ $CONTINUE =~ ^[Yy]$ ]]; then
    echo "📥 Pulling macOS CUA image (this may take a while)..."
    lume pull macos-sequoia-cua:latest
  else
    echo "❌ Installation cancelled."
    exit 1
  fi
fi

# Create a Python virtual environment
echo "🐍 Setting up Python environment..."
PYTHON_CMD="python3"

# Check if Python 3.11+ is available
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d" " -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
  echo "❌ Python 3.11+ is required. You have $PYTHON_VERSION."
  echo "Please install Python 3.11+ and try again."
  exit 1
fi

# Create a virtual environment
VENV_DIR="$HOME/.cua-venv"
if [ ! -d "$VENV_DIR" ]; then
  $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install required packages
echo "📦 Updating CUA packages..."
pip install -U pip setuptools wheel Cmake
pip install -U cua-computer "cua-agent[all]"

# Temporary fix for mlx-vlm, see https://github.com/Blaizzy/mlx-vlm/pull/349
pip install git+https://github.com/ddupont808/mlx-vlm.git@stable/fix/qwen2-position-id

# Create a simple demo script
DEMO_DIR="$HOME/.cua-demo"
mkdir -p "$DEMO_DIR"

cat > "$DEMO_DIR/run_demo.py" << 'EOF'
import asyncio
import os
from computer import Computer
from agent import ComputerAgent, LLM, AgentLoop, LLMProvider
from agent.ui.gradio.app import create_gradio_ui

# Try to load API keys from environment
api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    print("\n⚠️  No OpenAI API key found. You'll need to provide one in the UI.")

# Launch the Gradio UI and open it in the browser
app = create_gradio_ui()
app.launch(share=False, inbrowser=True)
EOF

# Create a convenience script to run the demo
cat > "$DEMO_DIR/start_demo.sh" << EOF
#!/bin/bash
source "$VENV_DIR/bin/activate"
cd "$DEMO_DIR"
python run_demo.py
EOF
chmod +x "$DEMO_DIR/start_demo.sh"

echo "✅ Setup complete!"
echo "🖥️  You can start the CUA playground by running: $DEMO_DIR/start_demo.sh"

# Check if the VM is running
echo "🔍 Checking if the macOS CUA VM is running..."
VM_RUNNING=$(lume ls | grep "macos-sequoia-cua" | grep "running" || echo "")

if [ -z "$VM_RUNNING" ]; then
  echo "🚀 Starting the macOS CUA VM in the background..."
  lume run macos-sequoia-cua:latest &
  # Wait a moment for the VM to initialize
  sleep 5
  echo "✅ VM started successfully."
else
  echo "✅ macOS CUA VM is already running."
fi

# Ask if the user wants to start the demo now
echo
read -p "Would you like to start the CUA playground now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🚀 Starting the CUA playground..."
  echo ""
  "$DEMO_DIR/start_demo.sh"
fi
