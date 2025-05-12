"""
Lumier VM provider implementation.

This provider uses Docker containers running the Lumier image to create
macOS and Linux VMs. It handles VM lifecycle operations through Docker
commands and container management.
"""

import logging
import os
import json
import asyncio
from typing import Dict, List, Optional, Any
import subprocess
import time
import re

from ..base import BaseVMProvider, VMProviderType
from ..lume_api import (
    lume_api_get,
    lume_api_run,
    lume_api_stop,
    lume_api_update
)

# Setup logging
logger = logging.getLogger(__name__)

# Check if Docker is available
try:
    subprocess.run(["docker", "--version"], capture_output=True, check=True)
    HAS_LUMIER = True
except (subprocess.SubprocessError, FileNotFoundError):
    HAS_LUMIER = False


class LumierProvider(BaseVMProvider):
    """
    Lumier VM Provider implementation using Docker containers.
    
    This provider uses Docker to run Lumier containers that can create
    macOS and Linux VMs through containerization.
    """
    
    def __init__(
        self, 
        port: Optional[int] = 3000,
        host: str = "localhost",
        storage: Optional[str] = None,
        shared_path: Optional[str] = None,
        image: str = "macos-sequoia-cua:latest",  # VM image to use
        verbose: bool = False,
        ephemeral: bool = False,
        noVNC_port: Optional[int] = 8006,
    ):
        """Initialize the Lumier VM Provider.
        
        Args:
            port: Port for the API server (default: 3000)
            host: Hostname for the API server (default: localhost)
            storage: Path for persistent VM storage
            shared_path: Path for shared folder between host and VM
            image: VM image to use (e.g. "macos-sequoia-cua:latest")
            verbose: Enable verbose logging
            ephemeral: Use ephemeral (temporary) storage
            noVNC_port: Specific port for noVNC interface (default: 8006)
        """
        self.host = host
        # Always ensure api_port has a valid value (3000 is the default)
        self.api_port = 3000 if port is None else port
        self.vnc_port = noVNC_port  # User-specified noVNC port, will be set in run_vm if provided
        self.ephemeral = ephemeral
        
        # Handle ephemeral storage (temporary directory)
        if ephemeral:
            self.storage = "ephemeral"
        else:
            self.storage = storage
            
        self.shared_path = shared_path
        self.vm_image = image  # Store the VM image name to use
        # The container_name will be set in run_vm using the VM name
        self.verbose = verbose
        self._container_id = None
        self._api_url = None  # Will be set after container starts
        
    @property
    def provider_type(self) -> VMProviderType:
        """Return the provider type."""
        return VMProviderType.LUMIER
    
    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to MB integer.
        
        Examples:
            "8GB" -> 8192
            "1024MB" -> 1024
            "512" -> 512
        """
        if isinstance(memory_str, int):
            return memory_str
            
        if isinstance(memory_str, str):
            # Extract number and unit
            match = re.match(r"(\d+)([A-Za-z]*)", memory_str)
            if match:
                value, unit = match.groups()
                value = int(value)
                unit = unit.upper()
                
                if unit == "GB" or unit == "G":
                    return value * 1024
                elif unit == "MB" or unit == "M" or unit == "":
                    return value
                    
        # Default fallback
        logger.warning(f"Could not parse memory string '{memory_str}', using 8GB default")
        return 8192  # Default to 8GB
    
    # Helper methods for interacting with the Lumier API through curl
    # These methods handle the various VM operations via API calls
    
    def _get_curl_error_message(self, return_code: int) -> str:
        """Get a descriptive error message for curl return codes.
        
        Args:
            return_code: The curl return code
            
        Returns:
            A descriptive error message
        """
        # Map common curl error codes to helpful messages
        if return_code == 7:
            return "Failed to connect - API server is starting up"
        elif return_code == 22:
            return "HTTP error returned from API server"
        elif return_code == 28:
            return "Operation timeout - API server is slow to respond"
        elif return_code == 52:
            return "Empty reply from server - API is starting but not ready"
        elif return_code == 56:
            return "Network problem during data transfer"
        else:
            return f"Unknown curl error code: {return_code}"

    
    async def get_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Get VM information by name.
        
        Args:
            name: Name of the VM to get information for
            storage: Optional storage path override. If provided, this will be used
                    instead of the provider's default storage path.
            
        Returns:
            Dictionary with VM information including status, IP address, etc.
        """
        if not HAS_LUMIER:
            logger.error("Docker is not available. Cannot get VM status.")
            return {
                "name": name,
                "status": "unavailable",
                "error": "Docker is not available"
            }
            
        # Store the current name for API requests
        self.container_name = name
        
        try:
            # Check if the container exists and is running
            check_cmd = ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Status}}"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            container_status = check_result.stdout.strip()
            
            if not container_status:
                logger.info(f"Container {name} does not exist. Will create when run_vm is called.")
                return {
                    "name": name,
                    "status": "not_found",
                    "message": "Container doesn't exist yet"
                }
                
            # Container exists, check if it's running
            is_running = container_status.startswith("Up")
            
            if not is_running:
                logger.info(f"Container {name} exists but is not running. Status: {container_status}")
                return {
                    "name": name,
                    "status": "stopped",
                    "container_status": container_status,
                }
                
            # Container is running, get the IP address and API status from Lumier API
            logger.info(f"Container {name} is running. Getting VM status from API.")
            
            # Use the shared lume_api_get function directly
            vm_info = lume_api_get(
                vm_name=name,
                host=self.host,
                port=self.api_port,
                storage=storage if storage is not None else self.storage,
                debug=self.verbose,
                verbose=self.verbose
            )
            
            # Check for API errors
            if "error" in vm_info:
                # Use debug level instead of warning to reduce log noise during polling
                logger.debug(f"API request error: {vm_info['error']}")
                return {
                    "name": name,
                    "status": "running",  # Container is running even if API is not responsive
                    "api_status": "error",
                    "error": vm_info["error"],
                    "container_status": container_status
                }
                
            # Process the VM status information
            vm_status = vm_info.get("status", "unknown")
            vnc_url = vm_info.get("vncUrl", "")
            ip_address = vm_info.get("ipAddress", "")
            
            # IMPORTANT: Always ensure we have a valid IP address for connectivity
            # If the API doesn't return an IP address, default to localhost (127.0.0.1)
            # This makes the behavior consistent with LumeProvider
            if not ip_address and vm_status == "running":
                ip_address = "127.0.0.1"
                logger.info(f"No IP address returned from API, defaulting to {ip_address}")
                vm_info["ipAddress"] = ip_address
            
            logger.info(f"VM {name} status: {vm_status}")
            
            if ip_address and vnc_url:
                logger.info(f"VM {name} has IP: {ip_address} and VNC URL: {vnc_url}")
            elif not ip_address and not vnc_url and vm_status != "running":
                # Not running is expected in this case
                logger.info(f"VM {name} is not running yet. Status: {vm_status}")
            else:
                # Missing IP or VNC but status is running - this is unusual but handled with default IP
                logger.warning(f"VM {name} is running but missing expected fields. API response: {vm_info}")
            
            # Return the full status information
            return {
                "name": name,
                "status": vm_status,
                "ip_address": ip_address,
                "vnc_url": vnc_url,
                "api_status": "ok",
                "container_status": container_status,
                **vm_info  # Include all fields from the API response
            }
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to check container status: {e}")
            return {
                "name": name,
                "status": "error",
                "error": f"Failed to check container status: {str(e)}"
            }
    
    async def list_vms(self) -> List[Dict[str, Any]]:
        """List all VMs managed by this provider.
        
        For Lumier provider, there is only one VM per container.
        """
        try:
            status = await self.get_vm("default")
            return [status] if status.get("status") != "unknown" else []
        except Exception as e:
            logger.error(f"Failed to list VMs: {e}")
            return []
    
    async def run_vm(self, name: str, run_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Run a VM with the given options.
        
        Args:
            name: Name of the VM to run (used for the container name and Docker image tag)
            run_opts: Options for running the VM, including:
                - cpu: Number of CPU cores
                - memory: Amount of memory (e.g. "8GB")
                - noVNC_port: Specific port for noVNC interface
        
        Returns:
            Dictionary with VM status information
        """
        # Set the container name using the VM name for consistency
        self.container_name = name or "lumier1-vm"
        try:
            # First, check if container already exists and remove it
            try:
                check_cmd = ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.ID}}"]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True)
                existing_container = check_result.stdout.strip()
                
                if existing_container:
                    logger.info(f"Removing existing container: {self.container_name}")
                    remove_cmd = ["docker", "rm", "-f", self.container_name]
                    subprocess.run(remove_cmd, check=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Error removing existing container: {e}")
                # Continue anyway, next steps will fail if there's a real problem
            
            # Prepare the Docker run command
            cmd = ["docker", "run", "-d", "--name", self.container_name]
            
            cmd.extend(["-p", f"{self.vnc_port}:8006"])
            print(f"Using specified noVNC_port: {self.vnc_port}")
                
            # Set API URL using the API port
            self._api_url = f"http://{self.host}:{self.api_port}"
            
            # Parse memory setting
            memory_mb = self._parse_memory(run_opts.get("memory", "8GB"))
            
            # Add storage volume mount if storage is specified (for persistent VM storage)
            if self.storage and self.storage != "ephemeral":
                # Create storage directory if it doesn't exist
                storage_dir = os.path.abspath(os.path.expanduser(self.storage or ""))
                os.makedirs(storage_dir, exist_ok=True)
                
                # Add volume mount for storage
                cmd.extend([
                    "-v", f"{storage_dir}:/storage", 
                    "-e", f"HOST_STORAGE_PATH={storage_dir}"
                ])
                print(f"Using persistent storage at: {storage_dir}")
            
            # Add shared folder volume mount if shared_path is specified
            if self.shared_path:
                # Create shared directory if it doesn't exist
                shared_dir = os.path.abspath(os.path.expanduser(self.shared_path or ""))
                os.makedirs(shared_dir, exist_ok=True)
                
                # Add volume mount for shared folder
                cmd.extend([
                    "-v", f"{shared_dir}:/shared",
                    "-e", f"HOST_SHARED_PATH={shared_dir}"
                ])
                print(f"Using shared folder at: {shared_dir}")
            
            # Add environment variables
            # Always use the container_name as the VM_NAME for consistency
            # Use the VM image passed from the Computer class
            print(f"Using VM image: {self.vm_image}")
            
            cmd.extend([
                "-e", f"VM_NAME={self.container_name}",
                "-e", f"VERSION=ghcr.io/trycua/{self.vm_image}",
                "-e", f"CPU_CORES={run_opts.get('cpu', '4')}",
                "-e", f"RAM_SIZE={memory_mb}",
            ])
            
            # Specify the Lumier image with the full image name
            lumier_image = "trycua/lumier:latest"
            
            # First check if the image exists locally
            try:
                print(f"Checking if Docker image {lumier_image} exists locally...")
                check_image_cmd = ["docker", "image", "inspect", lumier_image]
                subprocess.run(check_image_cmd, capture_output=True, check=True)
                print(f"Docker image {lumier_image} found locally.")
            except subprocess.CalledProcessError:
                # Image doesn't exist locally
                print(f"\nWARNING: Docker image {lumier_image} not found locally.")
                print("The system will attempt to pull it from Docker Hub, which may fail if you have network connectivity issues.")
                print("If the Docker pull fails, you may need to manually pull the image first with:")
                print(f"  docker pull {lumier_image}\n")
            
            # Add the image to the command
            cmd.append(lumier_image)
            
            # Print the Docker command for debugging
            print(f"DOCKER COMMAND: {' '.join(cmd)}")
            
            # Run the container with improved error handling
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                if "no route to host" in str(e.stderr).lower() or "failed to resolve reference" in str(e.stderr).lower():
                    error_msg = (f"Network error while trying to pull Docker image '{lumier_image}'\n"
                                f"Error: {e.stderr}\n\n"
                                f"SOLUTION: Please try one of the following:\n"
                                f"1. Check your internet connection\n"
                                f"2. Pull the image manually with: docker pull {lumier_image}\n"
                                f"3. Check if Docker is running properly\n")
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                raise
            
            # Container started, now check VM status with polling
            print("Container started, checking VM status...")
            print("NOTE: This may take some time while the VM image is being pulled and initialized")
            print("TIP: You can run 'lume logs -f' in another terminal to see the detailed initialization progress")
            
            # Skip waiting for container readiness and just poll get_vm directly
            # Poll the get_vm method indefinitely until the VM is ready with an IP address
            attempt = 0
            consecutive_errors = 0
            vm_running = False
            
            while True:  # Wait indefinitely
                try:
                    # Use longer delays to give the system time to initialize
                    if attempt > 0:
                        # Start with 5s delay, then increase gradually up to 30s for later attempts
                        # But use shorter delays while we're getting API errors
                        if consecutive_errors > 0 and consecutive_errors < 5:
                            wait_time = 3  # Use shorter delays when we're getting API errors
                        else:  
                            wait_time = min(30, 5 + (attempt * 2))
                        
                        print(f"Waiting {wait_time}s before retry #{attempt+1}...")
                        await asyncio.sleep(wait_time)
                    
                    # Try to get VM status
                    print(f"Checking VM status (attempt {attempt+1})...")
                    vm_status = await self.get_vm(name)
                    
                    # Check for API errors
                    if 'error' in vm_status:
                        consecutive_errors += 1
                        error_msg = vm_status.get('error', 'Unknown error')
                        
                        # Only print a user-friendly status message, not the raw error
                        # since _lume_api_get already logged the technical details
                        if consecutive_errors == 1 or attempt % 5 == 0:
                            if 'Empty reply from server' in error_msg:
                                print("API server is starting up - container is running, but API isn't fully initialized yet.")
                                print("This is expected during the initial VM setup - will continue polling...")
                            else:
                                # Don't repeat the exact same error message each time
                                logger.debug(f"API request error (attempt {attempt+1}): {error_msg}")
                                # Just log that we're still working on it
                                if attempt > 3:
                                    print("Still waiting for the API server to become available...")
                            
                        # If we're getting errors but container is running, that's normal during startup
                        if vm_status.get('status') == 'running':
                            if not vm_running:
                                print("Container is running, waiting for the VM within it to become fully ready...")
                                print("This might take a minute while the VM initializes...")
                                vm_running = True
                        
                        # Increase counter and continue
                        attempt += 1
                        continue
                    
                    # Reset consecutive error counter when we get a successful response
                    consecutive_errors = 0
                    
                    # If the VM is running, check if it has an IP address (which means it's fully ready)
                    if vm_status.get('status') == 'running':
                        vm_running = True
                        
                        # Check if we have an IP address, which means the VM is fully ready
                        if 'ip_address' in vm_status and vm_status['ip_address']:
                            print(f"VM is now fully running with IP: {vm_status.get('ip_address')}")
                            if 'vnc_url' in vm_status and vm_status['vnc_url']:
                                print(f"VNC URL: {vm_status.get('vnc_url')}")
                            return vm_status
                        else:
                            print("VM is running but still initializing network interfaces...")
                            print("Waiting for IP address to be assigned...")
                    else:
                        # VM exists but might still be starting up
                        status = vm_status.get('status', 'unknown')
                        print(f"VM found but status is: {status}. Continuing to poll...")
                    
                    # Increase counter for next iteration's delay calculation
                    attempt += 1
                    
                    # If we reach a very large number of attempts, give a reassuring message but continue
                    if attempt % 10 == 0:
                        print(f"Still waiting after {attempt} attempts. This might take several minutes for first-time setup.")
                        if not vm_running and attempt >= 20:
                            print("\nNOTE: First-time VM initialization can be slow as images are downloaded.")
                            print("If this continues for more than 10 minutes, you may want to check:")
                            print("  1. Docker logs with: docker logs " + name)
                            print("  2. If your network can access container registries")
                            print("Press Ctrl+C to abort if needed.\n")
                            
                    # After 150 attempts (likely over 30-40 minutes), return current status
                    if attempt >= 150:
                        print(f"Reached 150 polling attempts. VM status is: {vm_status.get('status', 'unknown')}")
                        print("Returning current VM status, but please check Docker logs if there are issues.")
                        return vm_status
                    
                except Exception as e:
                    # Always continue retrying, but with increasing delays
                    logger.warning(f"Error checking VM status (attempt {attempt+1}): {e}. Will retry.")
                    consecutive_errors += 1
                    
                    # If we've had too many consecutive errors, might be a deeper problem
                    if consecutive_errors >= 10:
                        print(f"\nWARNING: Encountered {consecutive_errors} consecutive errors while checking VM status.")
                        print("You may need to check the Docker container logs or restart the process.")
                        print(f"Error details: {str(e)}\n")
                        
                    # Increase attempt counter for next iteration
                    attempt += 1
                    
                    # After many consecutive errors, add a delay to avoid hammering the system
                    if attempt > 5:
                        error_delay = min(30, 10 + attempt)
                        print(f"Multiple connection errors, waiting {error_delay}s before next attempt...")
                        await asyncio.sleep(error_delay)
        
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to start Lumier container: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
    async def _wait_for_container_ready(self, container_name: str, timeout: int = 90) -> bool:
        """Wait for the Lumier container to be fully ready with a valid API response.
        
        Args:
            container_name: Name of the Docker container to check
            timeout: Maximum time to wait in seconds (default: 90 seconds)
            
        Returns:
            True if the container is running, even if API is not fully ready.
            This allows operations to continue with appropriate fallbacks.
        """
        start_time = time.time()
        api_ready = False
        container_running = False
        
        print(f"Waiting for container {container_name} to be ready (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            # Check if container is running
            try:
                check_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"]
                result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
                container_status = result.stdout.strip()
                
                if container_status and container_status.startswith("Up"):
                    container_running = True
                    print(f"Container {container_name} is running")
                    logger.info(f"Container {container_name} is running with status: {container_status}")
                else:
                    logger.warning(f"Container {container_name} not yet running, status: {container_status}")
                    # container is not running yet, wait and try again
                    await asyncio.sleep(2)  # Longer sleep to give Docker time
                    continue
            except subprocess.CalledProcessError as e:
                logger.warning(f"Error checking container status: {e}")
                await asyncio.sleep(2)
                continue
                
            # Container is running, check if API is responsive
            try:
                # First check the health endpoint
                api_url = f"http://{self.host}:{self.api_port}/health"
                logger.info(f"Checking API health at: {api_url}")
                
                # Use longer timeout for API health check since it may still be initializing
                curl_cmd = ["curl", "-s", "--connect-timeout", "5", "--max-time", "10", api_url]
                result = subprocess.run(curl_cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and "ok" in result.stdout.lower():
                    api_ready = True
                    print(f"API is ready at {api_url}")
                    logger.info(f"API is ready at {api_url}")
                    break
                else:
                    # API health check failed, now let's check if the VM status endpoint is responsive
                    # This covers cases where the health endpoint isn't implemented but the VM API is working
                    vm_api_url = f"http://{self.host}:{self.api_port}/lume/vms/{container_name}"
                    if self.storage:
                        import urllib.parse
                        encoded_storage = urllib.parse.quote_plus(self.storage)
                        vm_api_url += f"?storage={encoded_storage}"
                        
                    curl_vm_cmd = ["curl", "-s", "--connect-timeout", "5", "--max-time", "10", vm_api_url]
                    vm_result = subprocess.run(curl_vm_cmd, capture_output=True, text=True)
                    
                    if vm_result.returncode == 0 and vm_result.stdout.strip():
                        # VM API responded with something - consider the API ready
                        api_ready = True
                        print(f"VM API is ready at {vm_api_url}")
                        logger.info(f"VM API is ready at {vm_api_url}")
                        break
                    else:
                        curl_code = result.returncode
                        if curl_code == 0:
                            curl_code = vm_result.returncode
                            
                        # Map common curl error codes to helpful messages
                        if curl_code == 7:
                            curl_error = "Failed to connect - API server is starting up"
                        elif curl_code == 22:
                            curl_error = "HTTP error returned from API server"
                        elif curl_code == 28:
                            curl_error = "Operation timeout - API server is slow to respond"
                        elif curl_code == 52:
                            curl_error = "Empty reply from server - API is starting but not ready"
                        elif curl_code == 56:
                            curl_error = "Network problem during data transfer"
                        else:
                            curl_error = f"Unknown curl error code: {curl_code}"
                            
                        print(f"API not ready yet: {curl_error}")
                        logger.info(f"API not ready yet: {curl_error}")
            except subprocess.SubprocessError as e:
                logger.warning(f"Error checking API status: {e}")
                
            # If the container is running but API is not ready, that's OK - we'll just wait
            # a bit longer before checking again, as the container may still be initializing
            elapsed_seconds = time.time() - start_time
            if int(elapsed_seconds) % 5 == 0:  # Only print status every 5 seconds to reduce verbosity
                print(f"Waiting for API to initialize... ({elapsed_seconds:.1f}s / {timeout}s)")
            
            await asyncio.sleep(3)  # Longer sleep between API checks
        
        # Handle timeout - if the container is running but API is not ready, that's not
        # necessarily an error - the API might just need more time to start up
        if not container_running:
            print(f"Timed out waiting for container {container_name} to start")
            logger.warning(f"Timed out waiting for container {container_name} to start")
            return False
        
        if not api_ready:
            print(f"Container {container_name} is running, but API is not fully ready yet.")
            print("Proceeding with operations. API will become available shortly.")
            print("NOTE: You may see some 'API request failed' messages while the API initializes.")
            logger.warning(f"Container {container_name} is running, but API is not fully ready yet.")
        
        # Return True if container is running, even if API isn't ready yet
        # This allows VM operations to proceed, with appropriate retries for API calls
        return container_running

    async def stop_vm(self, name: str, storage: Optional[str] = None) -> Dict[str, Any]:
        """Stop a running VM by stopping the Lumier container."""
        try:
            # Use Docker commands to stop the container directly
            if hasattr(self, '_container_id') and self._container_id:
                logger.info(f"Stopping Lumier container: {self.container_name}")
                cmd = ["docker", "stop", self.container_name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.info(f"Container stopped: {result.stdout.strip()}")
                
                # Return minimal status info
                return {
                    "name": name,
                    "status": "stopped",
                    "container_id": self._container_id,
                }
            else:
                # Try to find the container by name
                check_cmd = ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.ID}}"]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True)
                container_id = check_result.stdout.strip()
                
                if container_id:
                    logger.info(f"Found container ID: {container_id}")
                    cmd = ["docker", "stop", self.container_name]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    logger.info(f"Container stopped: {result.stdout.strip()}")
                    
                    return {
                        "name": name,
                        "status": "stopped",
                        "container_id": container_id,
                    }
                else:
                    logger.warning(f"No container found with name {self.container_name}")
                    return {
                        "name": name,
                        "status": "unknown",
                    }
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to stop container: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(f"Failed to stop Lumier container: {error_msg}")
            
    # update_vm is not implemented as it's not needed for Lumier
    # The BaseVMProvider requires it, so we provide a minimal implementation
    async def update_vm(self, name: str, update_opts: Dict[str, Any], storage: Optional[str] = None) -> Dict[str, Any]:
        """Not implemented for Lumier provider."""
        logger.warning("update_vm is not implemented for Lumier provider")
        return {"name": name, "status": "unchanged"}
    
    async def __aenter__(self):
        """Async context manager entry.
        
        This method is called when entering an async context manager block.
        Returns self to be used in the context.
        """
        logger.debug("Entering LumierProvider context")
        
        # Initialize the API URL with the default value if not already set
        # This ensures get_vm can work before run_vm is called
        if not hasattr(self, '_api_url') or not self._api_url:
            self._api_url = f"http://{self.host}:{self.api_port}"
            logger.info(f"Initialized default Lumier API URL: {self._api_url}")
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.
        
        This method is called when exiting an async context manager block.
        It handles proper cleanup of resources, including stopping any running containers.
        """
        logger.debug(f"Exiting LumierProvider context, handling exceptions: {exc_type}")
        try:
            # If we have a container ID, we should stop it to clean up resources
            if hasattr(self, '_container_id') and self._container_id:
                logger.info(f"Stopping Lumier container on context exit: {self.container_name}")
                try:
                    cmd = ["docker", "stop", self.container_name]
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    logger.info(f"Container stopped during context exit: {self.container_name}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to stop container during cleanup: {e.stderr}")
                    # Don't raise an exception here, we want to continue with cleanup
        except Exception as e:
            logger.error(f"Error during LumierProvider cleanup: {e}")
            # We don't want to suppress the original exception if there was one
            if exc_type is None:
                raise
        # Return False to indicate that any exception should propagate
        return False
