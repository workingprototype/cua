"""
Computer handler implementation for OpenAI computer-use-preview protocol.
"""

import base64
from typing import Dict, List, Any, Literal, Union, Optional
from .types import Computer


class OpenAIComputerHandler:
    """Computer handler that implements the Computer protocol using the computer interface."""
    
    def __init__(self, computer_interface):
        """Initialize with a computer interface (from tool schema)."""
        self.interface = computer_interface
    
    # ==== Computer-Use-Preview Action Space ==== 

    async def get_environment(self) -> Literal["windows", "mac", "linux", "browser"]:
        """Get the current environment type."""
        # For now, return a default - this could be enhanced to detect actual environment
        return "windows"

    async def get_dimensions(self) -> tuple[int, int]:
        """Get screen dimensions as (width, height)."""
        screen_size = await self.interface.get_screen_size()
        return screen_size["width"], screen_size["height"]
    
    async def screenshot(self) -> str:
        """Take a screenshot and return as base64 string."""
        screenshot_bytes = await self.interface.screenshot()
        return base64.b64encode(screenshot_bytes).decode('utf-8')
    
    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at coordinates with specified button."""
        if button == "left":
            await self.interface.left_click(x, y)
        elif button == "right":
            await self.interface.right_click(x, y)
        else:
            # Default to left click for unknown buttons
            await self.interface.left_click(x, y)
    
    async def double_click(self, x: int, y: int) -> None:
        """Double click at coordinates."""
        await self.interface.double_click(x, y)
    
    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """Scroll at coordinates with specified scroll amounts."""
        await self.interface.move_cursor(x, y)
        await self.interface.scroll(scroll_x, scroll_y)
    
    async def type(self, text: str) -> None:
        """Type text."""
        await self.interface.type_text(text)
    
    async def wait(self, ms: int = 1000) -> None:
        """Wait for specified milliseconds."""
        import asyncio
        await asyncio.sleep(ms / 1000.0)
    
    async def move(self, x: int, y: int) -> None:
        """Move cursor to coordinates."""
        await self.interface.move_cursor(x, y)
    
    async def keypress(self, keys: Union[List[str], str]) -> None:
        """Press key combination."""
        if isinstance(keys, str):
            keys = keys.replace("-", "+").split("+")
        if len(keys) == 1:
            await self.interface.press_key(keys[0])
        else:
            # Handle key combinations
            await self.interface.hotkey(*keys)
    
    async def drag(self, path: List[Dict[str, int]]) -> None:
        """Drag along specified path."""
        if not path:
            return
        
        # Start drag from first point
        start = path[0]
        await self.interface.mouse_down(start["x"], start["y"])
        
        # Move through path
        for point in path[1:]:
            await self.interface.move_cursor(point["x"], point["y"])
        
        # End drag at last point
        end = path[-1]
        await self.interface.mouse_up(end["x"], end["y"])
    
    async def get_current_url(self) -> str:
        """Get current URL (for browser environments)."""
        # This would need to be implemented based on the specific browser interface
        # For now, return empty string
        return ""

    # ==== Anthropic Computer Action Space ==== 
    async def left_mouse_down(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Left mouse down at coordinates."""
        await self.interface.mouse_down(x, y, button="left")
    
    async def left_mouse_up(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Left mouse up at coordinates."""
        await self.interface.mouse_up(x, y, button="left")

def acknowledge_safety_check_callback(message: str, allow_always: bool = False) -> bool:
    """Safety check callback for user acknowledgment."""
    if allow_always:
        return True
    response = input(
        f"Safety Check Warning: {message}\nDo you want to acknowledge and proceed? (y/n): "
    ).lower()
    return response.strip() == "y"


def check_blocklisted_url(url: str) -> None:
    """Check if URL is blocklisted (placeholder implementation)."""
    # This would contain actual URL checking logic
    pass
