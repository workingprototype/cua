import platform
import subprocess
from typing import Tuple, Type
from .base import BaseAccessibilityHandler, BaseAutomationHandler
from .macos import MacOSAccessibilityHandler, MacOSAutomationHandler
# from .linux import LinuxAccessibilityHandler, LinuxAutomationHandler

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
            # Use uname -s to determine OS since this runs on the target machine
            result = subprocess.run(['uname', '-s'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"uname command failed: {result.stderr}")
            return result.stdout.strip().lower()
        except Exception as e:
            raise RuntimeError(f"Failed to determine current OS: {str(e)}")
    
    @staticmethod
    def create_handlers() -> Tuple[BaseAccessibilityHandler, BaseAutomationHandler]:
        """Create and return appropriate handlers for the current OS.
        
        Returns:
            Tuple[BaseAccessibilityHandler, BaseAutomationHandler]: A tuple containing
            the appropriate accessibility and automation handlers for the current OS.
            
        Raises:
            NotImplementedError: If the current OS is not supported
            RuntimeError: If unable to determine the current OS
        """
        os_type = HandlerFactory._get_current_os()
        
        if os_type == 'darwin':
            return MacOSAccessibilityHandler(), MacOSAutomationHandler()
        # elif os_type == 'linux':
        #     return LinuxAccessibilityHandler(), LinuxAutomationHandler()
        else:
            raise NotImplementedError(f"OS '{os_type}' is not supported") 