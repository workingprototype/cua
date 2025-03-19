"""Experiment management for the Cua provider."""

import os
import logging
import copy
import base64
from io import BytesIO
from datetime import datetime
from typing import Any, Dict, List, Optional
from PIL import Image
import json
import time

logger = logging.getLogger(__name__)


class ExperimentManager:
    """Manages experiment directories and logging for the agent."""

    def __init__(
        self,
        base_dir: Optional[str] = None,
        only_n_most_recent_images: Optional[int] = None,
    ):
        """Initialize the experiment manager.

        Args:
            base_dir: Base directory for saving experiment data
            only_n_most_recent_images: Maximum number of recent screenshots to include in API requests
        """
        self.base_dir = base_dir
        self.only_n_most_recent_images = only_n_most_recent_images
        self.run_dir = None
        self.current_turn_dir = None
        self.turn_count = 0
        self.screenshot_count = 0
        # Track all screenshots for potential API request inclusion
        self.screenshot_paths = []

        # Set up experiment directories if base_dir is provided
        if self.base_dir:
            self.setup_experiment_dirs()

    def setup_experiment_dirs(self) -> None:
        """Setup the experiment directory structure."""
        if not self.base_dir:
            return

        # Create base experiments directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)

        # Use the base_dir directly as the run_dir
        self.run_dir = self.base_dir
        logger.info(f"Using directory for experiment: {self.run_dir}")

        # Create first turn directory
        self.create_turn_dir()

    def create_turn_dir(self) -> None:
        """Create a new directory for the current turn."""
        if not self.run_dir:
            return

        self.turn_count += 1
        self.current_turn_dir = os.path.join(self.run_dir, f"turn_{self.turn_count:03d}")
        os.makedirs(self.current_turn_dir, exist_ok=True)
        logger.info(f"Created turn directory: {self.current_turn_dir}")

    def sanitize_log_data(self, data: Any) -> Any:
        """Sanitize data for logging by removing large base64 strings.

        Args:
            data: Data to sanitize (dict, list, or primitive)

        Returns:
            Sanitized copy of the data
        """
        if isinstance(data, dict):
            result = copy.deepcopy(data)

            # Handle nested dictionaries and lists
            for key, value in result.items():
                # Process content arrays that contain image data
                if key == "content" and isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            # Handle Anthropic format
                            if item.get("type") == "image" and isinstance(item.get("source"), dict):
                                source = item["source"]
                                if "data" in source and isinstance(source["data"], str):
                                    # Replace base64 data with a placeholder and length info
                                    data_len = len(source["data"])
                                    source["data"] = f"[BASE64_IMAGE_DATA_LENGTH_{data_len}]"

                            # Handle OpenAI format
                            elif item.get("type") == "image_url" and isinstance(
                                item.get("image_url"), dict
                            ):
                                url_dict = item["image_url"]
                                if "url" in url_dict and isinstance(url_dict["url"], str):
                                    url = url_dict["url"]
                                    if url.startswith("data:"):
                                        # Replace base64 data with placeholder
                                        data_len = len(url)
                                        url_dict["url"] = f"[BASE64_IMAGE_URL_LENGTH_{data_len}]"

                # Handle other nested structures recursively
                if isinstance(value, dict):
                    result[key] = self.sanitize_log_data(value)
                elif isinstance(value, list):
                    result[key] = [self.sanitize_log_data(item) for item in value]

            return result
        elif isinstance(data, list):
            return [self.sanitize_log_data(item) for item in data]
        else:
            return data

    def save_debug_image(self, image_data: str, filename: str) -> None:
        """Save a debug image to the experiment directory.

        Args:
            image_data: Base64 encoded image data
            filename: Filename to save the image as
        """
        # Since we no longer want to use the images/ folder, we'll skip this functionality
        return

    def save_screenshot(self, img_base64: str, action_type: str = "") -> Optional[str]:
        """Save a screenshot to the experiment directory.

        Args:
            img_base64: Base64 encoded screenshot
            action_type: Type of action that triggered the screenshot

        Returns:
            Optional[str]: Path to the saved screenshot, or None if saving failed
        """
        if not self.current_turn_dir:
            return None

        try:
            # Increment screenshot counter
            self.screenshot_count += 1

            # Create a descriptive filename
            timestamp = int(time.time() * 1000)
            action_suffix = f"_{action_type}" if action_type else ""
            filename = f"screenshot_{self.screenshot_count:03d}{action_suffix}_{timestamp}.png"

            # Save directly to the turn directory (no screenshots subdirectory)
            filepath = os.path.join(self.current_turn_dir, filename)

            # Save the screenshot
            img_data = base64.b64decode(img_base64)
            with open(filepath, "wb") as f:
                f.write(img_data)

            # Keep track of the file path for reference
            self.screenshot_paths.append(filepath)

            return filepath
        except Exception as e:
            logger.error(f"Error saving screenshot: {str(e)}")
            return None

    def should_save_debug_image(self) -> bool:
        """Determine if debug images should be saved.

        Returns:
            Boolean indicating if debug images should be saved
        """
        # We no longer need to save debug images, so always return False
        return False

    def save_action_visualization(
        self, img: Image.Image, action_name: str, details: str = ""
    ) -> str:
        """Save a visualization of an action.

        Args:
            img: Image to save
            action_name: Name of the action
            details: Additional details about the action

        Returns:
            Path to the saved image
        """
        if not self.current_turn_dir:
            return ""

        try:
            # Create a descriptive filename
            timestamp = int(time.time() * 1000)
            details_suffix = f"_{details}" if details else ""
            filename = f"vis_{action_name}{details_suffix}_{timestamp}.png"

            # Save directly to the turn directory (no visualizations subdirectory)
            filepath = os.path.join(self.current_turn_dir, filename)

            # Save the image
            img.save(filepath)

            # Keep track of the file path for cleanup
            self.screenshot_paths.append(filepath)

            return filepath
        except Exception as e:
            logger.error(f"Error saving action visualization: {str(e)}")
            return ""

    def extract_and_save_images(self, data: Any, prefix: str) -> None:
        """Extract and save images from response data.

        Args:
            data: Response data to extract images from
            prefix: Prefix for saved image filenames
        """
        # Since we no longer want to save extracted images separately,
        # we'll skip this functionality entirely
        return

    def log_api_call(
        self,
        call_type: str,
        request: Any,
        provider: str,
        model: str,
        response: Any = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Log API call details to file.

        Args:
            call_type: Type of API call (e.g., 'request', 'response', 'error')
            request: The API request data
            provider: The AI provider used
            model: The AI model used
            response: Optional API response data
            error: Optional error information
        """
        if not self.current_turn_dir:
            return

        try:
            # Create a unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_call_{timestamp}_{call_type}.json"
            filepath = os.path.join(self.current_turn_dir, filename)

            # Sanitize data to remove large base64 strings
            sanitized_request = self.sanitize_log_data(request)
            sanitized_response = self.sanitize_log_data(response) if response is not None else None

            # Prepare log data
            log_data = {
                "timestamp": timestamp,
                "provider": provider,
                "model": model,
                "type": call_type,
                "request": sanitized_request,
            }

            if sanitized_response is not None:
                log_data["response"] = sanitized_response
            if error is not None:
                log_data["error"] = str(error)

            # Write to file
            with open(filepath, "w") as f:
                json.dump(log_data, f, indent=2, default=str)

            logger.info(f"Logged API {call_type} to {filepath}")

        except Exception as e:
            logger.error(f"Error logging API call: {str(e)}")
