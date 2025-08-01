"""
GTA1 agent loop implementation for click prediction using litellm.acompletion
Paper: https://arxiv.org/pdf/2507.05791
Code: https://github.com/Yan98/GTA1
"""

import asyncio
import json
import re
import base64
from typing import Dict, List, Any, AsyncGenerator, Union, Optional, Tuple
from io import BytesIO
import uuid
from PIL import Image
import litellm
import math

from ..decorators import register_agent
from ..types import Messages, AgentResponse, Tools, AgentCapability
from ..loops.base import AsyncAgentConfig

SYSTEM_PROMPT = '''
You are an expert UI element locator. Given a GUI image and a user's element description, provide the coordinates of the specified element as a single (x,y) point. The image resolution is height {height} and width {width}. For elements with area, return the center point.

Output the coordinate pair exactly:
(x,y)
'''.strip()

# Global dictionary to map coordinates to descriptions
xy2desc: Dict[Tuple[float, float], str] = {}

GTA1_TOOL_SCHEMA = {
  "type": "function",
  "name": "computer",
  "description": "Control a computer by taking screenshots and interacting with UI elements. This tool uses element descriptions to locate and interact with UI elements on the screen (e.g., 'red submit button', 'search text field', 'hamburger menu icon', 'close button in top right corner').",
  "parameters": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": [
          "screenshot",
          "click",
          "double_click",
          "drag",
          "type",
          "keypress",
          "scroll",
          "move",
          "wait",
          "get_current_url",
          "get_dimensions",
          "get_environment"
        ],
        "description": "The action to perform"
      },
      "element_description": {
        "type": "string",
        "description": "Description of the element to interact with (required for click, double_click, move, scroll actions, and as start/end for drag)"
      },
      "start_element_description": {
        "type": "string",
        "description": "Description of the element to start dragging from (required for drag action)"
      },
      "end_element_description": {
        "type": "string",
        "description": "Description of the element to drag to (required for drag action)"
      },
      "text": {
        "type": "string",
        "description": "The text to type (required for type action)"
      },
      "keys": {
        "type": "string",
        "description": "Key combination to press (required for keypress action). Single key for individual key press, multiple keys for combinations (e.g., 'ctrl+c')"
      },
      "button": {
        "type": "string",
        "description": "The mouse button to use for click action (left, right, wheel, back, forward) Default: left",
      },
      "scroll_x": {
        "type": "integer",
        "description": "Horizontal scroll amount for scroll action (positive for right, negative for left)",
      },
      "scroll_y": {
        "type": "integer",
        "description": "Vertical scroll amount for scroll action (positive for down, negative for up)",
      },
    },
    "required": [
      "action"
    ]
  }
}

def extract_coordinates(raw_string: str) -> Tuple[float, float]:
    """Extract coordinates from model output."""
    try:
        matches = re.findall(r"\((-?\d*\.?\d+),\s*(-?\d*\.?\d+)\)", raw_string)
        return tuple(map(float, matches[0])) # type: ignore
    except:
        return (0.0, 0.0)

