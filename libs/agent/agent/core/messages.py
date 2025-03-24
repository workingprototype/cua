"""Message handling utilities for agent."""

import logging
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
import re
from ..providers.omni.parser import ParseResult

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


class StandardMessageManager:
    """Manages messages in a standardized OpenAI format across different providers."""

    def __init__(self, config: Optional[ImageRetentionConfig] = None):
        """Initialize message manager.

        Args:
            config: Configuration for image retention
        """
        self.messages: List[Dict[str, Any]] = []
        self.config = config or ImageRetentionConfig()

    def add_user_message(self, content: Union[str, List[Dict[str, Any]]]) -> None:
        """Add a user message.

        Args:
            content: Message content (text or multimodal content)
        """
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: Union[str, List[Dict[str, Any]]]) -> None:
        """Add an assistant message.

        Args:
            content: Message content (text or multimodal content)
        """
        self.messages.append({"role": "assistant", "content": content})

    def add_system_message(self, content: str) -> None:
        """Add a system message.

        Args:
            content: System message content
        """
        self.messages.append({"role": "system", "content": content})

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in standard format.

        Returns:
            List of messages
        """
        # If image retention is configured, apply it
        if self.config.num_images_to_keep is not None:
            return self._apply_image_retention(self.messages)
        return self.messages

    def _apply_image_retention(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply image retention policy to messages.

        Args:
            messages: List of messages

        Returns:
            List of messages with image retention applied
        """
        if not self.config.num_images_to_keep:
            return messages

        # Find user messages with images
        image_messages = []
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                has_image = any(
                    item.get("type") == "image_url" or item.get("type") == "image"
                    for item in msg["content"]
                )
                if has_image:
                    image_messages.append(msg)

        # If we don't have more images than the limit, return all messages
        if len(image_messages) <= self.config.num_images_to_keep:
            return messages

        # Get the most recent N images to keep
        images_to_keep = image_messages[-self.config.num_images_to_keep :]
        images_to_remove = image_messages[: -self.config.num_images_to_keep]

        # Create a new message list without the older images
        result = []
        for msg in messages:
            if msg in images_to_remove:
                # Skip this message
                continue
            result.append(msg)

        return result

    def to_anthropic_format(
        self, messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Convert standard OpenAI format messages to Anthropic format.

        Args:
            messages: List of messages in OpenAI format

        Returns:
            Tuple containing (anthropic_messages, system_content)
        """
        result = []
        system_content = ""

        # Process messages in order to maintain conversation flow
        previous_assistant_tool_use_ids = (
            set()
        )  # Track tool_use_ids in the previous assistant message

        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                # Collect system messages for later use
                system_content += content + "\n"
                continue

            if role == "assistant":
                # Track tool_use_ids in this assistant message for the next user message
                previous_assistant_tool_use_ids = set()
                if isinstance(content, list):
                    for item in content:
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "tool_use"
                            and "id" in item
                        ):
                            previous_assistant_tool_use_ids.add(item["id"])

                logger.info(
                    f"Tool use IDs in assistant message #{i}: {previous_assistant_tool_use_ids}"
                )

            if role in ["user", "assistant"]:
                anthropic_msg = {"role": role}

                # Convert content based on type
                if isinstance(content, str):
                    # Simple text content
                    anthropic_msg["content"] = [{"type": "text", "text": content}]
                elif isinstance(content, list):
                    # Convert complex content
                    anthropic_content = []
                    for item in content:
                        item_type = item.get("type", "")

                        if item_type == "text":
                            anthropic_content.append({"type": "text", "text": item.get("text", "")})
                        elif item_type == "image_url":
                            # Convert OpenAI image format to Anthropic
                            image_url = item.get("image_url", {}).get("url", "")
                            if image_url.startswith("data:"):
                                # Extract base64 data and media type
                                match = re.match(r"data:(.+);base64,(.+)", image_url)
                                if match:
                                    media_type, data = match.groups()
                                    anthropic_content.append(
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": media_type,
                                                "data": data,
                                            },
                                        }
                                    )
                            else:
                                # Regular URL
                                anthropic_content.append(
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "url",
                                            "url": image_url,
                                        },
                                    }
                                )
                        elif item_type == "tool_use":
                            # Always include tool_use blocks
                            anthropic_content.append(item)
                        elif item_type == "tool_result":
                            # Check if this is a user message AND if the tool_use_id exists in the previous assistant message
                            tool_use_id = item.get("tool_use_id")

                            # Only include tool_result if it references a tool_use from the immediately preceding assistant message
                            if (
                                role == "user"
                                and tool_use_id
                                and tool_use_id in previous_assistant_tool_use_ids
                            ):
                                anthropic_content.append(item)
                                logger.info(
                                    f"Including tool_result with tool_use_id: {tool_use_id}"
                                )
                            else:
                                # Convert to text to preserve information
                                logger.warning(
                                    f"Converting tool_result to text. Tool use ID {tool_use_id} not found in previous assistant message"
                                )
                                content_text = "Tool Result: "
                                if "content" in item:
                                    if isinstance(item["content"], list):
                                        for content_item in item["content"]:
                                            if (
                                                isinstance(content_item, dict)
                                                and content_item.get("type") == "text"
                                            ):
                                                content_text += content_item.get("text", "")
                                    elif isinstance(item["content"], str):
                                        content_text += item["content"]
                                anthropic_content.append({"type": "text", "text": content_text})

                    anthropic_msg["content"] = anthropic_content

                result.append(anthropic_msg)

        return result, system_content

    def from_anthropic_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Anthropic format messages to standard OpenAI format.

        Args:
            messages: List of messages in Anthropic format

        Returns:
            List of messages in OpenAI format
        """
        result = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", [])

            if role in ["user", "assistant"]:
                openai_msg = {"role": role}

                # Simple case: single text block
                if len(content) == 1 and content[0].get("type") == "text":
                    openai_msg["content"] = content[0].get("text", "")
                else:
                    # Complex case: multiple blocks or non-text
                    openai_content = []
                    for item in content:
                        item_type = item.get("type", "")

                        if item_type == "text":
                            openai_content.append({"type": "text", "text": item.get("text", "")})
                        elif item_type == "image":
                            # Convert Anthropic image to OpenAI format
                            source = item.get("source", {})
                            if source.get("type") == "base64":
                                media_type = source.get("media_type", "image/png")
                                data = source.get("data", "")
                                openai_content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{media_type};base64,{data}"},
                                    }
                                )
                            else:
                                # URL
                                openai_content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": source.get("url", "")},
                                    }
                                )
                        elif item_type in ["tool_use", "tool_result"]:
                            # Pass through tool-related content
                            openai_content.append(item)

                    openai_msg["content"] = openai_content

                result.append(openai_msg)

        return result
