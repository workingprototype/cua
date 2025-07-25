"""
Anthropic hosted tools agent loop implementation using liteLLM
"""

import asyncio
import json
from typing import Dict, List, Any, AsyncGenerator, Union, Optional
import litellm
from litellm.responses.litellm_completion_transformation.transformation import LiteLLMCompletionResponsesConfig

from ..decorators import agent_loop
from ..types import Messages, AgentResponse, Tools
from ..responses import (
    make_reasoning_item,
    make_output_text_item,
    make_click_item,
    make_double_click_item,
    make_drag_item,
    make_keypress_item,
    make_move_item,
    make_scroll_item,
    make_type_item,
    make_wait_item,
    make_input_image_item,
    make_screenshot_item
)

# Model version mapping to tool version and beta flag
MODEL_TOOL_MAPPING = [
    # Claude 4 models
    {
        "pattern": r"claude-4|claude-opus-4|claude-sonnet-4",
        "tool_version": "computer_20250124",
        "beta_flag": "computer-use-2025-01-24"
    },
    # Claude 3.7 models
    {
        "pattern": r"claude-3\.?7|claude-3-7",
        "tool_version": "computer_20250124",
        "beta_flag": "computer-use-2025-01-24"
    },
    # Claude 3.5 models (fallback)
    {
        "pattern": r"claude-3\.?5|claude-3-5",
        "tool_version": "computer_20241022",
        "beta_flag": "computer-use-2024-10-22"
    }
]

def _get_tool_config_for_model(model: str) -> Dict[str, str]:
    """Get tool version and beta flag for the given model."""
    import re
    
    for mapping in MODEL_TOOL_MAPPING:
        if re.search(mapping["pattern"], model, re.IGNORECASE):
            return {
                "tool_version": mapping["tool_version"],
                "beta_flag": mapping["beta_flag"]
            }
    
    # Default to Claude 3.5 configuration
    return {
        "tool_version": "computer_20241022",
        "beta_flag": "computer-use-2024-10-22"
    }

def _map_computer_tool_to_anthropic(computer_tool: Any, tool_version: str) -> Dict[str, Any]:
    """Map a computer tool to Anthropic's hosted tool schema."""
    return {
        "type": tool_version,
        "function": {
            "name": "computer",
            "parameters": {
                "display_height_px": getattr(computer_tool, 'display_height', 768),
                "display_width_px": getattr(computer_tool, 'display_width', 1024),
                "display_number": getattr(computer_tool, 'display_number', 1),
            },
        },
    }

def _prepare_tools_for_anthropic(tool_schemas: List[Dict[str, Any]], model: str) -> Tools:
    """Prepare tools for Anthropic API format."""
    tool_config = _get_tool_config_for_model(model)
    anthropic_tools = []
    
    for schema in tool_schemas:
        if schema["type"] == "computer":
            # Map computer tool to Anthropic format
            anthropic_tools.append(_map_computer_tool_to_anthropic(
                schema["computer"], 
                tool_config["tool_version"]
            ))
        elif schema["type"] == "function":
            # Function tools - convert to Anthropic format
            function_schema = schema["function"]
            anthropic_tools.append({
                "type": "function",
                "function": {
                    "name": function_schema["name"],
                    "description": function_schema.get("description", ""),
                    "parameters": function_schema.get("parameters", {})
                }
            })
    
    return anthropic_tools

