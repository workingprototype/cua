"""Cloud VM provider implementation.

This module contains a stub implementation for a future cloud VM provider.
"""

import logging
from typing import Dict, List, Optional, Any

from ..base import BaseVMProvider, VMProviderType

# Setup logging
logger = logging.getLogger(__name__)

import asyncio
import aiohttp
from urllib.parse import urlparse

class CloudProvider(BaseVMProvider):
    """Cloud VM Provider implementation using /api/vm-host endpoint."""
    def __init__(
        self,
        api_key: str = None,
        endpoint_url: str = "https://trycua.com/api/vm-host",
        verbose: bool = False,
        **kwargs,
    ):
        """
        Args:
            api_key: API key for authentication
            name: Name of the VM
            endpoint_url: Endpoint for the VM host API
            verbose: Enable verbose logging
        """
        assert api_key, "api_key required for CloudProvider"
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.verbose = verbose

    @property
    def provider_type(self) -> VMProviderType:
        return VMProviderType.CLOUD

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Get VM VNC URL by name using the cloud API."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"vm_name": name}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.endpoint_url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    vnc_url = (await resp.text()).strip()
                    parsed = urlparse(vnc_url)
                    hostname = parsed.hostname
                    return {"name": vm_name, "status": "available", "vnc_url": vnc_url, "hostname": hostname}
                else:
                    try:
                        error = await resp.json()
                    except Exception:
                        error = {"error": await resp.text()}
                    return {"name": vm_name, "status": "error", **error}

    async def list_vms(self) -> List[Dict[str, Any]]:
        logger.warning("CloudProvider.list_vms is not implemented")
        return []

    async def run_vm(self, image: str, name: str, run_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        logger.warning("CloudProvider.run_vm is not implemented")
        return {"name": name, "status": "unavailable", "message": "CloudProvider is not implemented"}

    async def stop_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        logger.warning("CloudProvider.stop_vm is not implemented")
        return {"name": name, "status": "stopped", "message": "CloudProvider is not implemented"}

    async def update_vm(self, name: str, update_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        logger.warning("CloudProvider.update_vm is not implemented")
        return {"name": name, "status": "unchanged", "message": "CloudProvider is not implemented"}

    async def get_ip(self, name: Optional[str] = None, storage: Optional[str] = None, retry_delay: int = 2) -> str:
        """
        Return the VM's IP address as '{vm_name}.us.vms.trycua.com'.
        Uses the provided 'name' argument (the VM name requested by the caller).
        Retries up to 3 times with retry_delay seconds if hostname is not available.
        """
        attempts = 3
        last_error = None
        for attempt in range(attempts):
            result = await self.get_vm(name=name, storage=storage)
            hostname = result.get("hostname")
            if hostname:
                return hostname
            last_error = result.get("error") or result
            if attempt < attempts - 1:
                await asyncio.sleep(retry_delay)
        raise RuntimeError(f"Failed to get VM hostname after {attempts} attempts: {last_error}")
