from typing import Optional
from .generic import GenericComputerInterface
from .tracing_interface import ITracingManager

class WindowsComputerInterface(GenericComputerInterface):
    """Interface for Windows."""

    def __init__(self, ip_address: str, username: str = "lume", password: str = "lume", api_key: Optional[str] = None, vm_name: Optional[str] = None, tracing: Optional[ITracingManager] = None):
        super().__init__(ip_address, username, password, api_key, vm_name, tracing, "computer.interface.windows")
