"""Provider-agnostic implementation of the ComputerTool."""

import logging
import base64
import io
from typing import Any, Dict

from PIL import Image
from computer.computer import Computer

from ....core.tools.computer import BaseComputerTool
from ....core.tools import ToolResult, ToolError


class OmniComputerTool(BaseComputerTool):
    """A provider-agnostic implementation of the computer tool."""

    name = "computer"
    logger = logging.getLogger(__name__)

    def __init__(self, computer: Computer):
        """Initialize the ComputerTool.

        Args:
            computer: Computer instance for screen interactions
        """
        super().__init__(computer)
        # Initialize dimensions to None, will be set in initialize_dimensions
        self.width = None
        self.height = None
        self.display_num = None

    def to_params(self) -> Dict[str, Any]:
        """Convert tool to provider-agnostic parameters.

        Returns:
            Dictionary with tool parameters
        """
        return {
            "name": self.name,
            "description": "A tool that allows the agent to interact with the screen, keyboard, and mouse",
            "parameters": {
                "action": {
                    "type": "string",
                    "enum": [
                        "key",
                        "type",
                        "mouse_move",
                        "left_click",
                        "left_click_drag",
                        "right_click",
                        "middle_click",
                        "double_click",
                        "screenshot",
                        "cursor_position",
                        "scroll",
                    ],
                    "description": "The action to perform on the computer",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type or key to press, required for 'key' and 'type' actions",
                },
                "coordinate": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "X,Y coordinates for mouse actions like click and move",
                },
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "Direction to scroll, used with the 'scroll' action",
                },
                "amount": {
                    "type": "integer",
                    "description": "Amount to scroll, used with the 'scroll' action",
                },
            },
            **self.options,
        }

    async def __call__(self, **kwargs) -> ToolResult:
        """Execute the computer tool with the provided arguments.

        Args:
            action: The action to perform
            text: Text to type or key to press (for key/type actions)
            coordinate: X,Y coordinates (for mouse actions)
            direction: Direction to scroll (for scroll action)
            amount: Amount to scroll (for scroll action)

        Returns:
            ToolResult with the action output and optional screenshot
        """
        # Ensure dimensions are initialized
        if self.width is None or self.height is None:
            await self.initialize_dimensions()

        action = kwargs.get("action")
        text = kwargs.get("text")
        coordinate = kwargs.get("coordinate")
        direction = kwargs.get("direction", "down")
        amount = kwargs.get("amount", 10)

        self.logger.info(f"Executing computer action: {action}")

        try:
            if action == "screenshot":
                return await self.screenshot()
            elif action == "left_click" and coordinate:
                x, y = coordinate
                self.logger.info(f"Clicking at ({x}, {y})")
                await self.computer.interface.move_cursor(x, y)
                await self.computer.interface.left_click()

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Performed left click at ({x}, {y})",
                    base64_image=base64.b64encode(screenshot).decode(),
                )
            elif action == "right_click" and coordinate:
                x, y = coordinate
                self.logger.info(f"Right clicking at ({x}, {y})")
                await self.computer.interface.move_cursor(x, y)
                await self.computer.interface.right_click()

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Performed right click at ({x}, {y})",
                    base64_image=base64.b64encode(screenshot).decode(),
                )
            elif action == "double_click" and coordinate:
                x, y = coordinate
                self.logger.info(f"Double clicking at ({x}, {y})")
                await self.computer.interface.move_cursor(x, y)
                await self.computer.interface.double_click()

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Performed double click at ({x}, {y})",
                    base64_image=base64.b64encode(screenshot).decode(),
                )
            elif action == "mouse_move" and coordinate:
                x, y = coordinate
                self.logger.info(f"Moving cursor to ({x}, {y})")
                await self.computer.interface.move_cursor(x, y)

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Moved cursor to ({x}, {y})",
                    base64_image=base64.b64encode(screenshot).decode(),
                )
            elif action == "type" and text:
                self.logger.info(f"Typing text: {text}")
                await self.computer.interface.type_text(text)

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Typed text: {text}",
                    base64_image=base64.b64encode(screenshot).decode(),
                )
            elif action == "key" and text:
                self.logger.info(f"Pressing key: {text}")

                # Handle special key combinations
                if "+" in text:
                    keys = text.split("+")
                    await self.computer.interface.hotkey(*keys)
                else:
                    await self.computer.interface.press(text)

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Pressed key: {text}",
                    base64_image=base64.b64encode(screenshot).decode(),
                )
            elif action == "cursor_position":
                pos = await self.computer.interface.get_cursor_position()
                return ToolResult(output=f"X={int(pos[0])},Y={int(pos[1])}")
            elif action == "scroll":
                if direction == "down":
                    self.logger.info(f"Scrolling down, amount: {amount}")
                    for _ in range(amount):
                        await self.computer.interface.hotkey("fn", "down")
                else:
                    self.logger.info(f"Scrolling up, amount: {amount}")
                    for _ in range(amount):
                        await self.computer.interface.hotkey("fn", "up")

                # Take screenshot after action
                screenshot = await self.computer.interface.screenshot()
                screenshot = await self.resize_screenshot_if_needed(screenshot)
                return ToolResult(
                    output=f"Scrolled {direction} by {amount} steps",
                    base64_image=base64.b64encode(screenshot).decode(),
                )

            # Default to screenshot for unimplemented actions
            self.logger.warning(f"Action {action} not fully implemented, taking screenshot")
            return await self.screenshot()

        except Exception as e:
            self.logger.error(f"Error during computer action: {str(e)}")
            return ToolResult(error=f"Failed to perform {action}: {str(e)}")
