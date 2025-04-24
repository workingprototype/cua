"""Utility functions for the UI-TARS provider."""

import logging
import base64
import re
from typing import Any, Dict, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)


def add_box_token(input_string: str) -> str:
    """Add box tokens to the coordinates in the model response.
    
    Args:
        input_string: Raw model response
        
    Returns:
        String with box tokens added
    """
    if "Action: " not in input_string or "start_box=" not in input_string:
        return input_string
        
    suffix = input_string.split("Action: ")[0] + "Action: "
    actions = input_string.split("Action: ")[1:]
    processed_actions = []
    
    for action in actions:
        action = action.strip()
        coordinates = re.findall(r"(start_box|end_box)='\((\d+),\s*(\d+)\)'", action)
        
        updated_action = action
        for coord_type, x, y in coordinates:
            updated_action = updated_action.replace(
                f"{coord_type}='({x},{y})'", 
                f"{coord_type}='<|box_start|>({x},{y})<|box_end|>'"
            )
        processed_actions.append(updated_action)
    
    return suffix + "\n\n".join(processed_actions)


def parse_actions(response: str) -> List[str]:
    """Parse actions from UI-TARS model response.

    Args:
        response: The raw model response text
        
    Returns:
        List of parsed actions
    """
    actions = []
    # Extract the Action part from the response
    if "Action:" in response:
        action_text = response.split("Action:")[-1].strip()
        # Clean up and format action
        if action_text:
            # Handle multiple actions separated by newlines
            action_parts = action_text.split("\n\n")
            for part in action_parts:
                if part.strip():
                    actions.append(part.strip())
    
    return actions


def parse_action_parameters(action: str) -> Tuple[str, Dict[str, Any]]:
    """Parse parameters from an action string.
    
    Args:
        action: The action string to parse
        
    Returns:
        Tuple of (action_name, action_parameters)
    """
    # Handle "finished" action
    if action.startswith("finished"):
        return "finished", {}
    
    # Parse action parameters
    action_match = re.match(r'(\w+)\((.*)\)', action)
    if not action_match:
        logger.warning(f"Could not parse action: {action}")
        return "", {}
        
    action_name = action_match.group(1)
    action_params_str = action_match.group(2)
    
    tool_args = {"action": action_name}
    
    # Extract coordinate values from the action
    if "start_box" in action_params_str:
        # Extract all box coordinates
        box_pattern = r"(start_box|end_box)='(?:<\|box_start\|>)?\((\d+),\s*(\d+)\)(?:<\|box_end\|>)?'"
        box_matches = re.findall(box_pattern, action_params_str)
        
        # Handle click-type actions
        if action_name in ["click", "left_double", "right_single"]:
            # Get coordinates from start_box
            for box_type, x, y in box_matches:
                if box_type == "start_box":
                    tool_args["x"] = int(x)
                    tool_args["y"] = int(y)
                    break
        
        # Handle drag action
        elif action_name == "drag":
            start_x, start_y = None, None
            end_x, end_y = None, None
            
            for box_type, x, y in box_matches:
                if box_type == "start_box":
                    start_x, start_y = int(x), int(y)
                elif box_type == "end_box":
                    end_x, end_y = int(x), int(y)
            
            if not None in [start_x, start_y, end_x, end_y]:
                tool_args["start_x"] = start_x
                tool_args["start_y"] = start_y
                tool_args["end_x"] = end_x
                tool_args["end_y"] = end_y
            
        # Handle scroll action
        elif action_name == "scroll":
            # Get coordinates from start_box
            for box_type, x, y in box_matches:
                if box_type == "start_box":
                    tool_args["x"] = int(x)
                    tool_args["y"] = int(y)
                    break
            
            # Extract direction
            direction_match = re.search(r"direction='([^']+)'", action_params_str)
            if direction_match:
                tool_args["direction"] = direction_match.group(1)
    
    # Handle typing text
    elif action_name == "type":
        # Extract text content
        content_match = re.search(r"content='([^']*)'", action_params_str)
        if content_match:
            # Unescape escaped characters
            text = content_match.group(1).replace("\\'", "'").replace('\\"', '"').replace("\\n", "\n")
            tool_args = {"action": "type_text", "text": text}
    
    # Handle hotkey
    elif action_name == "hotkey":
        # Extract key combination
        key_match = re.search(r"key='([^']*)'", action_params_str)
        if key_match:
            keys = key_match.group(1).split()
            tool_args = {"action": "hotkey", "keys": keys}
    
    return action_name, tool_args
