## Developer Guide

### Project Structure

The project is organized as a monorepo with these main packages:
- `libs/core/` - Base package with telemetry support
- `libs/pylume/` - Python bindings for Lume
- `libs/computer/` - Core computer interaction library
- `libs/agent/` - AI agent library with multi-provider support
- `libs/som/` - Computer vision and NLP processing library (formerly omniparser)
- `libs/computer-server/` - Server implementation for computer control
- `libs/lume/` - Swift implementation for enhanced macOS integration

Each package has its own virtual environment and dependencies, managed through PDM.

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/trycua/cua.git
cd cua
```

2. Create a `.env.local` file in the root directory with your API keys:
```bash
# Required for Anthropic provider
ANTHROPIC_API_KEY=your_anthropic_key_here

# Required for OpenAI provider
OPENAI_API_KEY=your_openai_key_here
```

3. Run the build script to set up all packages:
```bash
./scripts/build.sh
```

This will:
- Create a virtual environment for the project
- Install all packages in development mode
- Set up the correct Python path
- Install development tools

4. Open the workspace in VSCode or Cursor:
```bash
# Using VSCode or Cursor
code .vscode/py.code-workspace

# For Lume (Swift) development
code .vscode/lume.code-workspace
```

Using the workspace file is strongly recommended as it:
- Sets up correct Python environments for each package
- Configures proper import paths
- Enables debugging configurations
- Maintains consistent settings across packages

### Cleanup and Reset

If you need to clean up the environment and start fresh:

```bash
./scripts/cleanup.sh
```

This will:
- Remove all virtual environments
- Clean Python cache files and directories
- Remove build artifacts
- Clean PDM-related files
- Reset environment configurations

### Package Virtual Environments

The build script creates a shared virtual environment for all packages. The workspace configuration automatically handles import paths with the correct Python path settings.

### Running Examples

The Python workspace includes launch configurations for all packages:

- "Run Computer Examples" - Runs computer examples
- "Run Computer API Server" - Runs the computer-server
- "Run Omni Agent Examples" - Runs agent examples
- "SOM" configurations - Various settings for running SOM

To run examples:
1. Open the workspace file (`.vscode/py.code-workspace`)
2. Press F5 or use the Run/Debug view
3. Select the desired configuration

The workspace also includes compound launch configurations:
- "Run Computer Examples + Server" - Runs both the Computer Examples and Server simultaneously

## Release and Publishing Process

This monorepo contains multiple Python packages that can be published to PyPI. The packages 
have dependencies on each other in the following order:

1. `pylume` - Base package for VM management
2. `cua-computer` - Computer control interface (depends on pylume)
3. `cua-som` - Parser for UI elements (independent, formerly omniparser)
4. `cua-agent` - AI agent (depends on cua-computer and optionally cua-som)
5. `computer-server` - Server component installed on the sandbox

#### Workflow Structure

The publishing process is managed by these GitHub workflow files:

- **Package-specific workflows**: 
  - `.github/workflows/publish-pylume.yml`
  - `.github/workflows/publish-computer.yml`
  - `.github/workflows/publish-som.yml`
  - `.github/workflows/publish-agent.yml`
  - `.github/workflows/publish-computer-server.yml`

- **Coordinator workflow**:
  - `.github/workflows/publish-all.yml` - Manages global releases and manual selections

### Version Management

#### Special Considerations for Pylume

The `pylume` package requires special handling as it incorporates the binary executable from the [lume repository](https://github.com/trycua/lume):

- When releasing `pylume`, ensure the version matches a corresponding release in the lume repository
- The workflow automatically downloads the matching lume binary and includes it in the pylume package
- If you need to release a new version of pylume, make sure to coordinate with a matching lume release

## Development Workspaces

This monorepo includes multiple VS Code workspace configurations to optimize the development experience based on which components you're working with:

### Available Workspace Files

- **[py.code-workspace](.vscode/py.code-workspace)**: For Python package development (Computer, Agent, SOM, etc.)
- **[lume.code-workspace](.vscode/lume.code-workspace)**: For Swift-based Lume development

To open a specific workspace:

```bash
# For Python development
code .vscode/py.code-workspace

# For Lume (Swift) development
code .vscode/lume.code-workspace
```