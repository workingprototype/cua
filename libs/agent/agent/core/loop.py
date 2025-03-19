"""Base agent loop implementation."""

import logging
import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from datetime import datetime
import base64

from computer import Computer
from .experiment import ExperimentManager

logger = logging.getLogger(__name__)


class BaseLoop(ABC):
    """Base class for agent loops that handle message processing and tool execution."""

    def __init__(
        self,
        computer: Computer,
        model: str,
        api_key: str,
        max_tokens: int = 4096,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        base_dir: Optional[str] = "trajectories",
        save_trajectory: bool = True,
        only_n_most_recent_images: Optional[int] = 2,
        **kwargs,
    ):
        """Initialize base agent loop.

        Args:
            computer: Computer instance to control
            model: Model name to use
            api_key: API key for provider
            max_tokens: Maximum tokens to generate
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            base_dir: Base directory for saving experiment data
            save_trajectory: Whether to save trajectory data
            only_n_most_recent_images: Maximum number of recent screenshots to include in API requests
            **kwargs: Additional provider-specific arguments
        """
        self.computer = computer
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.base_dir = base_dir
        self.save_trajectory = save_trajectory
        self.only_n_most_recent_images = only_n_most_recent_images
        self._kwargs = kwargs
        self.message_history = []
        # self.tool_manager = BaseToolManager(computer)

        # Initialize experiment manager
        if self.save_trajectory and self.base_dir:
            self.experiment_manager = ExperimentManager(
                base_dir=self.base_dir,
                only_n_most_recent_images=only_n_most_recent_images,
            )
            # Track directories for convenience
            self.run_dir = self.experiment_manager.run_dir
            self.current_turn_dir = self.experiment_manager.current_turn_dir
        else:
            self.experiment_manager = None
            self.run_dir = None
            self.current_turn_dir = None

        # Initialize basic tracking
        self.turn_count = 0

    def _setup_experiment_dirs(self) -> None:
        """Setup the experiment directory structure."""
        if self.experiment_manager:
            # Use the experiment manager to set up directories
            self.experiment_manager.setup_experiment_dirs()

            # Update local tracking variables
            self.run_dir = self.experiment_manager.run_dir
            self.current_turn_dir = self.experiment_manager.current_turn_dir

    def _create_turn_dir(self) -> None:
        """Create a new directory for the current turn."""
        if self.experiment_manager:
            # Use the experiment manager to create the turn directory
            self.experiment_manager.create_turn_dir()

            # Update local tracking variables
            self.current_turn_dir = self.experiment_manager.current_turn_dir
            self.turn_count = self.experiment_manager.turn_count

    def _log_api_call(
        self, call_type: str, request: Any, response: Any = None, error: Optional[Exception] = None
    ) -> None:
        """Log API call details to file.

        Args:
            call_type: Type of API call (e.g., 'request', 'response', 'error')
            request: The API request data
            response: Optional API response data
            error: Optional error information
        """
        if self.experiment_manager:
            # Use the experiment manager to log the API call
            provider = getattr(self, "provider", "unknown")
            provider_str = str(provider) if provider else "unknown"

            self.experiment_manager.log_api_call(
                call_type=call_type,
                request=request,
                provider=provider_str,
                model=self.model,
                response=response,
                error=error,
            )

    def _save_screenshot(self, img_base64: str, action_type: str = "") -> None:
        """Save a screenshot to the experiment directory.

        Args:
            img_base64: Base64 encoded screenshot
            action_type: Type of action that triggered the screenshot
        """
        if self.experiment_manager:
            self.experiment_manager.save_screenshot(img_base64, action_type)

    async def initialize(self) -> None:
        """Initialize both the API client and computer interface with retries."""
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Starting initialization (attempt {attempt + 1}/{self.max_retries})..."
                )

                # Initialize API client
                await self.initialize_client()

                logger.info("Initialization complete.")
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Initialization failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}. Retrying..."
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"Initialization failed after {self.max_retries} attempts: {str(e)}"
                    )
                    raise RuntimeError(f"Failed to initialize: {str(e)}")

    async def _get_parsed_screen_som(self) -> Dict[str, Any]:
        """Get parsed screen information.

        Returns:
            Dict containing screen information
        """
        try:
            # Take screenshot
            screenshot = await self.computer.interface.screenshot()

            # Initialize with default values
            width, height = 1024, 768
            base64_image = ""

            # Handle different types of screenshot returns
            if isinstance(screenshot, (bytes, bytearray, memoryview)):
                # Raw bytes screenshot
                base64_image = base64.b64encode(screenshot).decode("utf-8")
            elif hasattr(screenshot, "base64_image"):
                # Object-style screenshot with attributes
                # Type checking can't infer these attributes, but they exist at runtime
                # on certain screenshot return types
                base64_image = getattr(screenshot, "base64_image")
                width = (
                    getattr(screenshot, "width", width) if hasattr(screenshot, "width") else width
                )
                height = (
                    getattr(screenshot, "height", height)
                    if hasattr(screenshot, "height")
                    else height
                )

            # Create parsed screen data
            parsed_screen = {
                "width": width,
                "height": height,
                "parsed_content_list": [],
                "timestamp": datetime.now().isoformat(),
                "screenshot_base64": base64_image,
            }

            # Save screenshot if requested
            if self.save_trajectory and self.experiment_manager:
                try:
                    img_data = base64_image
                    if "," in img_data:
                        img_data = img_data.split(",")[1]
                    self._save_screenshot(img_data, action_type="state")
                except Exception as e:
                    logger.error(f"Error saving screenshot: {str(e)}")

            return parsed_screen
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return {
                "width": 1024,
                "height": 768,
                "parsed_content_list": [],
                "timestamp": datetime.now().isoformat(),
                "error": f"Error taking screenshot: {str(e)}",
                "screenshot_base64": "",
            }

    @abstractmethod
    async def initialize_client(self) -> None:
        """Initialize the API client and any provider-specific components."""
        raise NotImplementedError

    @abstractmethod
    async def run(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the agent loop with provided messages.

        Args:
            messages: List of message objects

        Yields:
            Dict containing response data
        """
        raise NotImplementedError

    @abstractmethod
    async def _process_screen(
        self, parsed_screen: Dict[str, Any], messages: List[Dict[str, Any]]
    ) -> None:
        """Process screen information and add to messages.

        Args:
            parsed_screen: Dictionary containing parsed screen info
            messages: List of messages to update
        """
        raise NotImplementedError
