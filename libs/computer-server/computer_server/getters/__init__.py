import os
import importlib
from pathlib import Path

# Auto-import all getter modules
getter_dir = Path(__file__).parent
for file in getter_dir.glob("*.py"):
    if file.name not in ["__init__.py", "base.py"]:
        module_name = file.stem
        try:
            importlib.import_module(f".{module_name}", package=__name__)
        except ImportError as e:
            # Silently skip modules that can't be imported (e.g., missing dependencies)
            pass

# Export the main functions
from .base import getter, get_available_getters, execute_getter, GETTER_REGISTRY

__all__ = ["getter", "get_available_getters", "execute_getter", "GETTER_REGISTRY"]
