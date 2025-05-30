"""
Linux implementation of automation and accessibility handlers.

This implementation attempts to use pyautogui for GUI automation when available.
If running in a headless environment without X11, it will fall back to simulated responses.
To use GUI automation in a headless environment:
1. Install Xvfb: sudo apt-get install xvfb
2. Run with virtual display: xvfb-run python -m computer_server
"""
from typing import Dict, Any, List, Tuple, Optional
import logging
import subprocess
import base64
import os
import json
from io import BytesIO

# Configure logger
logger = logging.getLogger(__name__)

# Try to import pyautogui, but don't fail if it's not available
# This allows the server to run in headless environments
try:
    import pyautogui

    logger.info("pyautogui successfully imported, GUI automation available")
except Exception as e:
    logger.warning(f"pyautogui import failed: {str(e)}. GUI operations will be simulated.")

from .base import BaseAccessibilityHandler, BaseAutomationHandler

class LinuxAccessibilityHandler(BaseAccessibilityHandler):
    """Linux implementation of accessibility handler."""
    
    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """Get the accessibility tree of the current window."""
        # Linux doesn't have equivalent accessibility API like macOS
        # Return a minimal dummy tree
        logger.info("Getting accessibility tree (simulated, no accessibility API available on Linux)")
        return {
            "success": True,
            "tree": {
                "role": "Window",
                "title": "Linux Window",
                "position": {"x": 0, "y": 0},
                "size": {"width": 1920, "height": 1080},
                "children": []
            }
        }
    
    async def find_element(self, role: Optional[str] = None,
                          title: Optional[str] = None,
                          value: Optional[str] = None) -> Dict[str, Any]:
        """Find an element in the accessibility tree by criteria."""
        logger.info(f"Finding element with role={role}, title={title}, value={value} (not supported on Linux)")
        return {
            "success": False,
            "message": "Element search not supported on Linux"
        }
    
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get the current cursor position."""
        try:
            pos = pyautogui.position()
            return pos.x, pos.y
        except Exception as e:
            logger.warning(f"Failed to get cursor position with pyautogui: {e}")
        
        logger.info("Getting cursor position (simulated)")
        return 0, 0
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get the screen size."""
        try:
            size = pyautogui.size()
            return size.width, size.height
        except Exception as e:
            logger.warning(f"Failed to get screen size with pyautogui: {e}")
        
        logger.info("Getting screen size (simulated)")
        return 1920, 1080

class LinuxAutomationHandler(BaseAutomationHandler):
    """Linux implementation of automation handler using pyautogui."""
    
    # Mouse Actions
    async def move_cursor(self, x: int, y: int) -> Dict[str, Any]:
        try:
            pyautogui.moveTo(x, y)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def left_click(self, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.click()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.rightClick()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.doubleClick(interval=0.1)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> Dict[str, Any]:
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.click(button=button)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def drag_to(self, x: int, y: int, button: str = "left", duration: float = 0.5) -> Dict[str, Any]:
        try:
            pyautogui.dragTo(x, y, duration=duration, button=button)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, button: str = "left") -> Dict[str, Any]:
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.5, button=button)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def drag_path(self, path: List[Tuple[int, int]], button: str = "left", duration: float = 0.5) -> Dict[str, Any]:
        try:
            if not path:
                return {"success": False, "error": "Path is empty"}
            pyautogui.moveTo(*path[0])
            for x, y in path[1:]:
                pyautogui.dragTo(x, y, duration=duration, button=button)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Keyboard Actions
    async def type_text(self, text: str) -> Dict[str, Any]:
        try:
            pyautogui.write(text)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str) -> Dict[str, Any]:
        try:
            pyautogui.press(key)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        try:
            pyautogui.hotkey(*keys)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Scrolling Actions
    async def scroll_down(self, clicks: int = 1) -> Dict[str, Any]:
        try:
            pyautogui.scroll(-clicks)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll_up(self, clicks: int = 1) -> Dict[str, Any]:
        try:
            pyautogui.scroll(clicks)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Screen Actions
    async def screenshot(self) -> Dict[str, Any]:
        try:
            from PIL import Image
            screenshot = pyautogui.screenshot()
            if not isinstance(screenshot, Image.Image):
                return {"success": False, "error": "Failed to capture screenshot"}
            buffered = BytesIO()
            screenshot.save(buffered, format="PNG", optimize=True)
            buffered.seek(0)
            image_data = base64.b64encode(buffered.getvalue()).decode()
            return {"success": True, "image_data": image_data}
        except Exception as e:
            return {"success": False, "error": f"Screenshot error: {str(e)}"}

    async def get_screen_size(self) -> Dict[str, Any]:
        try:
            size = pyautogui.size()
            return {"success": True, "size": {"width": size.width, "height": size.height}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_cursor_position(self) -> Dict[str, Any]:
        try:
            pos = pyautogui.position()
            return {"success": True, "position": {"x": pos.x, "y": pos.y}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Clipboard Actions
    async def copy_to_clipboard(self) -> Dict[str, Any]:
        try:
            import pyperclip
            content = pyperclip.paste()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_clipboard(self, text: str) -> Dict[str, Any]:
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Command Execution
    async def run_command(self, command: str) -> Dict[str, Any]:
        try:
            process = subprocess.run(command, shell=True, capture_output=True, text=True)
            return {"success": True, "stdout": process.stdout, "stderr": process.stderr, "return_code": process.returncode}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_screen_data(self, getter_types: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Get screen data using specified getter types.
        
        Args:
            getter_types: List of getter types to use (e.g., ['accessibility_tree', 'ocr', 'dom'])
                         If None, defaults to ['accessibility_tree']
            **kwargs: Additional parameters for specific getter types
            
        Returns:
            Dict containing the requested screen data from all getters
        """
        try:
            # Default to accessibility_tree if no getter types specified
            if getter_types is None:
                getter_types = ["accessibility_tree"]
            
            # Collect data from all requested getters
            all_data = {}
            errors = []
            
            for getter_type in getter_types:
                try:
                    if getter_type == "accessibility_tree":
                        # Use the existing accessibility handler
                        accessibility_handler = LinuxAccessibilityHandler()
                        tree_data = await accessibility_handler.get_accessibility_tree()
                        all_data["accessibility_tree"] = tree_data
                    elif getter_type == "screenshot":
                        # Take a screenshot and return as base64
                        screenshot_result = await self.screenshot()
                        if screenshot_result.get("success"):
                            all_data["screenshot"] = {
                                "base64": screenshot_result.get("image_data"),
                                "format": "png"
                            }
                        else:
                            errors.append(f"Screenshot failed: {screenshot_result.get('error')}")
                    else:
                        # Future: Add support for application-specific getters
                        # For now, record unsupported getter types
                        errors.append(f"Unsupported getter type: {getter_type}")
                except Exception as e:
                    errors.append(f"Error with getter '{getter_type}': {str(e)}")
            
            return {
                "success": len(all_data) > 0,
                "data": all_data,
                "getter_types": getter_types,
                "errors": errors if errors else None,
                "supported_types": ["accessibility_tree", "screenshot"]  # List of currently supported types
            }
        except Exception as e:
            return {"success": False, "error": str(e), "getter_types": getter_types}
