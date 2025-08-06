"""
OpenAI computer-use-preview agent loop implementation using liteLLM
"""

import asyncio
import base64
import json
from io import BytesIO
from typing import Dict, List, Any, AsyncGenerator, Union, Optional, Tuple
import litellm
from PIL import Image

from ..decorators import register_agent
from ..types import Messages, AgentResponse, Tools, AgentCapability

async def _map_computer_tool_to_openai(computer_handler: Any) -> Dict[str, Any]:
    """Map a computer tool to OpenAI's computer-use-preview tool schema"""
    # Get dimensions from the computer handler
    try:
        width, height = await computer_handler.get_dimensions()
    except Exception:
        # Fallback to default dimensions if method fails
        width, height = 1024, 768
    
    # Get environment from the computer handler
    try:
        environment = await computer_handler.get_environment()
    except Exception:
        # Fallback to default environment if method fails
        environment = "linux"
    
    return {
        "type": "computer_use_preview",
        "display_width": width,
        "display_height": height,
        "environment": environment  # mac, windows, linux, browser
    }


async def _prepare_tools_for_openai(tool_schemas: List[Dict[str, Any]]) -> Tools:
    """Prepare tools for OpenAI API format"""
    openai_tools = []
    
    for schema in tool_schemas:
        if schema["type"] == "computer":
            # Map computer tool to OpenAI format
            computer_tool = await _map_computer_tool_to_openai(schema["computer"])
            openai_tools.append(computer_tool)
        elif schema["type"] == "function":
            # Function tools use OpenAI-compatible schema directly (liteLLM expects this format)
            # Schema should be: {type, name, description, parameters}
            openai_tools.append({ "type": "function", **schema["function"] })
    
    return openai_tools


@register_agent(models=r".*computer-use-preview.*")
class OpenAIComputerUseConfig:
    """
    OpenAI computer-use-preview agent configuration using liteLLM responses.
    
    Supports OpenAI's computer use preview models.
    """
    
    async def predict_step(
        self,
        messages: List[Dict[str, Any]],
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
    ) -> Dict[str, Any]:
        """
        Predict the next step based on input items.
        
        Args:
            messages: Input items following Responses format
            model: Model name to use
            tools: Optional list of tool schemas
            max_retries: Maximum number of retries
            stream: Whether to stream responses
            computer_handler: Computer handler instance
            _on_api_start: Callback for API start
            _on_api_end: Callback for API end
            _on_usage: Callback for usage tracking
            _on_screenshot: Callback for screenshot events
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with "output" (output items) and "usage" array
        """
        tools = tools or []
        
        # Prepare tools for OpenAI API
        openai_tools = await _prepare_tools_for_openai(tools)

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
        usage = {
            **response.usage.model_dump(),
            "response_cost": response._hidden_params.get("response_cost", 0.0),
        }
        if _on_usage:
            await _on_usage(usage)

        # Return in the expected format
        output_dict = response.model_dump()
        output_dict["usage"] = usage
        return output_dict
    
    async def predict_click(
        self,
        model: str,
        image_b64: str,
        instruction: str
    ) -> Optional[Tuple[int, int]]:
        """
        Predict click coordinates based on image and instruction.
        
        Uses OpenAI computer-use-preview with manually constructed input items
        and a prompt that instructs the agent to only output clicks.
        
        Args:
            model: Model name to use
            image_b64: Base64 encoded image
            instruction: Instruction for where to click
            
        Returns:
            Tuple of (x, y) coordinates or None if prediction fails
        """
        # TODO: use computer tool to get dimensions + environment
        # Manually construct input items with image and click instruction
        input_items = [
            {
                "role": "user", 
                "content": f"You are a UI grounding expert. Look at the image and {instruction}. Output ONLY a click action on the target element. No explanations, confirmations, or additional text."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_b64}"
                    }
                ]
            }
        ]
        
        # Get image dimensions from base64 data
        try:
            image_data = base64.b64decode(image_b64)
            image = Image.open(BytesIO(image_data))
            display_width, display_height = image.size
        except Exception:
            # Fallback to default dimensions if image parsing fails
            display_width, display_height = 1024, 768
        
        # Prepare computer tool for click actions
        computer_tool = {
            "type": "computer_use_preview",
            "display_width": display_width,
            "display_height": display_height,
            "environment": "windows"
        }
        
        # Prepare API call kwargs
        api_kwargs = {
            "model": model,
            "input": input_items,
            "tools": [computer_tool],
            "stream": False,
            "reasoning": {"summary": "concise"},
            "truncation": "auto",
            "max_tokens": 100  # Keep response short for click prediction
        }
        
        # Use liteLLM responses
        response = await litellm.aresponses(**api_kwargs)
        
        # Extract click coordinates from response output
        output_dict = response.model_dump()
        output_items = output_dict.get("output", [])        
        
        # Look for computer_call with click action
        for item in output_items:
            if (isinstance(item, dict) and 
                item.get("type") == "computer_call" and
                isinstance(item.get("action"), dict)):
                
                action = item["action"]
                if action.get("type") == "click":
                    x = action.get("x")
                    y = action.get("y")
                    if x is not None and y is not None:
                        return (int(x), int(y))
        
        return None
    
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get list of capabilities supported by this agent config.
        
        Returns:
            List of capability strings
        """
        return ["click", "step"]
