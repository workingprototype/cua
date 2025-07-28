"""
Functions for making various Responses API items from different types of responses.
Based on the OpenAI spec for Responses API items.
"""

import base64
import json
import uuid
from typing import List, Dict, Any, Literal, Union, Optional

from openai.types.responses.response_computer_tool_call_param import (
    ResponseComputerToolCallParam, 
    ActionClick,
    ActionDoubleClick,
    ActionDrag,
    ActionDragPath,
    ActionKeypress,
    ActionMove,
    ActionScreenshot,
    ActionScroll,
    ActionType as ActionTypeAction,
    ActionWait,
    PendingSafetyCheck
)

from openai.types.responses.response_function_tool_call_param import ResponseFunctionToolCallParam
from openai.types.responses.response_output_text_param import ResponseOutputTextParam
from openai.types.responses.response_reasoning_item_param import ResponseReasoningItemParam, Summary
from openai.types.responses.response_output_message_param import ResponseOutputMessageParam
from openai.types.responses.easy_input_message_param import EasyInputMessageParam
from openai.types.responses.response_input_image_param import ResponseInputImageParam

def random_id():
    return str(uuid.uuid4())

# User message items
def make_input_image_item(image_data: Union[str, bytes]) -> EasyInputMessageParam:
    return EasyInputMessageParam(
        content=[
            ResponseInputImageParam(
                type="input_image",
                image_url=f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8') if isinstance(image_data, bytes) else image_data}"
            )
        ],
        role="user",
        type="message"
    )

# Text items
def make_reasoning_item(reasoning: str) -> ResponseReasoningItemParam:
    return ResponseReasoningItemParam(
        id=random_id(),
        summary=[
            Summary(text=reasoning, type="summary_text")
        ],
        type="reasoning"
    )

def make_output_text_item(content: str) -> ResponseOutputMessageParam:
    return ResponseOutputMessageParam(
        id=random_id(),
        content=[
            ResponseOutputTextParam(
                text=content,
                type="output_text",
                annotations=[]
            )
        ],
        role="assistant",
        status="completed",
        type="message"
    )

# Function call items
def make_function_call_item(function_name: str, arguments: Dict[str, Any], call_id: Optional[str] = None) -> ResponseFunctionToolCallParam:
    return ResponseFunctionToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        name=function_name,
        arguments=json.dumps(arguments),
        status="completed",
        type="function_call"
    )

# Computer tool call items
def make_click_item(x: int, y: int, button: Literal["left", "right", "wheel", "back", "forward"] = "left", call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionClick(
            button=button,
            type="click",
            x=x,
            y=y
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_double_click_item(x: int, y: int, call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionDoubleClick(
            type="double_click",
            x=x,
            y=y
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_drag_item(path: List[Dict[str, int]], call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    drag_path = [ActionDragPath(x=point["x"], y=point["y"]) for point in path]
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionDrag(
            path=drag_path,
            type="drag"
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_keypress_item(keys: List[str], call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionKeypress(
            keys=keys,
            type="keypress"
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_move_item(x: int, y: int, call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionMove(
            type="move",
            x=x,
            y=y
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_screenshot_item(call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionScreenshot(
            type="screenshot"
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_scroll_item(x: int, y: int, scroll_x: int, scroll_y: int, call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionScroll(
            scroll_x=scroll_x,
            scroll_y=scroll_y,
            type="scroll",
            x=x,
            y=y
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_type_item(text: str, call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionTypeAction(
            text=text,
            type="type"
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )

def make_wait_item(call_id: Optional[str] = None) -> ResponseComputerToolCallParam:
    return ResponseComputerToolCallParam(
        id=random_id(),
        call_id=call_id if call_id else random_id(),
        action=ActionWait(
            type="wait"
        ),
        pending_safety_checks=[],
        status="completed",
        type="computer_call"
    )