def get_last_computer_call_output(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Get the last computer_call_output message from a messages list.
    
    Args:
        messages: List of messages to search through
        
    Returns:
        The last computer_call_output message dict, or None if not found
    """
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("type") == "computer_call_output":
            return message
    return None

def _prepare_tools_for_gta1(tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare tools for GTA1 API format"""
    gta1_tools = []
    
    for schema in tool_schemas:
        if schema["type"] == "computer":
            gta1_tools.append(GTA1_TOOL_SCHEMA)
        else:
            gta1_tools.append(schema)
    
    return gta1_tools

async def replace_function_with_computer_call_gta1(item: Dict[str, Any], agent_instance) -> List[Dict[str, Any]]:
    """Convert function_call to computer_call format using GTA1 click prediction."""
    global xy2desc
    item_type = item.get("type")

    async def _get_xy(element_description: Optional[str], last_image_b64: str) -> Union[Tuple[float, float], Tuple[None, None]]:
        if element_description is None:
            return (None, None)
        # Use self.predict_click to get coordinates from description
        coords = await agent_instance.predict_click(
            model=agent_instance.current_model,
            image_b64=last_image_b64,
            instruction=element_description
        )
        if coords:
            # Store the mapping from coordinates to description
            xy2desc[coords] = element_description
            return coords
        return (None, None)

    if item_type == "function_call":
        fn_name = item.get("name")
        fn_args = json.loads(item.get("arguments", "{}"))

        item_id = item.get("id")
        call_id = item.get("call_id")
        
        if fn_name == "computer":
            action = fn_args.get("action")
            element_description = fn_args.get("element_description")
            start_element_description = fn_args.get("start_element_description")
            end_element_description = fn_args.get("end_element_description")
            text = fn_args.get("text")
            keys = fn_args.get("keys")
            button = fn_args.get("button")
            scroll_x = fn_args.get("scroll_x")
            scroll_y = fn_args.get("scroll_y")

            # Get the last computer output image for click prediction
            last_image_b64 = agent_instance.last_screenshot_b64 or ""

            x, y = await _get_xy(element_description, last_image_b64)
            start_x, start_y = await _get_xy(start_element_description, last_image_b64)
            end_x, end_y = await _get_xy(end_element_description, last_image_b64)

            action_args = {
                "type": action,
                "x": x,
                "y": y,
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "text": text,
                "keys": keys,
                "button": button,
                "scroll_x": scroll_x,
                "scroll_y": scroll_y
            }
            # Remove None values to keep the JSON clean
            action_args = {k: v for k, v in action_args.items() if v is not None}

            return [{
                "type": "computer_call",
                "action": action_args,
                "id": item_id,
                "call_id": call_id,
                "status": "completed"
            }]

    return [item]

async def replace_computer_call_with_function_gta1(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert computer_call back to function_call format using descriptions.
    Only READS from the global xy2desc dictionary.
    
    Args:
        item: The item to convert
    """
    global xy2desc
    item_type = item.get("type")

    def _get_element_description(x: Optional[float], y: Optional[float]) -> Optional[str]:
        """Get element description from coordinates, return None if coordinates are None"""
        if x is None or y is None:
            return None
        return xy2desc.get((x, y))

    if item_type == "computer_call":
        action_data = item.get("action", {})
        
        # Extract coordinates and convert back to element descriptions
        element_description = _get_element_description(action_data.get("x"), action_data.get("y"))
        start_element_description = _get_element_description(action_data.get("start_x"), action_data.get("start_y"))
        end_element_description = _get_element_description(action_data.get("end_x"), action_data.get("end_y"))
        
        # Build function arguments
        fn_args = {
            "action": action_data.get("type"),
            "element_description": element_description,
            "start_element_description": start_element_description,
            "end_element_description": end_element_description,
            "text": action_data.get("text"),
            "keys": action_data.get("keys"),
            "button": action_data.get("button"),
            "scroll_x": action_data.get("scroll_x"),
            "scroll_y": action_data.get("scroll_y")
        }
        
        # Remove None values to keep the JSON clean
        fn_args = {k: v for k, v in fn_args.items() if v is not None}
        
        return [{
            "type": "function_call",
            "name": "computer",
            "arguments": json.dumps(fn_args),
            "id": item.get("id"),
            "call_id": item.get("call_id"),
            "status": "completed",
            # Fall back to string representation
            # "content": f"Used tool: {action_data.get('type')}({json.dumps(fn_args)})"
        }]
    
    elif item_type == "computer_call_output":
        # Simple conversion: computer_call_output -> function_call_output (text only), user message (image)
        return [
            {
                "type": "function_call_output",
                "call_id": item.get("call_id"),
                "output": "Tool executed successfully. See the current computer screenshot below, if nothing has changed yet then you may need to wait before trying again.",
                "id": item.get("id"),
                "status": "completed"
            }, {
                "role": "user",
                "content": [item.get("output")]
            }
        ]

    return [item]

def smart_resize(height: int, width: int, factor: int = 28, min_pixels: int = 3136, max_pixels: int = 8847360) -> Tuple[int, int]:
    """Smart resize function similar to qwen_vl_utils."""
    # Calculate the total pixels
    total_pixels = height * width
    
    # If already within bounds, return original dimensions
    if min_pixels <= total_pixels <= max_pixels:
        # Round to nearest factor
        new_height = (height // factor) * factor
        new_width = (width // factor) * factor
        return new_height, new_width
    
    # Calculate scaling factor
    if total_pixels > max_pixels:
        scale = (max_pixels / total_pixels) ** 0.5
    else:
        scale = (min_pixels / total_pixels) ** 0.5
    
    # Apply scaling
    new_height = int(height * scale)
    new_width = int(width * scale)
    
    # Round to nearest factor
    new_height = (new_height // factor) * factor
    new_width = (new_width // factor) * factor
    
    # Ensure minimum size
    new_height = max(new_height, factor)
    new_width = max(new_width, factor)
    
    return new_height, new_width

@register_agent(models=r".*GTA1.*", priority=10)
class GTA1Config(AsyncAgentConfig):
    """GTA1 agent configuration implementing AsyncAgentConfig protocol for click prediction."""
    
    def __init__(self):
        self.current_model = None
        self.last_screenshot_b64 = None
    
    async def predict_step(
        self,
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
    ) -> Dict[str, Any]:
        """
        GTA1 agent loop implementation using liteLLM responses with element descriptions.
        
        Follows the 4-step process:
        1. Prepare tools
        2. Replace computer calls with function calls (using descriptions)
        3. API call
        4. Replace function calls with computer calls (using predict_click)
        """
        models = model.split("+")
        if len(models) != 2:
            raise ValueError("GTA1 model must be in the format <gta1_model_name>+<planning_model_name> to be used in an agent loop")
        
        gta1_model, llm_model = models
        self.current_model = gta1_model
        
        tools = tools or []
        
        # Step 0: Prepare tools
        gta1_tools = _prepare_tools_for_gta1(tools)
        
        # Get last computer_call_output for screenshot reference
        # Convert messages to list of dicts first
        message_list = []
        for message in messages:
            if not isinstance(message, dict):
                message_list.append(message.__dict__)
            else:
                message_list.append(message)
        
        last_computer_call_output = get_last_computer_call_output(message_list)
        if last_computer_call_output:
            image_url = last_computer_call_output.get("output", {}).get("image_url", "")
            if image_url.startswith("data:image/"):
                self.last_screenshot_b64 = image_url.split(",")[-1]
            else:
                self.last_screenshot_b64 = image_url

        # Step 1: If there's no screenshot, simulate the model calling the screenshot function
        pre_output = []
        if not self.last_screenshot_b64 and computer_handler:
            screenshot_base64 = await computer_handler.screenshot()
            if _on_screenshot:
                await _on_screenshot(screenshot_base64, "screenshot_initial")

            call_id = uuid.uuid4().hex
            pre_output += [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Taking a screenshot to see the current computer screen."
                        }
                    ]
                },
                {
                    "action": {
                        "type": "screenshot"
                    },
                    "call_id": call_id,
                    "status": "completed",
                    "type": "computer_call"
                },
                {
                    "type": "computer_call_output",
                    "call_id": call_id,
                    "output": {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{screenshot_base64}"
                    }
                },
            ]
        
            # Update the last screenshot for future use
            self.last_screenshot_b64 = screenshot_base64
    
        message_list += pre_output
        
        # Step 2: Replace computer calls with function calls (using descriptions)
        new_messages = []
        for message in message_list:
            new_messages += await replace_computer_call_with_function_gta1(message)
        messages = new_messages
        
        # Step 3: API call
        api_kwargs = {
            "model": llm_model,
            "input": messages,
            "tools": gta1_tools if gta1_tools else None,
            "stream": stream,
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
            **response.usage.model_dump(), # type: ignore
            "response_cost": response._hidden_params.get("response_cost", 0.0), # type: ignore
        }
        if _on_usage:
            await _on_usage(usage)
        
        # Step 4: Replace function calls with computer calls (using predict_click)
        new_output = []
        for i in range(len(response.output)): # type: ignore
            output_item = response.output[i] # type: ignore
            # Convert to dict if it has model_dump method, otherwise use as-is
            if hasattr(output_item, 'model_dump'):
                item_dict = output_item.model_dump() # type: ignore
            else:
                item_dict = output_item # type: ignore
            new_output += await replace_function_with_computer_call_gta1(item_dict, self) # type: ignore
        
        return {
            "output": pre_output + new_output,
            "usage": usage
        }
    
    async def predict_click(
        self,
        model: str,
        image_b64: str,
        instruction: str,
        **kwargs
    ) -> Optional[Tuple[float, float]]:
        """
        Predict click coordinates using GTA1 model via litellm.acompletion.
        
        Args:
            model: The GTA1 model name
            image_b64: Base64 encoded image
            instruction: Instruction for where to click
            
        Returns:
            Tuple of (x, y) coordinates or None if prediction fails
        """
        # Decode base64 image
        image_data = base64.b64decode(image_b64)
        image = Image.open(BytesIO(image_data))
        width, height = image.width, image.height
        
        # Smart resize the image (similar to qwen_vl_utils)
        resized_height, resized_width = smart_resize(
            height, width, 
            factor=28,  # Default factor for Qwen models
            min_pixels=3136,
            max_pixels=4096 * 2160
        )
        resized_image = image.resize((resized_width, resized_height))
        scale_x, scale_y = width / resized_width, height / resized_height
        
        # Convert resized image back to base64
        buffered = BytesIO()
        resized_image.save(buffered, format="PNG")
        resized_image_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Prepare system and user messages
        system_message = {
            "role": "system",
            "content": SYSTEM_PROMPT.format(height=resized_height, width=resized_width)
        }
        
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{resized_image_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": instruction
                }
            ]
        }
        
        # Prepare API call kwargs
        api_kwargs = {
            "model": model,
            "messages": [system_message, user_message],
            "max_tokens": 32,
            "temperature": 0.0,
            **kwargs
        }
        
        # Use liteLLM acompletion
        response = await litellm.acompletion(**api_kwargs)
        
        # Extract response text
        output_text = response.choices[0].message.content
        
        # Extract and rescale coordinates
        pred_x, pred_y = extract_coordinates(output_text)
        pred_x *= scale_x
        pred_y *= scale_y
        
        return (math.floor(pred_x), math.floor(pred_y))
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Return the capabilities supported by this agent."""
        return ["click", "step"]
