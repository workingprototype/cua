from typing import Dict, Any, List, Callable, Optional, Union
from functools import wraps
import platform

# Registry to store all getters
GETTER_REGISTRY: Dict[str, List[Dict[str, Any]]] = {}

def getter(
    name: str,
    os: Optional[Union[str, List[str]]] = None,
    applications: Optional[Union[str, List[str]]] = None,
    description: str = ""
):
    """
    Decorator to register a getter function.
    
    Args:
        name: Unique name for the getter (e.g., "safari_html", "chrome_tabs")
        os: Supported OS names "macos", "linux", "windows", ["macos", "linux"], or None for all
        applications: Required applications "Safari", ["Safari", "Chrome"], or "all" for any
        description: Human-readable description of what this getter returns
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Normalize os and applications to lists
        os_list = []
        if os is None:
            os_list = ["all"]
        elif isinstance(os, str):
            os_list = [os]
        else:
            os_list = os
            
        app_list = []
        if applications is None:
            app_list = ["all"]
        elif isinstance(applications, str):
            app_list = [applications]
        else:
            app_list = applications
        
        # Register the getter
        getter_info = {
            "name": name,
            "function": wrapper,
            "os": os_list,
            "applications": app_list,
            "description": description
        }
        
        if name not in GETTER_REGISTRY:
            GETTER_REGISTRY[name] = []
        GETTER_REGISTRY[name].append(getter_info)
        
        return wrapper
    return decorator

def get_available_getters(current_os: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get list of available getters with their metadata for the current OS."""
    if current_os is None:
        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "macos"
    
    available = []
    for name, getters in GETTER_REGISTRY.items():
        for getter_info in getters:
            if current_os in getter_info["os"] or "all" in getter_info["os"]:
                available.append({
                    "name": name,
                    "description": getter_info["description"],
                    "applications": getter_info["applications"]
                })
                break
    
    return available

def execute_getter(name: str, **kwargs) -> Dict[str, Any]:
    """Execute a registered getter by name."""
    if name not in GETTER_REGISTRY:
        return {"error": f"Getter '{name}' not found"}
    
    current_os = platform.system().lower()
    if current_os == "darwin":
        current_os = "macos"
    
    # Find compatible getter
    for getter_info in GETTER_REGISTRY[name]:
        if current_os in getter_info["os"] or "all" in getter_info["os"]:
            try:
                result = getter_info["function"](**kwargs)
                # Ensure we always return a dict with success/error
                if isinstance(result, dict) and ("error" in result or "data" in result):
                    return result
                else:
                    return {"data": result}
            except Exception as e:
                return {"error": str(e)}
    
    return {"error": f"Getter '{name}' not available on {current_os}"}
