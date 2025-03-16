# Agent Package Structure

## Overview
The agent package provides a modular and extensible framework for AI-powered computer agents.

## Directory Structure
```
agent/
├── __init__.py           # Package exports
├── core/                 # Core functionality
│   ├── __init__.py
│   ├── computer_agent.py # Main entry point
│   └── factory.py        # Provider factory
├── base/                 # Base implementations
│   ├── __init__.py
│   ├── agent.py         # Base agent class
│   ├── core/            # Core components
│   │   ├── callbacks.py
│   │   ├── loop.py
│   │   └── messages.py
│   └── tools/           # Tool implementations
├── providers/           # Provider implementations
│   ├── __init__.py
│   ├── anthropic/      # Anthropic provider
│   │   ├── agent.py
│   │   ├── loop.py
│   │   └── tool_manager.py
│   └── omni/           # Omni provider
│       ├── agent.py
│       ├── loop.py
│       └── tool_manager.py
└── types/              # Type definitions
    ├── __init__.py
    ├── base.py        # Core types
    ├── messages.py    # Message types
    ├── tools.py       # Tool types
    └── providers/     # Provider-specific types
        ├── anthropic.py
        └── omni.py
```

## Key Components

### Core
- `computer_agent.py`: Main entry point for creating and using agents
- `factory.py`: Factory for creating provider-specific implementations

### Base
- `agent.py`: Base agent implementation with shared functionality
- `core/`: Core components used across providers
- `tools/`: Shared tool implementations

### Providers
Each provider follows the same structure:
- `agent.py`: Provider-specific agent implementation
- `loop.py`: Provider-specific message loop
- `tool_manager.py`: Tool management for provider

### Types
- `base.py`: Core type definitions
- `messages.py`: Message-related types
- `tools.py`: Tool-related types
- `providers/`: Provider-specific type definitions
