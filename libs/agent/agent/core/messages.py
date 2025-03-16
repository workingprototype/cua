"""Message handling utilities for agent."""

import base64
from datetime import datetime
from io import BytesIO
import logging
from typing import Any, Dict, List, Optional, Union
from PIL import Image
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ImageRetentionConfig:
    """Configuration for image retention in messages."""

    num_images_to_keep: Optional[int] = None
    min_removal_threshold: int = 1
    enable_caching: bool = True

    def should_retain_images(self) -> bool:
        """Check if image retention is enabled."""
        return self.num_images_to_keep is not None and self.num_images_to_keep > 0


class BaseMessageManager:
    """Base class for message preparation and management."""

    def __init__(self, image_retention_config: Optional[ImageRetentionConfig] = None):
        """Initialize the message manager.

        Args:
            image_retention_config: Configuration for image retention
        """
        self.image_retention_config = image_retention_config or ImageRetentionConfig()
        if self.image_retention_config.min_removal_threshold < 1:
            raise ValueError("min_removal_threshold must be at least 1")

        # Track provider for message formatting
        self.provider = "openai"  # Default provider

    def set_provider(self, provider: str) -> None:
        """Set the current provider to format messages for.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
        """
        self.provider = provider.lower()

    def prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare messages by applying image retention and caching as configured.

        Args:
            messages: List of messages to prepare

        Returns:
            Prepared messages
        """
        if self.image_retention_config.should_retain_images():
            self._filter_images(messages)
        if self.image_retention_config.enable_caching:
            self._inject_caching(messages)
        return messages

    def _filter_images(self, messages: List[Dict[str, Any]]) -> None:
        """Filter messages to retain only the specified number of most recent images.

        Args:
            messages: Messages to filter
        """
        # Find all tool result blocks that contain images
        tool_results = [
            item
            for message in messages
            for item in (message["content"] if isinstance(message["content"], list) else [])
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ]

        # Count total images
        total_images = sum(
            1
            for result in tool_results
            for content in result.get("content", [])
            if isinstance(content, dict) and content.get("type") == "image"
        )

        # Calculate how many images to remove
        images_to_remove = total_images - (self.image_retention_config.num_images_to_keep or 0)
        images_to_remove -= images_to_remove % self.image_retention_config.min_removal_threshold

        # Remove oldest images first
        for result in tool_results:
            if isinstance(result.get("content"), list):
                new_content = []
                for content in result["content"]:
                    if isinstance(content, dict) and content.get("type") == "image":
                        if images_to_remove > 0:
                            images_to_remove -= 1
                            continue
                    new_content.append(content)
                result["content"] = new_content

    def _inject_caching(self, messages: List[Dict[str, Any]]) -> None:
        """Inject caching control for recent message turns.

        Args:
            messages: Messages to inject caching into
        """
        # Only apply cache_control for Anthropic API, not OpenAI
        if self.provider != "anthropic":
            return

        # Default to caching last 3 turns
        turns_to_cache = 3
        for message in reversed(messages):
            if message["role"] == "user" and isinstance(content := message["content"], list):
                if turns_to_cache:
                    turns_to_cache -= 1
                    content[-1]["cache_control"] = {"type": "ephemeral"}
                else:
                    content[-1].pop("cache_control", None)
                    break


def create_user_message(text: str) -> Dict[str, str]:
    """Create a user message.

    Args:
        text: The message text

    Returns:
        Message dictionary
    """
    return {
        "role": "user",
        "content": text,
    }


def create_assistant_message(text: str) -> Dict[str, str]:
    """Create an assistant message.

    Args:
        text: The message text

    Returns:
        Message dictionary
    """
    return {
        "role": "assistant",
        "content": text,
    }


def create_system_message(text: str) -> Dict[str, str]:
    """Create a system message.

    Args:
        text: The message text

    Returns:
        Message dictionary
    """
    return {
        "role": "system",
        "content": text,
    }


def create_image_message(
    image_base64: Optional[str] = None,
    image_path: Optional[str] = None,
    image_obj: Optional[Image.Image] = None,
) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
    """Create a message with an image.

    Args:
        image_base64: Base64 encoded image
        image_path: Path to image file
        image_obj: PIL Image object

    Returns:
        Message dictionary with content list

    Raises:
        ValueError: If no image source is provided
    """
    if not any([image_base64, image_path, image_obj]):
        raise ValueError("Must provide one of image_base64, image_path, or image_obj")

    # Convert to base64 if needed
    if image_path and not image_base64:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    elif image_obj and not image_base64:
        buffer = BytesIO()
        image_obj.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "role": "user",
        "content": [
            {"type": "image", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
        ],
    }


def create_screen_message(
    parsed_screen: Dict[str, Any],
    include_raw: bool = False,
) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
    """Create a message with screen information.

    Args:
        parsed_screen: Dictionary containing parsed screen info
        include_raw: Whether to include raw screenshot base64

    Returns:
        Message dictionary with content
    """
    if include_raw and "screenshot_base64" in parsed_screen:
        # Create content list with both image and text
        return {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image_url": {
                        "url": f"data:image/png;base64,{parsed_screen['screenshot_base64']}"
                    },
                },
                {
                    "type": "text",
                    "text": f"Screen dimensions: {parsed_screen['width']}x{parsed_screen['height']}",
                },
            ],
        }
    else:
        # Create text-only message with screen info
        return {
            "role": "user",
            "content": f"Screen dimensions: {parsed_screen['width']}x{parsed_screen['height']}",
        }
