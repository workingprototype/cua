"""Factory for creating computer interfaces."""

from typing import Literal
from .base import BaseComputerInterface

class InterfaceFactory:
    """Factory for creating OS-specific computer interfaces."""
    
    @staticmethod
    def create_interface_for_os(
        os: Literal['macos', 'linux'],
        ip_address: str
    ) -> BaseComputerInterface:
        """Create an interface for the specified OS.
        
        Args:
            os: Operating system type ('macos' or 'linux')
            ip_address: IP address of the computer to control
            
        Returns:
            BaseComputerInterface: The appropriate interface for the OS
            
        Raises:
            ValueError: If the OS type is not supported
        """
        # Import implementations here to avoid circular imports
        from .macos import MacOSComputerInterface
        
        if os == 'macos':
            return MacOSComputerInterface(ip_address)
        else:
            raise ValueError(f"Unsupported OS type: {os}") 