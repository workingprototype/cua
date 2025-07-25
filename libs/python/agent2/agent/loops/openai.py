"""
OpenAI computer-use-preview agent loop implementation using liteLLM
"""

import asyncio
import json
from typing import Dict, List, Any, AsyncGenerator, Union, Optional
import litellm

from ..decorators import agent_loop
from ..types import Messages, AgentResponse, Tools

def _map_computer_tool_to_openai(computer_tool: Any) -> Dict[str, Any]:
    """Map a computer tool to OpenAI's computer-use-preview tool schema"""
    return {
        "type": "computer_use_preview",
        "display_width": getattr(computer_tool, 'display_width', 1024),
        "display_height": getattr(computer_tool, 'display_height', 768),
        "environment": getattr(computer_tool, 'environment', "linux")  # mac, windows, linux, browser
    }


def _prepare_tools_for_openai(tool_schemas: List[Dict[str, Any]]) -> Tools:
    """Prepare tools for OpenAI API format"""
    openai_tools = []
    
    for schema in tool_schemas:
        if schema["type"] == "computer":
            # Map computer tool to OpenAI format
            openai_tools.append(_map_computer_tool_to_openai(schema["computer"]))
        elif schema["type"] == "function":
            # Function tools use OpenAI-compatible schema directly (liteLLM expects this format)
            # Schema should be: {type, name, description, parameters}
            openai_tools.append({ "type": "function", **schema["function"] })
    
    return openai_tools


@agent_loop(models=r".*computer-use-preview.*", priority=10)
async def openai_computer_use_loop(
    messages: Messages,
    model: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    max_retries: Optional[int] = None,
    stream: bool = False,
    computer_handler=None,
    use_prompt_caching: Optional[bool] = False,
    _on_api_start=None,
    _on_api_end=None,
    _on_usage=None,
    _on_screenshot=None,
    **kwargs
) -> Union[AgentResponse, AsyncGenerator[Dict[str, Any], None]]:
    """
    OpenAI computer-use-preview agent loop using liteLLM responses.
    
    Supports OpenAI's computer use preview models.
    """
    tools = tools or []
    
    # Prepare tools for OpenAI API
    openai_tools = _prepare_tools_for_openai(tools)

    # Prepare API call kwargs
    api_kwargs = {
        "model": model,
        "input": messages,
        "tools": openai_tools if openai_tools else None,
        "stream": stream,
        "reasoning": {"summary": "concise"},
        "truncation": "auto",
        "num_retries": max_retries,
        **kwargs
    }
    
    # Call API start hook
    if _on_api_start:
        await _on_api_start(api_kwargs)
    
    # Use liteLLM responses
    response = await litellm.aresponses(**api_kwargs)
    
    # Call API end hook
    if _on_api_end:
        await _on_api_end(api_kwargs, response)

    # Extract usage information
    response.usage = {
        **response.usage.model_dump(),
        "response_cost": response._hidden_params.get("response_cost", 0.0),
    }
    if _on_usage:
        await _on_usage(response.usage)
    
    return response
