<div align="center">
<h1>
  <div class="image-wrapper" style="display: inline-block;">
    <picture>
      <source media="(prefers-color-scheme: dark)" alt="logo" height="150" srcset="../../img/logo_white.png" style="display: block; margin: auto;">
      <source media="(prefers-color-scheme: light)" alt="logo" height="150" srcset="../../img/logo_black.png" style="display: block; margin: auto;">
      <img alt="Shows my svg">
    </picture>
  </div>

  [![Python](https://img.shields.io/badge/Python-333333?logo=python&logoColor=white&labelColor=333333)](#)
  [![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=F0F0F0)](#)
  [![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?&logo=discord&logoColor=white)](https://discord.com/invite/mVnXXpdE85)
  [![PyPI](https://img.shields.io/pypi/v/cua-computer?color=333333)](https://pypi.org/project/cua-computer/)
</h1>
</div>

**cua-mcp-server** is a MCP server for the Computer-Use Agent (CUA), allowing you to run CUA through Claude Desktop or other MCP clients.
### Get started with Agent

## Installation

Install the package from PyPI:

```bash
pip install cua-mcp-server
```

This will install:
- The MCP server
- CUA agent and computer dependencies 
- An executable `cua-mcp-server` script in your PATH

## Claude Desktop Integration

To use with Claude Desktop, add an entry to your Claude Desktop configuration (`claude_desktop_config.json`, typically found in `~/.config/claude-desktop/`):

```json
"mcpServers": {
  "cua-agent": {
    "command": "cua-mcp-server",
    "args": [],
    "env": {
      "CUA_AGENT_LOOP": "OMNI",
      "CUA_MODEL_PROVIDER": "ANTHROPIC",
      "CUA_MODEL_NAME": "claude-3-opus-20240229",
      "ANTHROPIC_API_KEY": "your-api-key",
      "PYTHONIOENCODING": "utf-8"
    }
  }
}
```

For more information on MCP with Claude Desktop, see the [official MCP User Guide](https://modelcontextprotocol.io/quickstart/user).

## Cursor Integration

To use with Cursor, add an MCP configuration file in one of these locations:

- **Project-specific**: Create `.cursor/mcp.json` in your project directory
- **Global**: Create `~/.cursor/mcp.json` in your home directory

The configuration format is similar to Claude Desktop's:

```json
{
  "mcpServers": {
    "cua-agent": {
      "command": "cua-mcp-server",
      "args": [],
      "env": {
        "CUA_AGENT_LOOP": "OMNI",
        "CUA_MODEL_PROVIDER": "ANTHROPIC",
        "CUA_MODEL_NAME": "claude-3-7-sonnet-20250219",
        "ANTHROPIC_API_KEY": "your-api-key",
        "PYTHONPATH": "/path/to/your/cua/installation"
      }
    }
  }
}
```

After configuration, you can simply tell Cursor's Agent to perform computer tasks by explicitly mentioning the CUA agent, such as "Use the computer control tools to open Safari."

For more information on MCP with Cursor, see the [official Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol).

### First-time Usage Notes

**API Keys**: Ensure you have valid API keys:
   - Add your Anthropic API key, or other model provider API key in the Claude Desktop config (as shown above)
   - Or set it as an environment variable in your shell profile

## Configuration

The server is configured using environment variables (can be set in the Claude Desktop config):

| Variable | Description | Default |
|----------|-------------|---------|
| `CUA_AGENT_LOOP` | Agent loop to use (OPENAI, ANTHROPIC, OMNI) | OMNI |
| `CUA_MODEL_PROVIDER` | Model provider (ANTHROPIC, OPENAI, OLLAMA, OAICOMPAT) | ANTHROPIC |
| `CUA_MODEL_NAME` | Model name to use | None (provider default) |
| `CUA_PROVIDER_BASE_URL` | Base URL for provider API | None |
| `CUA_MAX_IMAGES` | Maximum number of images to keep in context | 3 |

## Available Tools

The MCP server exposes the following tools to Claude:

1. `run_cua_task` - Run a single Computer-Use Agent task with the given instruction
2. `run_multi_cua_tasks` - Run multiple tasks in sequence

## Usage

Once configured, you can simply ask Claude to perform computer tasks:

- "Open Chrome and go to github.com"
- "Create a folder called 'Projects' on my desktop"
- "Find all PDFs in my Downloads folder"
- "Take a screenshot and highlight the error message"

Claude will automatically use your CUA agent to perform these tasks.