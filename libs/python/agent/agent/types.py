"""
Type definitions for agent
"""

from typing import Dict, List, Any, Optional, Callable, Protocol, Literal
from pydantic import BaseModel
import re
from litellm import ResponseInputParam, ResponsesAPIResponse, ToolParam
from collections.abc import Iterable

# Agent input types
Messages = str | ResponseInputParam
Tools = Optional[Iterable[ToolParam]]

# Agent output types
AgentResponse = ResponsesAPIResponse 
AgentCapability = Literal["step", "click"]


# Agent config registration
class AgentConfigInfo(BaseModel):
    """Information about a registered agent config"""
    agent_class: type
    models_regex: str
    priority: int = 0
    
    def matches_model(self, model: str) -> bool:
        """Check if this agent config matches the given model"""
        return bool(re.match(self.models_regex, model))

# Computer tool interface
class Computer(Protocol):
    """Protocol defining the interface for computer interactions."""
    
    async def get_environment(self) -> Literal["windows", "mac", "linux", "browser"]:
        """Get the current environment type."""
        ...
    
    async def get_dimensions(self) -> tuple[int, int]:
        """Get screen dimensions as (width, height)."""
        ...
    
    async def screenshot(self) -> str:
        """Take a screenshot and return as base64 string."""
        ...
    
    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at coordinates with specified button."""
        ...
    
    async def double_click(self, x: int, y: int) -> None:
        """Double click at coordinates."""
        ...
    
    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """Scroll at coordinates with specified scroll amounts."""
        ...
    
    async def type(self, text: str) -> None:
        """Type text."""
        ...
    
    async def wait(self, ms: int = 1000) -> None:
        """Wait for specified milliseconds."""
        ...
    
    async def move(self, x: int, y: int) -> None:
        """Move cursor to coordinates."""
        ...
    
    async def keypress(self, keys: List[str]) -> None:
        """Press key combination."""
        ...
    
    async def drag(self, path: List[Dict[str, int]]) -> None:
        """Drag along specified path."""
        ...
    
    async def get_current_url(self) -> str:
        """Get current URL (for browser environments)."""
        ...
