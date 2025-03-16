"""Base computer agent implementation."""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

from computer import Computer

from ..types.base import Provider

logger = logging.getLogger(__name__)


class BaseComputerAgent(ABC):
    """Base class for computer agents."""

    def __init__(
        self,
        max_retries: int = 3,
        computer: Optional[Computer] = None,
        screenshot_dir: Optional[str] = None,
        log_dir: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the base computer agent.

        Args:
            max_retries: Maximum number of retry attempts
            computer: Optional Computer instance
            screenshot_dir: Directory to save screenshots
            log_dir: Directory to save logs (set to None to disable logging to files)
            **kwargs: Additional provider-specific arguments
        """
        self.max_retries = max_retries
        self.computer = computer or Computer()
        self.queue = asyncio.Queue()
        self.screenshot_dir = screenshot_dir
        self.log_dir = log_dir
        self._retry_count = 0
        self.provider = Provider.UNKNOWN

        # Setup logging
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            logger.info(f"Created logs directory: {self.log_dir}")

        # Setup screenshots directory
        if self.screenshot_dir:
            os.makedirs(self.screenshot_dir, exist_ok=True)
            logger.info(f"Created screenshots directory: {self.screenshot_dir}")

        logger.info("BaseComputerAgent initialized")

    async def run(self, task: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Run a task using the computer agent.

        Args:
            task: Task description

        Yields:
            Task execution updates
        """
        try:
            logger.info(f"Running task: {task}")

            # Initialize the computer if needed
            await self._init_if_needed()

            # Execute the task and yield results
            # The _execute_task method should be implemented to yield results
            async for result in self._execute_task(task):
                yield result

        except Exception as e:
            logger.error(f"Error in agent run method: {str(e)}")
            yield {
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "metadata": {"title": "❌ Error"},
            }

    async def _init_if_needed(self):
        """Initialize the computer interface if it hasn't been initialized yet."""
        if not self.computer._initialized:
            logger.info("Computer not initialized, initializing now...")
            try:
                # Call run directly without setting the flag first
                await self.computer.run()
                logger.info("Computer interface initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing computer interface: {str(e)}")
                raise

    async def __aenter__(self):
        """Initialize the agent when used as a context manager."""
        logger.info("Entering BaseComputerAgent context")

        # In case the computer wasn't initialized
        try:
            # Initialize the computer only if not already initialized
            logger.info("Checking if computer is already initialized...")
            if not self.computer._initialized:
                logger.info("Initializing computer in __aenter__...")
                # Use the computer's __aenter__ directly instead of calling run()
                # This avoids the circular dependency
                await self.computer.__aenter__()
                logger.info("Computer initialized in __aenter__")
            else:
                logger.info("Computer already initialized, skipping initialization")

            # Take a test screenshot to verify the computer is working
            logger.info("Testing computer with a screenshot...")
            try:
                test_screenshot = await self.computer.interface.screenshot()
                # Determine the screenshot size based on its type
                if isinstance(test_screenshot, bytes):
                    size = len(test_screenshot)
                else:
                    # Assume it's an object with base64_image attribute
                    try:
                        size = len(test_screenshot.base64_image)
                    except AttributeError:
                        size = "unknown"
                logger.info(f"Screenshot test successful, size: {size}")
            except Exception as e:
                logger.error(f"Screenshot test failed: {str(e)}")
                # Even though screenshot failed, we continue since some tests might not need it
        except Exception as e:
            logger.error(f"Error initializing computer in __aenter__: {str(e)}")
            raise

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup computer resources if needed."""
        logger.info("Cleaning up agent resources")

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

    @abstractmethod
    async def _execute_task(self, task: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a task. Must be implemented by subclasses.

        This is an async method that returns an AsyncGenerator. Implementations
        should use 'yield' statements to produce results asynchronously.
        """
        yield {
            "role": "assistant",
            "content": "Base class method called",
            "metadata": {"title": "Error"},
        }
        raise NotImplementedError("Subclasses must implement _execute_task")
