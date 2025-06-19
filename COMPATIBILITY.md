# C/ua Compatibility Matrix

## Table of Contents
- [Host OS Compatibility](#host-os-compatibility)
  - [macOS Host](#macos-host)
  - [Ubuntu/Linux Host](#ubuntulinux-host)
  - [Windows Host](#windows-host)
- [VM Emulation Support](#vm-emulation-support)
- [Installation Method Details](#installation-method-details)

---

## Host OS Compatibility

*This section shows compatibility based on your **host operating system** (the OS you're running C/ua on).*

### macOS Host

| Installation Method | Requirements | Lume | Cloud | Notes |
|-------------------|-------------|------|-------|-------|
| **playground-docker.sh** | Docker Desktop | ✅ Full | ✅ Full | Recommended for quick setup |
| **Dev Container** | VS Code/WindSurf + Docker | ✅ Full | ✅ Full | Best for development |
| **PyPI packages** | Python 3.12+ | ✅ Full | ✅ Full | Most flexible |

**macOS Host Requirements:**
- macOS 15+ (Sequoia) for local VM support
- Apple Silicon (M1/M2/M3/M4) recommended for best performance
- Docker Desktop for containerized installations

---

### Ubuntu/Linux Host

| Installation Method | Requirements | Lume | Cloud | Notes |
|-------------------|-------------|------|-------|-------|
| **playground-docker.sh** | Docker Engine | ✅ Full | ✅ Full | Recommended for quick setup |
| **Dev Container** | VS Code/WindSurf + Docker | ✅ Full | ✅ Full | Best for development |
| **PyPI packages** | Python 3.12+ | ✅ Full | ✅ Full | Most flexible |

**Ubuntu/Linux Host Requirements:**
- Ubuntu 20.04+ or equivalent Linux distribution
- Docker Engine or Docker Desktop
- Python 3.12+ for PyPI installation

---

### Windows Host

| Installation Method | Requirements | Lume | Winsandbox | Cloud | Notes |
|-------------------|-------------|------|------------|-------|-------|
| **playground-docker.sh** | Docker Desktop + WSL2 | ❌ Not supported | ❌ Not supported | ✅ Full | Requires WSL2 |
| **Dev Container** | VS Code/WindSurf + Docker + WSL2 | ❌ Not supported | ❌ Not supported | ✅ Full | Requires WSL2 |
| **PyPI packages** | Python 3.12+ | ❌ Not supported | ✅ Limited | ✅ Full | WSL for .sh scripts |

**Windows Host Requirements:**
- Windows 10/11 with WSL2 enabled for shell script execution
- Docker Desktop with WSL2 backend
- Windows Sandbox feature enabled (for Winsandbox support)
- Python 3.12+ installed in WSL2 or Windows
- **Note**: Lume CLI is not available on Windows - use Cloud or Winsandbox providers

---

## VM Emulation Support

*This section shows which **virtual machine operating systems** each provider can emulate.*

| Provider | macOS VM | Ubuntu/Linux VM | Windows VM | Notes |
|----------|----------|-----------------|------------|-------|
| **Lume** | ✅ Full support | ⚠️ Limited support | ⚠️ Limited support | macOS: native; Ubuntu/Linux/Windows: need custom image |
| **Cloud** | 🚧 Coming soon | ✅ Full support | 🚧 Coming soon | Currently Ubuntu only, macOS/Windows in development |
| **Winsandbox** | ❌ Not supported | ❌ Not supported | ✅ Windows only | Windows Sandbox environments only |

### VM Emulation Details

#### Lume VM Support
- **macOS VMs**: ✅ Full native support with official images
- **Ubuntu/Linux VMs**: ⚠️ Limited support - requires custom image creation
- **Windows VMs**: ⚠️ Limited support - requires custom image creation

#### Cloud VM Support  
- **Ubuntu/Linux VMs**: ✅ Full support with managed cloud instances
- **macOS VMs**: 🚧 Coming soon - in development
- **Windows VMs**: 🚧 Coming soon - in development

#### Windows Sandbox VM Support
- **Windows VMs**: ✅ Full support for Windows Sandbox environments
- **macOS/Linux VMs**: ❌ Not supported - Windows Sandbox only runs Windows

---

## Installation Method Details

### playground-docker.sh
- **Containerized setup** using Docker
- Handles all dependencies automatically
- Requires Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- **Windows note**: Must run in WSL2 environment

### Dev Container
- **Development-focused** setup for contributors
- Integrates with VS Code and WindSurf IDEs
- Provides consistent development environment
- **Windows note**: Requires WSL2 backend for Docker

### PyPI packages
- **Manual installation** via pip
- Most flexible installation method
- Allows custom configurations and integrations
- **Windows note**: Shell scripts require WSL2, but Python packages work natively

---

## Legend

- ✅ **Full support**: All features work natively without limitations
- ⚠️ **Partial support**: Requires additional setup (e.g., WSL2) or has limitations
- ❌ **Not supported**: Feature/provider combination is not available
- 🚧 **Coming soon**: Feature/provider combination is in development
