"""Omni tool manager implementation."""

from typing import Dict, List, Any
from enum import Enum

from computer.computer import Computer

from ....core.tools import BaseToolManager
from ....core.tools.collection import ToolCollection

from .bash import OmniBashTool
from .computer import OmniComputerTool
from .edit import OmniEditTool


class ProviderType(Enum):
    """Supported provider types."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CLAUDE = "claude"  # Alias for Anthropic
    GPT = "gpt"  # Alias for OpenAI


class OmniToolManager(BaseToolManager):
    """Tool manager for multi-provider support."""

    def __init__(self, computer: Computer):
        """Initialize Omni tool manager.

        Args:
            computer: Computer instance for tools
        """
        super().__init__(computer)
        # Initialize tools
        self.computer_tool = OmniComputerTool(self.computer)
        self.bash_tool = OmniBashTool(self.computer)
        self.edit_tool = OmniEditTool(self.computer)

    def _initialize_tools(self) -> ToolCollection:
        """Initialize all available tools."""
        return ToolCollection(self.computer_tool, self.bash_tool, self.edit_tool)

    async def _initialize_tools_specific(self) -> None:
        """Initialize provider-specific tool requirements."""
        await self.computer_tool.initialize_dimensions()

    def get_tool_params(self) -> List[Dict[str, Any]]:
        """Get tool parameters for API calls.

        Returns:
            List of tool parameters in default format
        """
        if self.tools is None:
            raise RuntimeError("Tools not initialized. Call initialize() first.")
        return self.tools.to_params()

    def get_provider_tools(self, provider: ProviderType) -> List[Dict[str, Any]]:
        """Get tools formatted for a specific provider.

        Args:
            provider: Provider type to format tools for

        Returns:
            List of tool parameters in provider-specific format
        """
        if self.tools is None:
            raise RuntimeError("Tools not initialized. Call initialize() first.")

        # Default is the base implementation
        tools = self.tools.to_params()

        # Customize for each provider if needed
        if provider in [ProviderType.ANTHROPIC, ProviderType.CLAUDE]:
            # Format for Anthropic API
            # Additional adjustments can be made here
            pass
        elif provider in [ProviderType.OPENAI, ProviderType.GPT]:
            # Format for OpenAI API
            # Future implementation
            pass

        return tools
