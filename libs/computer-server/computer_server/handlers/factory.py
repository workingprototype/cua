import platform
import subprocess
from typing import Tuple, Type
from .base import BaseAccessibilityHandler, BaseAutomationHandler
from computer_server.diorama.base import BaseDioramaHandler

# Conditionally import platform-specific handlers
system = platform.system().lower()
if system == 'darwin':
    from .macos import MacOSAccessibilityHandler, MacOSAutomationHandler
    from computer_server.diorama.macos import MacOSDioramaHandler
elif system == 'linux':
    from .linux import LinuxAccessibilityHandler, LinuxAutomationHandler

class HandlerFactory:
    """Factory for creating OS-specific handlers."""
    
    @staticmethod
    def _get_current_os() -> str:
        """Determine the current OS.
        
        Returns:
            str: The OS type ('darwin' for macOS or 'linux' for Linux)
            
        Raises:
            RuntimeError: If unable to determine the current OS
        """
        try:
            # Use platform.system() as primary method
            system = platform.system().lower()
            if system in ['darwin', 'linux', 'windows']:
                return 'darwin' if system == 'darwin' else 'linux' if system == 'linux' else 'windows'
                
            # Fallback to uname if platform.system() doesn't return expected values
            result = subprocess.run(['uname', '-s'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"uname command failed: {result.stderr}")
            return result.stdout.strip().lower()
        except Exception as e:
            raise RuntimeError(f"Failed to determine current OS: {str(e)}")
    
    @staticmethod
    def create_handlers() -> Tuple[BaseAccessibilityHandler, BaseAutomationHandler, BaseDioramaHandler]:
        """Create and return appropriate handlers for the current OS.
        
        Returns:
            Tuple[BaseAccessibilityHandler, BaseAutomationHandler, BaseDioramaHandler]: A tuple containing
            the appropriate accessibility, automation, and diorama handlers for the current OS.
        
        Raises:
            NotImplementedError: If the current OS is not supported
            RuntimeError: If unable to determine the current OS
        """
        os_type = HandlerFactory._get_current_os()
        
        if os_type == 'darwin':
            return MacOSAccessibilityHandler(), MacOSAutomationHandler(), MacOSDioramaHandler()
        else:
            return LinuxAccessibilityHandler(), LinuxAutomationHandler(), BaseDioramaHandler()

            raise NotImplementedError(f"OS '{os_type}' is not supported") 