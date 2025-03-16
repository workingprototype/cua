"""Models for computer configuration."""

from dataclasses import dataclass
from typing import Optional
from pylume import PyLume

@dataclass
class Display:
    """Display configuration."""
    width: int
    height: int

@dataclass
class Image:
    """VM image configuration."""
    image: str
    tag: str
    name: str

@dataclass
class Computer:
    """Computer configuration."""
    image: str
    tag: str
    name: str
    display: Display
    memory: str
    cpu: str
    pylume: Optional[PyLume] = None
    
    # @property   # Remove the property decorator
    async def get_ip(self) -> Optional[str]:
        """Get the IP address of the VM."""
        vm = await self.pylume.get_vm(self.name)  # type: ignore[attr-defined]
        return vm.ip_address if vm else None 