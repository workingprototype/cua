"""Main entry point for computer agents."""

import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Dict, Optional, cast, List

from computer import Computer
from ..providers.anthropic.loop import AnthropicLoop
from ..providers.omni.loop import OmniLoop
from ..providers.omni.parser import OmniParser
from ..providers.omni.types import LLMProvider, LLM
from .. import AgentLoop
from .messages import StandardMessageManager, ImageRetentionConfig

logging.basicConfig(level=logging.INFO)
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


class ComputerAgent:
    """A computer agent that can perform automated tasks using natural language instructions."""

    def __init__(
        self,
        computer: Computer,
        model: LLM,
        loop: AgentLoop,
        max_retries: int = 3,
        screenshot_dir: Optional[str] = None,
        log_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        save_trajectory: bool = True,
        trajectory_dir: str = "trajectories",
        only_n_most_recent_images: Optional[int] = None,
        verbosity: int = logging.INFO,
    ):
        """Initialize the ComputerAgent.

        Args:
            computer: Computer instance. If not provided, one will be created with default settings.
            max_retries: Maximum number of retry attempts.
            screenshot_dir: Directory to save screenshots.
            log_dir: Directory to save logs (set to None to disable logging to files).
            model: LLM object containing provider and model name. Takes precedence over provider/model_name.
            provider: The AI provider to use (e.g., LLMProvider.ANTHROPIC). Only used if model is None.
            api_key: The API key for the provider. If not provided, will look for environment variable.
            model_name: The model name to use. Only used if model is None.
            save_trajectory: Whether to save the trajectory.
            trajectory_dir: Directory to save the trajectory.
            only_n_most_recent_images: Maximum number of recent screenshots to include in API requests.
            verbosity: Logging level.
        """
        # Basic agent configuration
        self.max_retries = max_retries
        self.computer = computer or Computer()
        self.queue = asyncio.Queue()
        self.screenshot_dir = screenshot_dir
        self.log_dir = log_dir
        self._retry_count = 0
        self._initialized = False
        self._in_context = False

        # Initialize the message manager for standardized message handling
        self.message_manager = StandardMessageManager(
            config=ImageRetentionConfig(num_images_to_keep=only_n_most_recent_images)
        )

        # Set logging level
        logger.setLevel(verbosity)

        # Setup logging
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            logger.info(f"Created logs directory: {self.log_dir}")

        # Setup screenshots directory
        if self.screenshot_dir:
            os.makedirs(self.screenshot_dir, exist_ok=True)
            logger.info(f"Created screenshots directory: {self.screenshot_dir}")

        # Use the provided LLM object
        self.provider = model.provider
        actual_model_name = model.name or DEFAULT_MODELS.get(self.provider, "")

        # Ensure we have a valid model name
        if not actual_model_name:
            actual_model_name = DEFAULT_MODELS.get(self.provider, "")
            if not actual_model_name:
                raise ValueError(
                    f"No model specified for provider {self.provider} and no default found"
                )

        # Ensure computer is properly cast for typing purposes
        computer_instance = cast(Computer, self.computer)

        # Get API key from environment if not provided
        actual_api_key = api_key or os.environ.get(ENV_VARS[self.provider], "")
        if not actual_api_key:
            raise ValueError(f"No API key provided for {self.provider}")

        # Initialize the appropriate loop based on the loop parameter
        if loop == AgentLoop.ANTHROPIC:
            self._loop = AnthropicLoop(
                api_key=actual_api_key,
                model=actual_model_name,
                computer=computer_instance,
                save_trajectory=save_trajectory,
                base_dir=trajectory_dir,
                only_n_most_recent_images=only_n_most_recent_images,
            )
        else:
            self._loop = OmniLoop(
                provider=self.provider,
                api_key=actual_api_key,
                model=actual_model_name,
                computer=computer_instance,
                save_trajectory=save_trajectory,
                base_dir=trajectory_dir,
                only_n_most_recent_images=only_n_most_recent_images,
                parser=OmniParser(),
            )

        logger.info(
            f"ComputerAgent initialized with provider: {self.provider}, model: {actual_model_name}"
        )

    async def __aenter__(self):
        """Initialize the agent when used as a context manager."""
        logger.info("Entering ComputerAgent context")
        self._in_context = True

        # In case the computer wasn't initialized
        try:
            # Initialize the computer only if not already initialized
            logger.info("Checking if computer is already initialized...")
            if not self.computer._initialized:
                logger.info("Initializing computer in __aenter__...")
                # Use the computer's __aenter__ directly instead of calling run()
                await self.computer.__aenter__()
                logger.info("Computer initialized in __aenter__")
            else:
                logger.info("Computer already initialized, skipping initialization")

            # Take a test screenshot to verify the computer is working
            logger.info("Testing computer with a screenshot...")
            try:
                test_screenshot = await self.computer.interface.screenshot()
                # Determine the screenshot size based on its type
                if isinstance(test_screenshot, (bytes, bytearray, memoryview)):
                    size = len(test_screenshot)
                elif hasattr(test_screenshot, "base64_image"):
                    size = len(test_screenshot.base64_image)
                else:
                    size = "unknown"
                logger.info(f"Screenshot test successful, size: {size}")
            except Exception as e:
                logger.error(f"Screenshot test failed: {str(e)}")
                # Even though screenshot failed, we continue since some tests might not need it
        except Exception as e:
            logger.error(f"Error initializing computer in __aenter__: {str(e)}")
            raise

        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup agent resources if needed."""
        logger.info("Cleaning up agent resources")
        self._in_context = False

        # Do any necessary cleanup
        # We're not shutting down the computer here as it might be shared
        # Just log that we're exiting
        if exc_type:
            logger.error(f"Exiting agent context with error: {exc_type.__name__}: {exc_val}")
        else:
            logger.info("Exiting agent context normally")

        # If we have a queue, make sure to signal it's done
        if hasattr(self, "queue") and self.queue:
            await self.queue.put(None)  # Signal that we're done

    async def initialize(self) -> None:
        """Initialize the agent and its components."""
        if not self._initialized:
            # Always initialize the computer if available
            if self.computer and not self.computer._initialized:
                await self.computer.run()
            self._initialized = True

    async def _init_if_needed(self):
        """Initialize the computer interface if it hasn't been initialized yet."""
        if not self.computer._initialized:
            logger.info("Computer not initialized, initializing now...")
            try:
                # Call run directly
                await self.computer.run()
                logger.info("Computer interface initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing computer interface: {str(e)}")
                raise

    async def run(self, task: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Run a task using the computer agent.

        Args:
            task: Task description

        Yields:
            Task execution updates
        """
        try:
            logger.info(f"Running task: {task}")
            logger.info(
                f"Message history before task has {len(self.message_manager.messages)} messages"
            )

            # Initialize the computer if needed
            if not self._initialized:
                await self.initialize()

            # Add task as a user message using the message manager
            self.message_manager.add_user_message([{"type": "text", "text": task}])
            logger.info(
                f"Added task message. Message history now has {len(self.message_manager.messages)} messages"
            )

            # Log message history types to help with debugging
            message_types = [
                f"{i}: {msg['role']}" for i, msg in enumerate(self.message_manager.messages)
            ]
            logger.info(f"Message history roles: {', '.join(message_types)}")

            # Pass properly formatted messages to the loop
            if self._loop is None:
                logger.error("Loop not initialized properly")
                yield {"error": "Loop not initialized properly"}
                return

            # Execute the task and yield results
            async for result in self._loop.run(self.message_manager.messages):
                # Extract the assistant message from the result and add it to our history
                assistant_response = result["response"]["choices"][0].get("message", None)
                if assistant_response and assistant_response.get("role") == "assistant":
                    # Extract the content from the assistant response
                    content = assistant_response.get("content")
                    self.message_manager.add_assistant_message(content)

                    logger.info("Added assistant response to message history")

                # Yield the result to the caller
                yield result

                # Logging the message history for debugging
                logger.info(
                    f"Updated message history now has {len(self.message_manager.messages)} messages"
                )
                message_types = [
                    f"{i}: {msg['role']}" for i, msg in enumerate(self.message_manager.messages)
                ]
                logger.info(f"Updated message history roles: {', '.join(message_types)}")

        except Exception as e:
            logger.error(f"Error in agent run method: {str(e)}")
            yield {
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "metadata": {"title": "❌ Error"},
            }
