"""Omni message manager implementation."""

import base64
from typing import Any, Dict, List, Optional
from io import BytesIO
from PIL import Image

from ...core.messages import BaseMessageManager, ImageRetentionConfig


class OmniMessageManager(BaseMessageManager):
    """Message manager for multi-provider support."""

    def __init__(self, config: Optional[ImageRetentionConfig] = None):
        """Initialize the message manager.

        Args:
            config: Optional configuration for image retention
        """
        super().__init__(config)
        self.messages: List[Dict[str, Any]] = []
        self.config = config

    def add_user_message(self, content: str, images: Optional[List[bytes]] = None) -> None:
        """Add a user message to the history.

        Args:
            content: Message content
            images: Optional list of image data
        """
        # Add images if present
        if images:
            # Initialize with proper typing for mixed content
            message_content: List[Dict[str, Any]] = [{"type": "text", "text": content}]

            # Add each image
            for img in images:
                message_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(img).decode()}"
                        },
                    }
                )

            message = {"role": "user", "content": message_content}
        else:
            # Simple text message
            message = {"role": "user", "content": content}

        self.messages.append(message)

        # Apply retention policy
        if self.config and self.config.num_images_to_keep:
            self._apply_image_retention_policy()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the history.

        Args:
            content: Message content
        """
        self.messages.append({"role": "assistant", "content": content})

    def add_system_message(self, content: str) -> None:
        """Add a system message to the history.

        Args:
            content: Message content
        """
        self.messages.append({"role": "system", "content": content})

    def _apply_image_retention_policy(self) -> None:
        """Apply image retention policy to message history."""
        if not self.config or not self.config.num_images_to_keep:
            return

        # Count images from newest to oldest
        image_count = 0
        for message in reversed(self.messages):
            if message["role"] != "user":
                continue

            # Handle multimodal messages
            if isinstance(message["content"], list):
                new_content = []
                for item in message["content"]:
                    if item["type"] == "text":
                        new_content.append(item)
                    elif item["type"] == "image_url":
                        if image_count < self.config.num_images_to_keep:
                            new_content.append(item)
                            image_count += 1
                message["content"] = new_content

    def get_formatted_messages(self, provider: str) -> List[Dict[str, Any]]:
        """Get messages formatted for specific provider.

        Args:
            provider: Provider name to format messages for

        Returns:
            List of formatted messages
        """
        # Set the provider for message formatting
        self.set_provider(provider)

        if provider == "anthropic":
            return self._format_for_anthropic()
        elif provider == "openai":
            return self._format_for_openai()
        elif provider == "groq":
            return self._format_for_groq()
        elif provider == "qwen":
            return self._format_for_qwen()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _format_for_anthropic(self) -> List[Dict[str, Any]]:
        """Format messages for Anthropic API."""
        formatted = []
        for msg in self.messages:
            formatted_msg = {"role": msg["role"]}

            # Handle multimodal content
            if isinstance(msg["content"], list):
                formatted_msg["content"] = []
                for item in msg["content"]:
                    if item["type"] == "text":
                        formatted_msg["content"].append({"type": "text", "text": item["text"]})
                    elif item["type"] == "image_url":
                        formatted_msg["content"].append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": item["image_url"]["url"].split(",")[1],
                                },
                            }
                        )
            else:
                formatted_msg["content"] = msg["content"]

            formatted.append(formatted_msg)
        return formatted

    def _format_for_openai(self) -> List[Dict[str, Any]]:
        """Format messages for OpenAI API."""
        # OpenAI already uses the same format
        return self.messages

    def _format_for_groq(self) -> List[Dict[str, Any]]:
        """Format messages for Groq API."""
        # Groq uses OpenAI-compatible format
        return self.messages

    def _format_for_qwen(self) -> List[Dict[str, Any]]:
        """Format messages for Qwen API."""
        formatted = []
        for msg in self.messages:
            if isinstance(msg["content"], list):
                # Convert multimodal content to text-only
                text_content = next(
                    (item["text"] for item in msg["content"] if item["type"] == "text"), ""
                )
                formatted.append({"role": msg["role"], "content": text_content})
            else:
                formatted.append(msg)
        return formatted
