<div align="center">
<h1>
  <div class="image-wrapper" style="display: inline-block;">
    <picture>
      <source media="(prefers-color-scheme: dark)" alt="logo" height="150" srcset="../../img/logo_white.png" style="display: block; margin: auto;">
      <source media="(prefers-color-scheme: light)" alt="logo" height="150" srcset="../../img/logo_black.png" style="display: block; margin: auto;">
      <img alt="Shows my svg">
    </picture>
  </div>

  [![Swift 6](https://img.shields.io/badge/Swift_6-F54A2A?logo=swift&logoColor=white&labelColor=F54A2A)](#)
  [![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=F0F0F0)](#)
  [![Homebrew](https://img.shields.io/badge/Homebrew-FBB040?logo=homebrew&logoColor=fff)](#install)
  [![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?&logo=discord&logoColor=white)](https://discord.com/invite/mVnXXpdE85)
</h1>
</div>

**Lumier** provides a Docker-based interface for the `lume` CLI, allowing you to easily run macOS virtual machines inside a container with VNC access. It interacts directly with the `lume serve` API running on your host machine to manage VMs.

## Requirements

Before using Lumier, make sure you have:

1. Install [lume](https://github.com/trycua/cua/blob/main/libs/lume/README.md) on your host machine and ensure `lume serve` is running (typically on port 3000).
2. Docker installed on your host machine

## Usage (Direct Docker Commands - Recommended)

The primary way to use Lumier is directly through Docker commands. This gives you full control over the container environment.

Ensure `lume serve` is running on your host machine before starting the container.

```bash
# 1. Build the Docker image (if not already built or pulled)
docker build -t lumier:latest .

# 2. Run the container
docker run -it --rm \
    --name lumier-vm \
    -p 8006:8006 \
    -v $(pwd)/storage:/storage \
    -v $(pwd)/shared:/shared \
    -e VM_NAME=lumier-vm \
    -e VERSION=ghcr.io/trycua/macos-sequoia-cua:latest \
    -e CPU_CORES=4 \
    -e RAM_SIZE=8192 \
    -e HOST_STORAGE_PATH=$(pwd)/storage \
    -e HOST_SHARED_PATH=$(pwd)/shared \
    lumier:latest
```

Note that when using Docker directly, you're responsible for:
- Ensuring `lume serve` is running on the host.
- Building the Docker image (or pulling `trycua/lumier:latest`).
- Providing all necessary environment variables (`-e`) and volume mounts (`-v`).
- Mapping the VNC port (`-p 8006:8006`).

See "Available Environment Variables" below for customization options.

## Optional Helper Script (`lumier`)

For convenience, an optional helper script `lumier` is provided. It simplifies some common tasks like building the image and passing arguments to `docker run`.

### Installation (Optional, for `lumier` script)

If you want to use the `lumier` helper script system-wide, you can install it:

```bash
# Option 1: Install to your user's bin directory (recommended)
./install.sh

# Option 2: Install to a custom directory
./install.sh --install-dir=/usr/local/bin  # May require sudo

# Option 3: View installation options
./install.sh --help
```

### Using the Lumier Script

If you installed the script, you can use it as a wrapper around Docker commands:

```bash
# Show help for the script
lumier help

# Build the Docker image (optional, happens automatically on first run if not pulled)
lumier build

# Run a VM with default settings
lumier run -it --rm

# Run a VM with custom settings using Docker's -e flag
lumier run -it --rm \
    --name lumier1-vm \
    -p 8006:8006 \
    -v $(pwd)/storage1:/storage \
    -v $(pwd)/shared1:/shared \
    -e VERSION=ghcr.io/trycua/macos-sequoia-cua:latest \
    -e CPU_CORES=8 \
    -e RAM_SIZE=16GB
    
# Note:
# The lumier script will automatically:
# 1. Detect user-provided volume paths for /storage and /shared and use those exact paths
# 2. If not specified, default to ./storage and ./shared in the current directory
# 3. Pass the resolved paths to the container as HOST_STORAGE_PATH and HOST_SHARED_PATH
# 4. Create any non-existent directories automatically via Docker's volume mounting
# 5. Set the VM name from the container name
#
# You do NOT need to specify HOST_STORAGE_PATH or HOST_SHARED_PATH environment variables manually.
```

## Available Environment Variables

These variables can be set using Docker's `-e` flag:

- `VM_NAME`: Set the VM name (default: lumier)
- `VERSION`: Set the VM image (default: ghcr.io/trycua/macos-sequoia-vanilla:latest)
- `CPU_CORES`: Set the number of CPU cores (default: 4)
- `RAM_SIZE`: Set the memory size in MB (default: 8192)
- `DISPLAY`: Set the display resolution (default: 1024x768)
- `HOST_SHARED_PATH`: Path on the host to share with the VM
- `LUMIER_DEBUG`: Enable debug mode (set to 1)

## Project Structure

The project is organized as follows:

```
lumier/
├── Dockerfile            # Main Docker image definition
├── README.md             # This file
├── lumier                # Main CLI script
├── install.sh            # Installation script
├── src/                  # Source code
│   ├── bin/              # Executable scripts
│   │   ├── entry.sh      # Docker entrypoint
│   │   └── utils.sh      # Utility functions
│   ├── config/           # Configuration
│   │   └── constants.sh  # Shared constants
│   ├── hooks/            # Lifecycle hooks
│   │   └── on-logon.sh   # Run after VM boots
│   └── lib/              # Shared library code
│       └── vm.sh         # VM management functions
└── mount/                # Default shared directory
```

## VNC Access

When a VM is running, you can access it via VNC through:
http://localhost:8006/vnc.html

The password is displayed in the console output when the VM starts.