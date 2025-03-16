"""Callback handlers for agent."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

class ContentCallback(Protocol):
    """Protocol for content callbacks."""
    def __call__(self, content: Dict[str, Any]) -> None: ...

class ToolCallback(Protocol):
    """Protocol for tool callbacks."""
    def __call__(self, result: Any, tool_id: str) -> None: ...

class APICallback(Protocol):
    """Protocol for API callbacks."""
    def __call__(self, request: Any, response: Any, error: Optional[Exception] = None) -> None: ...

class BaseCallbackManager(ABC):
    """Base class for callback managers."""
    
    def __init__(
        self,
        content_callback: ContentCallback,
        tool_callback: ToolCallback,
        api_callback: APICallback,
    ):
        """Initialize the callback manager.
        
        Args:
            content_callback: Callback for content updates
            tool_callback: Callback for tool execution results
            api_callback: Callback for API interactions
        """
        self.content_callback = content_callback
        self.tool_callback = tool_callback
        self.api_callback = api_callback
    
    @abstractmethod
    def on_content(self, content: Any) -> None:
        """Handle content updates."""
        raise NotImplementedError
    
    @abstractmethod
    def on_tool_result(self, result: Any, tool_id: str) -> None:
        """Handle tool execution results."""
        raise NotImplementedError
    
    @abstractmethod
    def on_api_interaction(
        self,
        request: Any,
        response: Any,
        error: Optional[Exception] = None
    ) -> None:
        """Handle API interactions."""
        raise NotImplementedError


class CallbackManager:
    """Manager for callback handlers."""
    
    def __init__(self, handlers: Optional[List["CallbackHandler"]] = None):
        """Initialize with optional handlers.
        
        Args:
            handlers: List of callback handlers
        """
        self.handlers = handlers or []
    
    def add_handler(self, handler: "CallbackHandler") -> None:
        """Add a callback handler.
        
        Args:
            handler: Callback handler to add
        """
        self.handlers.append(handler)
    
    async def on_action_start(self, action: str, **kwargs) -> None:
        """Called when an action starts.
        
        Args:
            action: Action name
            **kwargs: Additional data
        """
        for handler in self.handlers:
            await handler.on_action_start(action, **kwargs)
    
    async def on_action_end(self, action: str, success: bool, **kwargs) -> None:
        """Called when an action ends.
        
        Args:
            action: Action name
            success: Whether the action was successful
            **kwargs: Additional data
        """
        for handler in self.handlers:
            await handler.on_action_end(action, success, **kwargs)
    
    async def on_error(self, error: Exception, **kwargs) -> None:
        """Called when an error occurs.
        
        Args:
            error: Exception that occurred
            **kwargs: Additional data
        """
        for handler in self.handlers:
            await handler.on_error(error, **kwargs)


class CallbackHandler(ABC):
    """Base class for callback handlers."""
    
    @abstractmethod
    async def on_action_start(self, action: str, **kwargs) -> None:
        """Called when an action starts.
        
        Args:
            action: Action name
            **kwargs: Additional data
        """
        pass
    
    @abstractmethod
    async def on_action_end(self, action: str, success: bool, **kwargs) -> None:
        """Called when an action ends.
        
        Args:
            action: Action name
            success: Whether the action was successful
            **kwargs: Additional data
        """
        pass
    
    @abstractmethod
    async def on_error(self, error: Exception, **kwargs) -> None:
        """Called when an error occurs.
        
        Args:
            error: Exception that occurred
            **kwargs: Additional data
        """
        pass 