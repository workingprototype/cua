"""Lume VM provider implementation using curl commands.

This provider uses direct curl commands to interact with the Lume API,
removing the dependency on the pylume Python package.
"""

import os
import re
import asyncio
import json
import subprocess
import logging
from typing import Dict, Any, Optional, List, Tuple

from ..base import BaseVMProvider, VMProviderType
from ...logger import Logger, LogLevel
from ..lume_api import (
    lume_api_get,
    lume_api_run,
    lume_api_stop,
    lume_api_update,
    HAS_CURL,
    parse_memory
)

# Setup logging
logger = logging.getLogger(__name__)


class LumeProvider(BaseVMProvider):
    """Lume VM provider implementation using direct curl commands.
    
    This provider uses curl to interact with the Lume API server,
    removing the dependency on the pylume Python package.
    """
    
    def __init__(
        self, 
        port: Optional[int] = None,
        host: str = "localhost",
        bin_path: Optional[str] = None,
        storage: Optional[str] = None,
        verbose: bool = False,
    ):
        """Initialize the Lume provider.
        
        Args:
            port: Port for the Lume API server (default: 3000)
            host: Host to use for API connections (default: localhost)
            bin_path: Optional path to the Lume binary (not used directly)
            storage: Path to store VM data
            verbose: Enable verbose logging
        """
        if not HAS_CURL:
            raise ImportError(
                "curl is required for LumeProvider. "
                "Please ensure it is installed and in your PATH."
            )
            
        self.host = host
        self.port = port or 3000  # Default port for Lume API
        self.storage = storage
        self.bin_path = bin_path
        self.verbose = verbose
        
        # Base API URL for Lume API calls
        self.api_base_url = f"http://{self.host}:{self.port}"
        
    @property
    def provider_type(self) -> VMProviderType:
        """Get the provider type."""
        return VMProviderType.LUME
        
    async def __aenter__(self):
        """Enter async context manager."""
        # No initialization needed, just return self
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        # No cleanup needed
        pass
            
    def _lume_api_get(self, vm_name: str = "", storage: Optional[str] = None, debug: bool = False) -> Dict[str, Any]:
        """Get VM information using shared lume_api function.
        
        Args:
            vm_name: Optional name of the VM to get info for.
                     If empty, lists all VMs.
            storage: Optional storage path override. If provided, this will be used instead of self.storage
            debug: Whether to show debug output
            
        Returns:
            Dictionary with VM status information parsed from JSON response
        """
        # Use the shared implementation from lume_api module
        return lume_api_get(
            vm_name=vm_name,
            host=self.host,
            port=self.port,
            storage=storage if storage is not None else self.storage,
            debug=debug,
            verbose=self.verbose
        )
    
    def _lume_api_run(self, vm_name: str, run_opts: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
        """Run a VM using shared lume_api function.
        
        Args:
            vm_name: Name of the VM to run
            run_opts: Dictionary of run options
            debug: Whether to show debug output
            
        Returns:
            Dictionary with API response or error information
        """
        # Use the shared implementation from lume_api module
        return lume_api_run(
            vm_name=vm_name, 
            host=self.host,
            port=self.port,
            run_opts=run_opts,
            storage=self.storage,
            debug=debug,
            verbose=self.verbose
        )
    
    def _lume_api_stop(self, vm_name: str, debug: bool = False) -> Dict[str, Any]:
        """Stop a VM using shared lume_api function.
        
        Args:
            vm_name: Name of the VM to stop
            debug: Whether to show debug output
            
        Returns:
            Dictionary with API response or error information
        """
        # Use the shared implementation from lume_api module
        return lume_api_stop(
            vm_name=vm_name, 
            host=self.host,
            port=self.port,
            storage=self.storage,
            debug=debug,
            verbose=self.verbose
        )
    
    def _lume_api_update(self, vm_name: str, update_opts: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
        """Update VM configuration using shared lume_api function.
        
        Args:
            vm_name: Name of the VM to update
            update_opts: Dictionary of update options
            debug: Whether to show debug output
            
        Returns:
            Dictionary with API response or error information
        """
        # Use the shared implementation from lume_api module
        return lume_api_update(
            vm_name=vm_name, 
            host=self.host,
            port=self.port,
            update_opts=update_opts,
            storage=self.storage,
            debug=debug,
            verbose=self.verbose
        )
    
    async def get_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Get VM information by name.
        
        Args:
            name: Name of the VM to get information for
            storage: Optional storage path override. If provided, this will be used
                    instead of the provider's default storage path.
            
        Returns:
            Dictionary with VM information including status, IP address, etc.
            
        Note:
            If storage is not provided, the provider's default storage path will be used.
            The storage parameter allows overriding the storage location for this specific call.
        """
        if not HAS_CURL:
            logger.error("curl is not available. Cannot get VM status.")
            return {
                "name": name,
                "status": "unavailable",
                "error": "curl is not available"
            }
        
        # First try to get detailed VM info from the API
        try:
            # Query the Lume API for VM status using the provider's storage_path
            vm_info = self._lume_api_get(
                vm_name=name, 
                storage=storage if storage is not None else self.storage,
                debug=self.verbose
            )
            
            # Check for API errors
            if "error" in vm_info:
                logger.debug(f"API request error: {vm_info['error']}")
                # If we got an error from the API, report the VM as not ready yet
                return {
                    "name": name,
                    "status": "starting",  # VM is still starting - do not attempt to connect yet
                    "api_status": "error",
                    "error": vm_info["error"]
                }
            
            # Process the VM status information
            vm_status = vm_info.get("status", "unknown")
            
            # Check if VM is stopped or not running - don't wait for IP in this case
            if vm_status == "stopped":
                logger.info(f"VM {name} is in '{vm_status}' state - not waiting for IP address")
                # Return the status as-is without waiting for an IP
                result = {
                    "name": name,
                    "status": vm_status,
                    **vm_info  # Include all original fields from the API response
                }
                return result
            
            # Handle field name differences between APIs
            # Some APIs use camelCase, others use snake_case
            if "vncUrl" in vm_info:
                vnc_url = vm_info["vncUrl"]
            elif "vnc_url" in vm_info:
                vnc_url = vm_info["vnc_url"]
            else:
                vnc_url = ""
                
            if "ipAddress" in vm_info:
                ip_address = vm_info["ipAddress"]
            elif "ip_address" in vm_info:
                ip_address = vm_info["ip_address"]
            else:
                # If no IP address is provided and VM is supposed to be running,
                # report it as still starting
                ip_address = None
                logger.info(f"VM {name} is in '{vm_status}' state but no IP address found - reporting as still starting")
                
            logger.info(f"VM {name} status: {vm_status}")
            
            # Return the complete status information
            result = {
                "name": name,
                "status": vm_status if vm_status else "running",
                "ip_address": ip_address,
                "vnc_url": vnc_url,
                "api_status": "ok"
            }
            
            # Include all original fields from the API response
            if isinstance(vm_info, dict):
                for key, value in vm_info.items():
                    if key not in result:  # Don't override our carefully processed fields
                        result[key] = value
                        
            return result
            
        except Exception as e:
            logger.error(f"Failed to get VM status: {e}")
            # Return a fallback status that indicates the VM is not ready yet
            return {
                "name": name,
                "status": "initializing",  # VM is still initializing
                "error": f"Failed to get VM status: {str(e)}"
            }
        
    async def list_vms(self) -> List[Dict[str, Any]]:
        """List all available VMs."""
        result = self._lume_api_get(debug=self.verbose)
        
        # Extract the VMs list from the response
        if "vms" in result and isinstance(result["vms"], list):
            return result["vms"]
        elif "error" in result:
            logger.error(f"Error listing VMs: {result['error']}")
            return []
        else:
            return []
        
    async def run_vm(self, name: str, run_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Run a VM with the given options."""
        return self._lume_api_run(name, run_opts, debug=self.verbose)
        
    async def stop_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Stop a running VM."""
        return self._lume_api_stop(name, debug=self.verbose)
        
    async def update_vm(self, name: str, update_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Update VM configuration."""
        return self._lume_api_update(name, update_opts, debug=self.verbose)
