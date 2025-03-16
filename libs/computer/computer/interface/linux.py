"""Linux computer interface implementation."""

from typing import Dict
from .base import BaseComputerInterface

class LinuxInterface(BaseComputerInterface):
    """Linux-specific computer interface."""
    
    async def wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for interface to be ready."""
        # Placeholder implementation
        pass
    
    def close(self) -> None:
        """Close the interface connection."""
        # Placeholder implementation
        pass
    
    async def get_screen_size(self) -> Dict[str, int]:
        """Get the screen dimensions."""
        # Placeholder implementation
        return {"width": 1920, "height": 1080}
    
    async def screenshot(self) -> bytes:
        """Take a screenshot."""
        # Placeholder implementation
        return b"" 