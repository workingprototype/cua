"""Omni callback manager implementation."""

import logging
from typing import Any, Dict, Optional, Set

from ...core.callbacks import BaseCallbackManager, ContentCallback, ToolCallback, APICallback
from ...types.tools import ToolResult

logger = logging.getLogger(__name__)

class OmniCallbackManager(BaseCallbackManager):
    """Callback manager for multi-provider support."""
    
    def __init__(
        self,
        content_callback: ContentCallback,
        tool_callback: ToolCallback,
        api_callback: APICallback,
    ):
        """Initialize Omni callback manager.
        
        Args:
            content_callback: Callback for content updates
            tool_callback: Callback for tool execution results
            api_callback: Callback for API interactions
        """
        super().__init__(
            content_callback=content_callback,
            tool_callback=tool_callback,
            api_callback=api_callback
        )
        self._active_tools: Set[str] = set()
    
    def on_content(self, content: Any) -> None:
        """Handle content updates.
        
        Args:
            content: Content update data
        """
        logger.debug(f"Content update: {content}")
        self.content_callback(content)
    
    def on_tool_result(self, result: ToolResult, tool_id: str) -> None:
        """Handle tool execution results.
        
        Args:
            result: Tool execution result
            tool_id: ID of the tool
        """
        logger.debug(f"Tool result for {tool_id}: {result}")
        self.tool_callback(result, tool_id)
    
    def on_api_interaction(
        self,
        request: Any,
        response: Any,
        error: Optional[Exception] = None
    ) -> None:
        """Handle API interactions.
        
        Args:
            request: API request data
            response: API response data
            error: Optional error that occurred
        """
        if error:
            logger.error(f"API error: {str(error)}")
        else:
            logger.debug(f"API interaction - Request: {request}, Response: {response}")
        self.api_callback(request, response, error)
    
    def get_active_tools(self) -> Set[str]:
        """Get currently active tools.
        
        Returns:
            Set of active tool names
        """
        return self._active_tools.copy()
