"""Unified computer agent implementation that supports multiple loops."""

import os
import logging
import asyncio
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING, Union, cast
from datetime import datetime
from enum import Enum

from computer import Computer

from ..types.base import Provider, AgentLoop
from .base_agent import BaseComputerAgent
from ..core.telemetry import record_agent_initialization

# Only import types for type checking to avoid circular imports
if TYPE_CHECKING:
    from ..providers.anthropic.loop import AnthropicLoop
    from ..providers.omni.loop import OmniLoop
    from ..providers.omni.parser import OmniParser

# Import the provider types
from ..providers.omni.types import LLMProvider, LLM, Model, LLMModel

logger = logging.getLogger(__name__)

# Default models for different providers
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.ANTHROPIC: "claude-3-7-sonnet-20250219",
}

# Map providers to their environment variable names
ENV_VARS = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
}


class ComputerAgent(BaseComputerAgent):
    """Unified implementation of the computer agent supporting multiple loop types.

    This class consolidates the previous AnthropicComputerAgent and OmniComputerAgent
    into a single implementation with configurable loop type.
    """

    def __init__(
        self,
        computer: Computer,
        loop: AgentLoop = AgentLoop.OMNI,
        model: Optional[Union[LLM, Dict[str, str], str]] = None,
        api_key: Optional[str] = None,
        save_trajectory: bool = True,
        trajectory_dir: Optional[str] = "trajectories",
        only_n_most_recent_images: Optional[int] = None,
        max_retries: int = 3,
        verbosity: int = logging.INFO,
        telemetry_enabled: bool = True,
        **kwargs,
    ):
        """Initialize a ComputerAgent instance.

        Args:
            computer: The Computer instance to control
            loop: The agent loop to use: ANTHROPIC or OMNI
            model: The model to use. Can be a string, dict or LLM object.
                  Defaults to LLM for the loop type.
            api_key: The API key to use. If None, will use environment variables.
            save_trajectory: Whether to save the trajectory.
            trajectory_dir: The directory to save trajectories to.
            only_n_most_recent_images: Only keep this many most recent images.
            max_retries: Maximum number of retries for failed requests.
            verbosity: Logging level (standard Python logging levels).
            telemetry_enabled: Whether to enable telemetry tracking. Defaults to True.
            **kwargs: Additional keyword arguments to pass to the loop.
        """
        super().__init__(computer)
        self._configure_logging(verbosity)
        logger.info(f"Initializing ComputerAgent with {loop} loop")

        # Store telemetry preference
        self.telemetry_enabled = telemetry_enabled

        # Process the model configuration
        self.model = self._process_model_config(model, loop)
        self.loop_type = loop
        self.api_key = api_key

        # Store computer
        self.computer = computer

        # Save trajectory settings
        self.save_trajectory = save_trajectory
        self.trajectory_dir = trajectory_dir
        self.only_n_most_recent_images = only_n_most_recent_images

        # Store the max retries setting
        self.max_retries = max_retries

        # Initialize message history
        self.messages = []

        # Extra kwargs for the loop
        self.loop_kwargs = kwargs

        # Initialize the actual loop implementation
        self.loop = self._init_loop()

        # Record initialization in telemetry if enabled
        if telemetry_enabled:
            record_agent_initialization()

    def _process_model_config(
        self, model_input: Optional[Union[LLM, Dict[str, str], str]], loop: AgentLoop
    ) -> LLM:
        """Process and normalize model configuration.

        Args:
            model_input: Input model configuration (LLM, dict, string, or None)
            loop: The loop type being used

        Returns:
            Normalized LLM instance
        """
        # Handle case where model_input is None
        if model_input is None:
            # Use Anthropic for Anthropic loop, OpenAI for Omni loop
            default_provider = (
                LLMProvider.ANTHROPIC if loop == AgentLoop.ANTHROPIC else LLMProvider.OPENAI
            )
            return LLM(provider=default_provider)

        # Handle case where model_input is already a LLM or one of its aliases
        if isinstance(model_input, (LLM, Model, LLMModel)):
            return model_input

        # Handle case where model_input is a dict
        if isinstance(model_input, dict):
            provider = model_input.get("provider", LLMProvider.OPENAI)
            if isinstance(provider, str):
                provider = LLMProvider(provider)
            return LLM(provider=provider, name=model_input.get("name"))

        # Handle case where model_input is a string (model name)
        if isinstance(model_input, str):
            default_provider = (
                LLMProvider.ANTHROPIC if loop == AgentLoop.ANTHROPIC else LLMProvider.OPENAI
            )
            return LLM(provider=default_provider, name=model_input)

        raise ValueError(f"Unsupported model configuration: {model_input}")

    def _configure_logging(self, verbosity: int):
        """Configure logging based on verbosity level."""
        # Use the logging level directly without mapping
        logger.setLevel(verbosity)
        logging.getLogger("agent").setLevel(verbosity)

        # Log the verbosity level that was set
        if verbosity <= logging.DEBUG:
            logger.info("Agent logging set to DEBUG level (full debug information)")
        elif verbosity <= logging.INFO:
            logger.info("Agent logging set to INFO level (standard output)")
        elif verbosity <= logging.WARNING:
            logger.warning("Agent logging set to WARNING level (warnings and errors only)")
        elif verbosity <= logging.ERROR:
            logger.warning("Agent logging set to ERROR level (errors only)")
        elif verbosity <= logging.CRITICAL:
            logger.warning("Agent logging set to CRITICAL level (critical errors only)")

    def _init_loop(self) -> Any:
        """Initialize the loop based on the loop_type.

        Returns:
            Initialized loop instance
        """
        # Lazy import OmniLoop and OmniParser to avoid circular imports
        from ..providers.omni.loop import OmniLoop
        from ..providers.omni.parser import OmniParser

        if self.loop_type == AgentLoop.ANTHROPIC:
            from ..providers.anthropic.loop import AnthropicLoop

            # Ensure we always have a valid model name
            model_name = self.model.name or DEFAULT_MODELS[LLMProvider.ANTHROPIC]

            return AnthropicLoop(
                api_key=self.api_key,
                model=model_name,
                computer=self.computer,
                save_trajectory=self.save_trajectory,
                base_dir=self.trajectory_dir,
                only_n_most_recent_images=self.only_n_most_recent_images,
                **self.loop_kwargs,
            )

        # Initialize parser for OmniLoop with appropriate device
        if "parser" not in self.loop_kwargs:
            self.loop_kwargs["parser"] = OmniParser()

        # Ensure we always have a valid model name
        model_name = self.model.name or DEFAULT_MODELS[self.model.provider]

        return OmniLoop(
            provider=self.model.provider,
            api_key=self.api_key,
            model=model_name,
            computer=self.computer,
            save_trajectory=self.save_trajectory,
            base_dir=self.trajectory_dir,
            only_n_most_recent_images=self.only_n_most_recent_images,
            **self.loop_kwargs,
        )

    async def _execute_task(self, task: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a task using the appropriate agent loop.

        Args:
            task: The task to execute

        Returns:
            AsyncGenerator yielding task outputs
        """
        logger.info(f"Executing task: {task}")

        try:
            # Create a message from the task
            task_message = {"role": "user", "content": task}
            messages_with_task = self.messages + [task_message]

            # Use the run method of the loop
            async for output in self.loop.run(messages_with_task):
                yield output
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            raise
        finally:
            pass

    async def _execute_action(self, action_type: str, **action_params) -> Any:
        """Execute an action with telemetry tracking."""
        try:
            # Execute the action
            result = await super()._execute_action(action_type, **action_params)
            return result
        except Exception as e:
            logger.exception(f"Error executing action {action_type}: {e}")
            raise
        finally:
            pass
