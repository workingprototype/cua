"""Base provider interface for VM backends."""

import abc
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncContextManager


class VMProviderType(str, Enum):
    """Enum of supported VM provider types."""
    LUME = "lume"
    LUMIER = "lumier"
    QEMU = "qemu"
    CLOUD = "cloud"
    UNKNOWN = "unknown"


class BaseVMProvider(AsyncContextManager):
    """Base interface for VM providers.
    
    All VM provider implementations must implement this interface.
    """
    
    @property
    @abc.abstractmethod
    def provider_type(self) -> VMProviderType:
        """Get the provider type."""
        pass
        
    @abc.abstractmethod
    async def get_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Get VM information by name.
        
        Args:
            name: Name of the VM to get information for
            storage: Optional storage path override. If provided, this will be used
                    instead of the provider's default storage path.
        
        Returns:
            Dictionary with VM information including status, IP address, etc.
        """
        pass
        
    @abc.abstractmethod
    async def list_vms(self) -> List[Dict[str, Any]]:
        """List all available VMs."""
        pass
        
    @abc.abstractmethod
    async def run_vm(self, name: str, run_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Run a VM by name with the given options.
        
        Args:
            name: Name of the VM to run
            run_opts: Dictionary of run options (memory, cpu, etc.)
            storage: Optional storage path override. If provided, this will be used
                    instead of the provider's default storage path.
        
        Returns:
            Dictionary with VM run status and information
        """
        pass
        
    @abc.abstractmethod
    async def stop_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Stop a VM by name.
        
        Args:
            name: Name of the VM to stop
            storage: Optional storage path override. If provided, this will be used
                    instead of the provider's default storage path.
        
        Returns:
            Dictionary with VM stop status and information
        """
        pass
        
    @abc.abstractmethod
    async def update_vm(self, name: str, update_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Update VM configuration.
        
        Args:
            name: Name of the VM to update
            update_opts: Dictionary of update options (memory, cpu, etc.)
            storage: Optional storage path override. If provided, this will be used
                    instead of the provider's default storage path.
        
        Returns:
            Dictionary with VM update status and information
        """
        pass