def _convert_responses_items_to_completion_messages(messages: Messages) -> List[Dict[str, Any]]:
    """Convert responses_items message format to liteLLM completion format."""
    completion_messages = []
    
    for message in messages:
        msg_type = message.get("type")
        role = message.get("role")
        
        # Handle user messages (both with and without explicit type)
        if role == "user" or msg_type == "user":
            content = message.get("content", "")
            if isinstance(content, list):
                # Multi-modal content - convert input_image to image format
                converted_content = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "input_image":
                        # Convert input_image to Anthropic image format
                        image_url = item.get("image_url", "")
                        if image_url and image_url != "[omitted]":
                            # Extract base64 data from data URL
                            if "," in image_url:
                                base64_data = image_url.split(",")[-1]
                            else:
                                base64_data = image_url
                            
                            converted_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_data
                                }
                            })
                    else:
                        # Keep other content types as-is
                        converted_content.append(item)
                
                completion_messages.append({
                    "role": "user",
                    "content": converted_content if converted_content else content
                })
            else:
                # Text content
                completion_messages.append({
                    "role": "user",
                    "content": content
                })
        
        # Handle assistant messages
        elif role == "assistant":
            content = message.get("content", [])
            if isinstance(content, str):
                content = [{ "type": "output_text", "text": content }]
            
            content = "\n".join(item.get("text", "") for item in content)
            completion_messages.append({
                "role": "assistant",
                "content": content
            })
        
        elif msg_type == "reasoning":
            # Reasoning becomes part of assistant message
            summary = message.get("summary", [])
            reasoning_text = ""
            
            if isinstance(summary, list) and summary:
                # Extract text from summary items
                for item in summary:
                    if isinstance(item, dict) and item.get("type") == "summary_text":
                        reasoning_text = item.get("text", "")
                        break
            else:
                # Fallback to direct reasoning field
                reasoning_text = message.get("reasoning", "")
            
            if reasoning_text:
                completion_messages.append({
                    "role": "assistant",
                    "content": reasoning_text
                })
        
        elif msg_type == "computer_call":
            # Computer call becomes tool use in assistant message
            action = message.get("action", {})
            action_type = action.get("type")
            call_id = message.get("call_id", "call_1")
            
            tool_use_content = []
            
            if action_type == "click":
                tool_use_content.append({
                    "type": "tool_use",
                    "id": call_id,
                    "name": "computer",
                    "input": {
                        "action": "click",
                        "coordinate": [action.get("x", 0), action.get("y", 0)]
                    }
                })
            elif action_type == "type":
                tool_use_content.append({
                    "type": "tool_use",
                    "id": call_id,
                    "name": "computer",
                    "input": {
                        "action": "type",
                        "text": action.get("text", "")
                    }
                })
            elif action_type == "key":
                tool_use_content.append({
                    "type": "tool_use",
                    "id": call_id,
                    "name": "computer",
                    "input": {
                        "action": "key",
                        "key": action.get("key", "")
                    }
                })
            elif action_type == "wait":
                tool_use_content.append({
                    "type": "tool_use",
                    "id": call_id,
                    "name": "computer",
                    "input": {
                        "action": "screenshot"
                    }
                })
            elif action_type == "screenshot":
                tool_use_content.append({
                    "type": "tool_use",
                    "id": call_id,
                    "name": "computer",
                    "input": {
                        "action": "screenshot"
                    }
                })
            
            # Convert tool_use_content to OpenAI tool_calls format
            openai_tool_calls = []
            for tool_use in tool_use_content:
                openai_tool_calls.append({
                    "id": tool_use["id"],
                    "type": "function",
                    "function": {
                        "name": tool_use["name"],
                        "arguments": json.dumps(tool_use["input"])
                    }
                })
            
            # If the last completion message is an assistant message, extend the tool_calls
            if completion_messages and completion_messages[-1].get("role") == "assistant":
                if "tool_calls" not in completion_messages[-1]:
                    completion_messages[-1]["tool_calls"] = []
                completion_messages[-1]["tool_calls"].extend(openai_tool_calls)
            else:
                # Create new assistant message with tool calls
                completion_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": openai_tool_calls
                })
        
        elif msg_type == "computer_call_output":
            # Computer call output becomes OpenAI function result
            output = message.get("output", {})
            call_id = message.get("call_id", "call_1")
            
            if output.get("type") == "input_image":
                # Screenshot result - convert to OpenAI format with image_url content
                image_url = output.get("image_url", "")
                completion_messages.append({
                    "role": "function",
                    "name": "computer",
                    "tool_call_id": call_id,
                    "content": [{
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }]
                })
            else:
                # Text result - convert to OpenAI format
                completion_messages.append({
                    "role": "function",
                    "name": "computer",
                    "tool_call_id": call_id,
                    "content": str(output)
                })
    
    return completion_messages

