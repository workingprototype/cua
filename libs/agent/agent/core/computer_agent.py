"""Main entry point for computer agents."""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

from computer import Computer
from ..types.base import Provider
from .factory import AgentFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComputerAgent:
    """A computer agent that can perform automated tasks using natural language instructions."""

    def __init__(self, provider: Provider, computer: Optional[Computer] = None, **kwargs):
        """Initialize the ComputerAgent.

        Args:
            provider: The AI provider to use (e.g., Provider.ANTHROPIC)
            computer: Optional Computer instance. If not provided, one will be created with default settings.
            **kwargs: Additional provider-specific arguments
        """
        self.provider = provider
        self._computer = computer
        self._kwargs = kwargs
        self._agent = None
        self._initialized = False
        self._in_context = False

        # Create provider-specific agent using factory
        self._agent = AgentFactory.create(provider=provider, computer=computer, **kwargs)

    async def __aenter__(self):
        """Enter the async context manager."""
        self._in_context = True
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        self._in_context = False

    async def initialize(self) -> None:
        """Initialize the agent and its components."""
        if not self._initialized:
            if not self._in_context and self._computer:
                # If not in context manager but have a computer, initialize it
                await self._computer.run()
            self._initialized = True

    async def run(self, task: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the agent with a given task."""
        if not self._initialized:
            await self.initialize()

        if self._agent is None:
            logger.error("Agent not initialized properly")
            yield {"error": "Agent not initialized properly"}
            return

        async for result in self._agent.run(task):
            yield result

    @property
    def computer(self) -> Optional[Computer]:
        """Get the underlying computer instance."""
        return self._agent.computer if self._agent else None
