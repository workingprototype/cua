"""Interface for tracing functionality."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ITracingManager(ABC):
    """Interface for tracing managers that can log events and attachments."""
    
    @abstractmethod
    def log(self, key: str, data: Dict[str, Any]) -> None:
        """Log an event with structured data.
        
        Args:
            key: Event key/type identifier
            data: Event data dictionary
        """
        pass
    
    @abstractmethod
    def add_attachment(self, path: str, content: bytes) -> None:
        """Add a binary attachment to the trace.
        
        Args:
            path: Relative path for the attachment within the trace
            content: Binary content of the attachment
        """
        pass
    
    @property
    @abstractmethod
    def is_tracing(self) -> bool:
        """Check if tracing is currently active."""
        pass