def _convert_completion_to_responses_items(response: Any) -> List[Dict[str, Any]]:
    """Convert liteLLM completion response to responses_items message format."""
    responses_items = []
    
    if not response or not hasattr(response, 'choices') or not response.choices:
        return responses_items
    
    choice = response.choices[0]
    message = choice.message
    
    # Handle text content
    if hasattr(message, 'content') and message.content:
        if isinstance(message.content, str):
            responses_items.append(make_output_text_item(message.content))
        elif isinstance(message.content, list):
            for content_item in message.content:
                if isinstance(content_item, dict):
                    if content_item.get("type") == "text":
                        responses_items.append(make_output_text_item(content_item.get("text", "")))
                    elif content_item.get("type") == "tool_use":
                        # Convert tool use to computer call
                        tool_input = content_item.get("input", {})
                        action_type = tool_input.get("action")
                        call_id = content_item.get("id")
                        
                        # Action reference:
                        # https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/computer-use-tool#available-actions
                        
                        # Basic actions (all versions)
                        if action_type == "screenshot":
                            responses_items.append(make_screenshot_item(call_id=call_id))
                        elif action_type == "left_click":
                            coordinate = tool_input.get("coordinate", [0, 0])
                            responses_items.append(make_click_item(
                                x=coordinate[0] if len(coordinate) > 0 else 0,
                                y=coordinate[1] if len(coordinate) > 1 else 0,
                                call_id=call_id
                            ))
                        elif action_type == "type":
                            responses_items.append(make_type_item(
                                text=tool_input.get("text", ""),
                                call_id=call_id
                            ))
                        elif action_type == "key":
                            responses_items.append(make_keypress_item(
                                key=tool_input.get("key", ""),
                                call_id=call_id
                            ))
                        elif action_type == "mouse_move":
                            # Mouse move - create a custom action item
                            coordinate = tool_input.get("coordinate", [0, 0])
                            responses_items.append({
                                "type": "computer_call",
                                "call_id": call_id,
                                "action": {
                                    "type": "mouse_move",
                                    "x": coordinate[0] if len(coordinate) > 0 else 0,
                                    "y": coordinate[1] if len(coordinate) > 1 else 0
                                }
                            })
                        
                        # Enhanced actions (computer_20250124) Available in Claude 4 and Claude Sonnet 3.7
                        elif action_type == "scroll":
                            coordinate = tool_input.get("coordinate", [0, 0])
                            responses_items.append(make_scroll_item(
                                x=coordinate[0] if len(coordinate) > 0 else 0,
                                y=coordinate[1] if len(coordinate) > 1 else 0,
                                direction=tool_input.get("scroll_direction", "down"),
                                amount=tool_input.get("scroll_amount", 3),
                                call_id=call_id
                            ))
                        elif action_type == "left_click_drag":
                            start_coord = tool_input.get("start_coordinate", [0, 0])
                            end_coord = tool_input.get("end_coordinate", [0, 0])
                            responses_items.append(make_drag_item(
                                start_x=start_coord[0] if len(start_coord) > 0 else 0,
                                start_y=start_coord[1] if len(start_coord) > 1 else 0,
                                end_x=end_coord[0] if len(end_coord) > 0 else 0,
                                end_y=end_coord[1] if len(end_coord) > 1 else 0,
                                call_id=call_id
                            ))
                        elif action_type == "right_click":
                            coordinate = tool_input.get("coordinate", [0, 0])
                            responses_items.append(make_click_item(
                                x=coordinate[0] if len(coordinate) > 0 else 0,
                                y=coordinate[1] if len(coordinate) > 1 else 0,
                                button="right",
                                call_id=call_id
                            ))
                        elif action_type == "middle_click":
                            coordinate = tool_input.get("coordinate", [0, 0])
                            responses_items.append(make_click_item(
                                x=coordinate[0] if len(coordinate) > 0 else 0,
                                y=coordinate[1] if len(coordinate) > 1 else 0,
                                button="wheel",
                                call_id=call_id
                            ))
                        elif action_type == "double_click":
                            coordinate = tool_input.get("coordinate", [0, 0])
                            responses_items.append(make_double_click_item(
                                x=coordinate[0] if len(coordinate) > 0 else 0,
                                y=coordinate[1] if len(coordinate) > 1 else 0,
                                call_id=call_id
                            ))
                        elif action_type == "triple_click":
                            # coordinate = tool_input.get("coordinate", [0, 0])
                            # responses_items.append({
                            #     "type": "computer_call",
                            #     "call_id": call_id,
                            #     "action": {
                            #         "type": "triple_click",
                            #         "x": coordinate[0] if len(coordinate) > 0 else 0,
                            #         "y": coordinate[1] if len(coordinate) > 1 else 0
                            #     }
                            # })
                            raise NotImplementedError("triple_click")
                        elif action_type == "left_mouse_down":
                            # coordinate = tool_input.get("coordinate", [0, 0])
                            # responses_items.append({
                            #     "type": "computer_call",
                            #     "call_id": call_id,
                            #     "action": {
                            #         "type": "mouse_down",
                            #         "button": "left",
                            #         "x": coordinate[0] if len(coordinate) > 0 else 0,
                            #         "y": coordinate[1] if len(coordinate) > 1 else 0
                            #     }
                            # })
                            raise NotImplementedError("left_mouse_down")
                        elif action_type == "left_mouse_up":
                            # coordinate = tool_input.get("coordinate", [0, 0])
                            # responses_items.append({
                            #     "type": "computer_call",
                            #     "call_id": call_id,
                            #     "action": {
                            #         "type": "mouse_up",
                            #         "button": "left",
                            #         "x": coordinate[0] if len(coordinate) > 0 else 0,
                            #         "y": coordinate[1] if len(coordinate) > 1 else 0
                            #     }
                            # })
                            raise NotImplementedError("left_mouse_up")
                        elif action_type == "hold_key":
                            # responses_items.append({
                            #     "type": "computer_call",
                            #     "call_id": call_id,
                            #     "action": {
                            #         "type": "key_hold",
                            #         "key": tool_input.get("key", "")
                            #     }
                            # })
                            raise NotImplementedError("hold_key")
                        elif action_type == "wait":
                            responses_items.append(make_wait_item(
                                call_id=call_id
                            ))
                        else:
                            raise ValueError(f"Unknown action type: {action_type}")
    
    # Handle tool calls (alternative format)
    if hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
            print(tool_call)
            if tool_call.function.name == "computer":
                try:
                    args = json.loads(tool_call.function.arguments)
                    action_type = args.get("action")
                    call_id = tool_call.id

                    # Basic actions (all versions)
                    if action_type == "screenshot":
                        responses_items.append(make_screenshot_item(
                            call_id=call_id
                        ))
                    elif action_type in ["click", "left_click"]:
                        coordinate = args.get("coordinate", [0, 0])
                        responses_items.append(make_click_item(
                            x=coordinate[0] if len(coordinate) > 0 else 0,
                            y=coordinate[1] if len(coordinate) > 1 else 0,
                            call_id=call_id
                        ))
                    elif action_type == "type":
                        responses_items.append(make_type_item(
                            text=args.get("text", ""),
                            call_id=call_id
                        ))
                    elif action_type == "key":
                        responses_items.append(make_keypress_item(
                            key=args.get("key", ""),
                            call_id=call_id
                        ))
                    elif action_type == "mouse_move":
                        coordinate = args.get("coordinate", [0, 0])
                        responses_items.append(make_move_item(
                            x=coordinate[0] if len(coordinate) > 0 else 0,
                            y=coordinate[1] if len(coordinate) > 1 else 0,
                            call_id=call_id
                        ))
                    
                    # Enhanced actions (computer_20250124) Available in Claude 4 and Claude Sonnet 3.7
                    elif action_type == "scroll":
                        coordinate = args.get("coordinate", [0, 0])
                        direction = args.get("scroll_direction", "down")
                        amount = args.get("scroll_amount", 3)
                        scroll_x = amount if direction == "left" else \
                                   -amount if direction == "right" else 0
                        scroll_y = amount if direction == "up" else \
                                   -amount if direction == "down" else 0
                        responses_items.append(make_scroll_item(
                            x=coordinate[0] if len(coordinate) > 0 else 0,
                            y=coordinate[1] if len(coordinate) > 1 else 0,
                            scroll_x=scroll_x,
                            scroll_y=scroll_y,
                            call_id=call_id
                        ))
                    elif action_type == "left_click_drag":
                        start_coord = args.get("start_coordinate", [0, 0])
                        end_coord = args.get("end_coordinate", [0, 0])
                        responses_items.append(make_drag_item(
                            start_x=start_coord[0] if len(start_coord) > 0 else 0,
                            start_y=start_coord[1] if len(start_coord) > 1 else 0,
                            end_x=end_coord[0] if len(end_coord) > 0 else 0,
                            end_y=end_coord[1] if len(end_coord) > 1 else 0,
                            call_id=call_id
                        ))
                    elif action_type == "right_click":
                        coordinate = args.get("coordinate", [0, 0])
                        responses_items.append(make_click_item(
                            x=coordinate[0] if len(coordinate) > 0 else 0,
                            y=coordinate[1] if len(coordinate) > 1 else 0,
                            button="right",
                            call_id=call_id
                        ))
                    elif action_type == "middle_click":
                        coordinate = args.get("coordinate", [0, 0])
                        responses_items.append(make_click_item(
                            x=coordinate[0] if len(coordinate) > 0 else 0,
                            y=coordinate[1] if len(coordinate) > 1 else 0,
                            button="scroll",
                            call_id=call_id
                        ))
                    elif action_type == "double_click":
                        coordinate = args.get("coordinate", [0, 0])
                        responses_items.append(make_double_click_item(
                            x=coordinate[0] if len(coordinate) > 0 else 0,
                            y=coordinate[1] if len(coordinate) > 1 else 0,
                            call_id=call_id
                        ))
                    elif action_type == "triple_click":
                        raise NotImplementedError("triple_click")
                    elif action_type == "left_mouse_down":
                        raise NotImplementedError("left_mouse_down")
                    elif action_type == "left_mouse_up":
                        raise NotImplementedError("left_mouse_up")
                    elif action_type == "hold_key":
                        raise NotImplementedError("hold_key")
                    elif action_type == "wait":
                        responses_items.append(make_wait_item(
                            call_id=call_id
                        ))
                except json.JSONDecodeError:
                    print("Failed to decode tool call arguments")
                    # Skip malformed tool calls
                    continue
    
    return responses_items

