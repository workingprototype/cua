# Unified ComputerAgent

The `ComputerAgent` class provides a unified implementation that consolidates the previously separate agent implementations (AnthropicComputerAgent and OmniComputerAgent) into a single, configurable class.

## Features

- **Multiple Loop Types**: Switch between different agentic loop implementations using the `loop_type` parameter (Anthropic or Omni).
- **Provider Support**: Use different AI providers (OpenAI, Anthropic, etc.) with the appropriate loop.
- **Trajectory Saving**: Control whether to save screenshots and logs with the `save_trajectory` parameter.
- **Consistent Interface**: Maintains a consistent interface regardless of the underlying loop implementation.

## API Key Requirements

To use the ComputerAgent, you'll need API keys for the providers you want to use:

- For **OpenAI**: Set the `OPENAI_API_KEY` environment variable or pass it directly as `api_key`.
- For **Anthropic**: Set the `ANTHROPIC_API_KEY` environment variable or pass it directly as `api_key`.
- For **Groq**: Set the `GROQ_API_KEY` environment variable or pass it directly as `api_key`.

You can set environment variables in several ways:

```bash
# In your terminal before running the code
export OPENAI_API_KEY=your_api_key_here

# Or in a .env file
OPENAI_API_KEY=your_api_key_here
```

## Usage

Here's how to use the unified ComputerAgent:

```python
from agent.core.agent import ComputerAgent
from agent.types.base import AgenticLoop
from agent.providers.omni.types import LLMProvider
from computer import Computer

# Create a Computer instance
computer = Computer()

# Create an agent with the OMNI loop and OpenAI provider
agent = ComputerAgent(
    computer=computer,
    loop_type=AgenticLoop.OMNI,
    provider=LLMProvider.OPENAI,
    model="gpt-4o",
    api_key="your_api_key_here",  # Can also use OPENAI_API_KEY environment variable
    save_trajectory=True,
    only_n_most_recent_images=5
)

# Create an agent with the ANTHROPIC loop
agent = ComputerAgent(
    computer=computer,
    loop_type=AgenticLoop.ANTHROPIC,
    model="claude-3-7-sonnet-20250219",
    api_key="your_api_key_here",  # Can also use ANTHROPIC_API_KEY environment variable
    save_trajectory=True,
    only_n_most_recent_images=5
)

# Use the agent
async with agent:
    async for result in agent.run("Your task description here"):
        # Process the result
        title = result["metadata"].get("title", "Screen Analysis")
        content = result["content"]
        print(f"\n{title}")
        print(content)
```

## Parameters

- `computer`: Computer instance to control
- `loop_type`: The type of loop to use (AgenticLoop.ANTHROPIC or AgenticLoop.OMNI)
- `provider`: AI provider to use (required for Omni loop)
- `api_key`: Optional API key (will use environment variable if not provided)
- `model`: Optional model name (will use provider default if not specified)
- `save_trajectory`: Whether to save screenshots and logs
- `only_n_most_recent_images`: Only keep N most recent images
- `max_retries`: Maximum number of retry attempts

## Directory Structure

When `save_trajectory` is enabled, the agent will create the following directory structure:

```
experiments/
  ├── screenshots/   # Screenshots captured during agent execution
  └── logs/          # API call logs and other logging information
```

## Extending with New Loop Types

To add a new loop type:

1. Implement a new loop class
2. Add a new value to the `AgenticLoop` enum
3. Update the `_initialize_loop` method in `ComputerAgent` to handle the new loop type 