# Agent2 - Computer Use Agent

**agent2** is a clean Computer-Use framework with liteLLM integration for running agentic workflows on macOS and Linux.

## Key Features

- **Docstring-based Tools**: Define tools using standard Python docstrings (no decorators needed)
- **Regex Model Matching**: Agent loops can match models using regex patterns
- **liteLLM Integration**: All completions use liteLLM's `.responses()` method
- **Streaming Support**: Built-in streaming with asyncio.Queue and cancellation support
- **Computer Tools**: Direct integration with computer interface for clicks, typing, etc.
- **Custom Tools**: Easy Python function tools with comprehensive docstrings

## Install

```bash
pip install "cua-agent2[all]"

# or install specific providers
pip install "cua-agent2[anthropic]" # Anthropic support
pip install "cua-agent2[openai]"    # OpenAI computer-use-preview support
```

## Usage

### Define Tools

```python
# No imports needed for tools - just define functions with comprehensive docstrings

def read_file(location: str) -> str:
    """Read contents of a file
    
    Parameters
    ----------
    location : str
        Path to the file to read
        
    Returns
    -------
    str
        Contents of the file
    """
    with open(location, 'r') as f:
        return f.read()

def search_web(query: str) -> str:
    """Search the web for information
    
    Parameters
    ----------
    query : str
        Search query to look for
        
    Returns
    -------
    str
        Search results
    """
    return f"Search results for: {query}"
```

### Define Agent Loops

```python
from agent2 import agent_loop
from agent2.types import Messages

@agent_loop(models=r"claude-3.*", priority=10)
async def custom_claude_loop(messages: Messages, model: str, stream: bool = False, tools: Optional[List[Dict[str, Any]]] = None, **kwargs):
    """Custom agent loop for Claude models."""
    # Map computer tools to Claude format
    anthropic_tools = _prepare_tools_for_anthropic(tools)

    # Your custom logic here
    response = await litellm.aresponses(
        model=model,
        messages=messages,
        stream=stream,
        tools=anthropic_tools,
        **kwargs
    )

    if stream:
        async for chunk in response:
            yield chunk
    else:
        yield response

@agent_loop(models=r"omni+.*", priority=10)
async def custom_omni_loop(messages: Messages, model: str, stream: bool = False, tools: Optional[List[Dict[str, Any]]] = None, **kwargs):
    """Custom agent loop for Omni models."""
    # Map computer tools to Claude format
    omni_tools, som_prompt = _prepare_tools_for_omni(tools)

    # Your custom logic here
    response = await litellm.aresponses(
        model=model.replace("omni+", ""),
        messages=som_prompt,
        stream=stream,
        tools=omni_tools,
        **kwargs
    )

    if stream:
        async for chunk in response:
            yield chunk
    else:
        yield response
```

### Use ComputerAgent

```python
from agent2 import ComputerAgent
from computer import Computer

async def main():
    with Computer() as computer:
        agent = ComputerAgent(
            model="claude-3-5-sonnet-20241022",
            tools=[computer, read_file, search_web]
        )
        
        messages = [{"role": "user", "content": "Save a picture of a cat to my desktop."}]
        
        async for chunk in agent.run(messages, stream=True):
            print(chunk)

        omni_agent = ComputerAgent(
            model="omni+vertex_ai/gemini-pro",
            tools=[computer, read_file, search_web]
        )
        
        messages = [{"role": "user", "content": "Save a picture of a cat to my desktop."}]
        
        async for chunk in omni_agent.run(messages, stream=True):
            print(chunk)
```

## Supported Agent Loops

- **Anthropic**: Claude models with computer use
- **Computer-Use-Preview**: OpenAI's computer use preview models

## Architecture

- Agent loops are automatically selected based on model regex matching
- Computer tools are mapped to model-specific schemas
- All completions use `litellm.responses()` for consistency
- Streaming is handled with asyncio.Queue for cancellation support