def _add_cache_control(completion_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add cache control to completion messages"""
    num_writes = 0
    for message in completion_messages:
        message["cache_control"] = { "type": "ephemeral" }
        num_writes += 1
        # Cache control has a maximum of 4 blocks
        if num_writes >= 4:
            break
    
    return completion_messages

def _combine_completion_messages(completion_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Combine completion messages with the same role"""
    if not completion_messages:
        return completion_messages
    
    combined_messages = []
    
    for message in completion_messages:
        # If this is the first message or role is different from last, add as new message
        if not combined_messages or combined_messages[-1]["role"] != message["role"]:
            # Ensure content is a list format and normalize text content
            new_message = message.copy()
            new_message["content"] = _normalize_content(message.get("content", ""))
            
            # Copy tool_calls if present
            if "tool_calls" in message:
                new_message["tool_calls"] = message["tool_calls"].copy()
            
            combined_messages.append(new_message)
        else:
            # Same role as previous message, combine them
            last_message = combined_messages[-1]
            
            # Combine content
            current_content = _normalize_content(message.get("content", ""))
            last_message["content"].extend(current_content)
            
            # Combine tool_calls if present
            if "tool_calls" in message:
                if "tool_calls" not in last_message:
                    last_message["tool_calls"] = []
                last_message["tool_calls"].extend(message["tool_calls"])
    
    # Post-process to merge consecutive text blocks
    for message in combined_messages:
        message["content"] = _merge_consecutive_text(message["content"])
    
    return combined_messages

def _normalize_content(content) -> List[Dict[str, Any]]:
    """Normalize content to list format"""
    if isinstance(content, str):
        if content.strip():  # Only add non-empty strings
            return [{"type": "text", "text": content}]
        else:
            return []
    elif isinstance(content, list):
        return content.copy()
    else:
        return []

def _merge_consecutive_text(content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge consecutive text blocks with newlines"""
    if not content_list:
        return content_list
    
    merged = []
    
    for item in content_list:
        if (item.get("type") == "text" and 
            merged and 
            merged[-1].get("type") == "text"):
            # Merge with previous text block
            merged[-1]["text"] += "\n" + item["text"]
        else:
            merged.append(item.copy())
    
    return merged

@agent_loop(models=r".*claude-.*", priority=5)
async def anthropic_hosted_tools_loop(
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
    Anthropic hosted tools agent loop using liteLLM acompletion.
    
    Supports Anthropic's computer use models with hosted tools.
    """
    tools = tools or []
    
    # Get tool configuration for this model
    tool_config = _get_tool_config_for_model(model)
    
    # Prepare tools for Anthropic API
    anthropic_tools = _prepare_tools_for_anthropic(tools, model)
    
    # Convert responses_items messages to completion format
    completion_messages = _convert_responses_items_to_completion_messages(messages)
    if use_prompt_caching:
        # First combine messages to reduce number of blocks
        completion_messages = _combine_completion_messages(completion_messages)
        # Then add cache control, anthropic requires explicit "cache_control" dicts
        completion_messages = _add_cache_control(completion_messages)
    
    # Prepare API call kwargs
    api_kwargs = {
        "model": model,
        "messages": completion_messages,
        "tools": anthropic_tools if anthropic_tools else None,
        "stream": stream,
        "num_retries": max_retries,
        **kwargs
    }
    
    # Add beta header for computer use
    if anthropic_tools:
        api_kwargs["headers"] = {
            "anthropic-beta": tool_config["beta_flag"]
        }
    
    # Call API start hook
    if _on_api_start:
        await _on_api_start(api_kwargs)
    
    # Use liteLLM acompletion
    response = await litellm.acompletion(**api_kwargs)
    
    # Call API end hook
    if _on_api_end:
        await _on_api_end(api_kwargs, response)
    
    # Convert response to responses_items format
    responses_items = _convert_completion_to_responses_items(response)

    # Extract usage information
    responses_usage = { 
        **LiteLLMCompletionResponsesConfig._transform_chat_completion_usage_to_responses_usage(response.usage).model_dump(),
        "response_cost": response._hidden_params.get("response_cost", 0.0),
    }
    if _on_usage:
        await _on_usage(responses_usage)

    # Create agent response
    agent_response = {
        "output": responses_items,
        "usage": responses_usage
    }
    
    return agent_response
