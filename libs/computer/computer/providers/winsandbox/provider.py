"""Windows Sandbox VM provider implementation using pywinsandbox."""

import os
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List

from ..base import BaseVMProvider, VMProviderType

# Setup logging
logger = logging.getLogger(__name__)

try:
    import winsandbox
    HAS_WINSANDBOX = True
except ImportError:
    HAS_WINSANDBOX = False


class WinSandboxProvider(BaseVMProvider):
    """Windows Sandbox VM provider implementation using pywinsandbox.
    
    This provider uses Windows Sandbox to create isolated Windows environments.
    Storage is always ephemeral with Windows Sandbox.
    """
    
    def __init__(
        self, 
        port: int = 7777,
        host: str = "localhost",
        storage: Optional[str] = None,
        verbose: bool = False,
        ephemeral: bool = True,  # Windows Sandbox is always ephemeral
        memory_mb: int = 4096,
        networking: bool = True,
        **kwargs
    ):
        """Initialize the Windows Sandbox provider.
        
        Args:
            port: Port for the computer server (default: 7777)
            host: Host to use for connections (default: localhost)
            storage: Storage path (ignored - Windows Sandbox is always ephemeral)
            verbose: Enable verbose logging
            ephemeral: Always True for Windows Sandbox
            memory_mb: Memory allocation in MB (default: 4096)
            networking: Enable networking in sandbox (default: True)
        """
        if not HAS_WINSANDBOX:
            raise ImportError(
                "pywinsandbox is required for WinSandboxProvider. "
                "Please install it with 'pip install pywinsandbox'"
            )
            
        self.host = host
        self.port = port
        self.verbose = verbose
        self.memory_mb = memory_mb
        self.networking = networking
        
        # Windows Sandbox is always ephemeral
        if not ephemeral:
            logger.warning("Windows Sandbox storage is always ephemeral. Ignoring ephemeral=False.")
        self.ephemeral = True
        
        # Storage is always ephemeral for Windows Sandbox
        if storage and storage != "ephemeral":
            logger.warning("Windows Sandbox does not support persistent storage. Using ephemeral storage.")
        self.storage = "ephemeral"
        
        self.logger = logging.getLogger(__name__)
        
        # Track active sandboxes
        self._active_sandboxes: Dict[str, Any] = {}
        
    @property
    def provider_type(self) -> VMProviderType:
        """Get the provider type."""
        return VMProviderType.WINSANDBOX
        
    async def __aenter__(self):
        """Enter async context manager."""
        # Verify Windows Sandbox is available
        if not HAS_WINSANDBOX:
            raise ImportError("pywinsandbox is not available")
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        # Clean up any active sandboxes
        for name, sandbox in self._active_sandboxes.items():
            try:
                sandbox.shutdown()
                self.logger.info(f"Terminated sandbox: {name}")
            except Exception as e:
                self.logger.error(f"Error terminating sandbox {name}: {e}")
        
        self._active_sandboxes.clear()
        
    async def get_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Get VM information by name.
        
        Args:
            name: Name of the VM to get information for
            storage: Ignored for Windows Sandbox (always ephemeral)
            
        Returns:
            Dictionary with VM information including status, IP address, etc.
        """
        if name not in self._active_sandboxes:
            return {
                "name": name,
                "status": "stopped",
                "ip_address": None,
                "storage": "ephemeral"
            }
        
        sandbox = self._active_sandboxes[name]
        
        # Check if sandbox is still running
        try:
            # For Windows Sandbox, we assume it's running if it's in our active list
            # and hasn't been terminated
            # Try to ping the sandbox to see if it's responsive
            try:
                # Simple test to see if RPyC connection is alive
                sandbox.rpyc.modules.os.getcwd()
                status = "running"
                # Windows Sandbox typically uses localhost for RPyC connections
                ip_address = "127.0.0.1"
            except Exception:
                status = "starting"
                ip_address = None
        except Exception as e:
            self.logger.error(f"Error checking sandbox status: {e}")
            status = "error"
            ip_address = None
        
        return {
            "name": name,
            "status": status,
            "ip_address": ip_address,
            "storage": "ephemeral",
            "memory_mb": self.memory_mb,
            "networking": self.networking
        }
        
    async def list_vms(self) -> List[Dict[str, Any]]:
        """List all available VMs."""
        vms = []
        for name in self._active_sandboxes.keys():
            vm_info = await self.get_vm(name)
            vms.append(vm_info)
        return vms
        
    async def run_vm(self, image: str, name: str, run_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Run a VM with the given options.
        
        Args:
            image: Image name (ignored for Windows Sandbox - always uses host Windows)
            name: Name of the VM to run
            run_opts: Dictionary of run options (memory, cpu, etc.)
            storage: Ignored for Windows Sandbox (always ephemeral)
        
        Returns:
            Dictionary with VM run status and information
        """
        if name in self._active_sandboxes:
            return {
                "success": False,
                "error": f"Sandbox {name} is already running"
            }
        
        try:
            # Extract options from run_opts
            memory_mb = run_opts.get("memory_mb", self.memory_mb)
            if isinstance(memory_mb, str):
                # Convert memory string like "4GB" to MB
                if memory_mb.upper().endswith("GB"):
                    memory_mb = int(float(memory_mb[:-2]) * 1024)
                elif memory_mb.upper().endswith("MB"):
                    memory_mb = int(memory_mb[:-2])
                else:
                    memory_mb = self.memory_mb
            
            networking = run_opts.get("networking", self.networking)
            
            # Get the logon script path
            script_path = os.path.join(os.path.dirname(__file__), "logon_script.bat")
            
            # Create folder mappers if shared directories are specified
            folder_mappers = []
            shared_directories = run_opts.get("shared_directories", [])
            for shared_dir in shared_directories:
                if isinstance(shared_dir, dict):
                    host_path = shared_dir.get("hostPath", "")
                elif isinstance(shared_dir, str):
                    host_path = shared_dir
                else:
                    continue
                    
                if host_path and os.path.exists(host_path):
                    folder_mappers.append(winsandbox.FolderMapper(host_path))
            
            self.logger.info(f"Creating Windows Sandbox: {name}")
            self.logger.info(f"Memory: {memory_mb}MB, Networking: {networking}")
            if folder_mappers:
                self.logger.info(f"Shared directories: {len(folder_mappers)}")
            
            # Create the sandbox
            sandbox = winsandbox.new_sandbox(
                memory_mb=str(memory_mb),
                networking=networking,
                logon_script=f'cmd /c "{script_path}"',
                folder_mappers=folder_mappers
            )
            
            # Store the sandbox
            self._active_sandboxes[name] = sandbox
            
            self.logger.info(f"Windows Sandbox {name} created successfully")
            
            return {
                "success": True,
                "name": name,
                "status": "starting",
                "memory_mb": memory_mb,
                "networking": networking,
                "storage": "ephemeral"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create Windows Sandbox {name}: {e}")
            return {
                "success": False,
                "error": f"Failed to create sandbox: {str(e)}"
            }
        
    async def stop_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Stop a running VM.
        
        Args:
            name: Name of the VM to stop
            storage: Ignored for Windows Sandbox
            
        Returns:
            Dictionary with stop status and information
        """
        if name not in self._active_sandboxes:
            return {
                "success": False,
                "error": f"Sandbox {name} is not running"
            }
        
        try:
            sandbox = self._active_sandboxes[name]
            
            # Terminate the sandbox
            sandbox.shutdown()
            
            # Remove from active sandboxes
            del self._active_sandboxes[name]
            
            self.logger.info(f"Windows Sandbox {name} stopped successfully")
            
            return {
                "success": True,
                "name": name,
                "status": "stopped"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to stop Windows Sandbox {name}: {e}")
            return {
                "success": False,
                "error": f"Failed to stop sandbox: {str(e)}"
            }
        
    async def update_vm(self, name: str, update_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Update VM configuration.
        
        Note: Windows Sandbox does not support runtime configuration updates.
        The sandbox must be stopped and restarted with new configuration.
        
        Args:
            name: Name of the VM to update
            update_opts: Dictionary of update options
            storage: Ignored for Windows Sandbox
            
        Returns:
            Dictionary with update status and information
        """
        return {
            "success": False,
            "error": "Windows Sandbox does not support runtime configuration updates. "
                    "Please stop and restart the sandbox with new configuration."
        }
        
    async def get_ip(self, name: str, storage: Optional[str] = None, retry_delay: int = 2) -> str:
        """Get the IP address of a VM, waiting indefinitely until it's available.
        
        Args:
            name: Name of the VM to get the IP for
            storage: Ignored for Windows Sandbox
            retry_delay: Delay between retries in seconds (default: 2)
            
        Returns:
            IP address of the VM when it becomes available
        """
        total_attempts = 0
        
        # Loop indefinitely until we get a valid IP
        while True:
            total_attempts += 1
            
            # Log retry message but not on first attempt
            if total_attempts > 1:
                self.logger.info(f"Waiting for Windows Sandbox {name} IP address (attempt {total_attempts})...")
            
            try:
                # Get VM information
                vm_info = await self.get_vm(name, storage=storage)
                
                # Check if we got a valid IP
                ip = vm_info.get("ip_address", None)
                if ip and ip != "unknown" and not ip.startswith("0.0.0.0"):
                    self.logger.info(f"Got valid Windows Sandbox IP address: {ip}")
                    return ip
                    
                # Check the VM status
                status = vm_info.get("status", "unknown")
                
                # If VM is not running yet, log and wait
                if status != "running":
                    self.logger.info(f"Windows Sandbox is not running yet (status: {status}). Waiting...")
                # If VM is running but no IP yet, wait and retry
                else:
                    self.logger.info("Windows Sandbox is running but no valid IP address yet. Waiting...")
                
            except Exception as e:
                self.logger.warning(f"Error getting Windows Sandbox {name} IP: {e}, continuing to wait...")
                
            # Wait before next retry
            await asyncio.sleep(retry_delay)
            
            # Add progress log every 10 attempts
            if total_attempts % 10 == 0:
                self.logger.info(f"Still waiting for Windows Sandbox {name} IP after {total_attempts} attempts...")
