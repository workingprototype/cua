from dataclasses import dataclass
from typing import cast
from anthropic.types.beta import (
    BetaMessageParam,
    BetaCacheControlEphemeralParam,
    BetaToolResultBlockParam,
)


@dataclass
class ImageRetentionConfig:
    """Configuration for image retention in messages."""

    num_images_to_keep: int | None = None
    min_removal_threshold: int = 1
    enable_caching: bool = True

    def should_retain_images(self) -> bool:
        """Check if image retention is enabled."""
        return self.num_images_to_keep is not None and self.num_images_to_keep > 0


class MessageManager:
    """Manages message preparation, including image retention and caching."""

    def __init__(self, image_retention_config: ImageRetentionConfig):
        """Initialize the message manager.

        Args:
            image_retention_config: Configuration for image retention
        """
        if image_retention_config.min_removal_threshold < 1:
            raise ValueError("min_removal_threshold must be at least 1")
        self.image_retention_config = image_retention_config

    def prepare_messages(self, messages: list[BetaMessageParam]) -> list[BetaMessageParam]:
        """Prepare messages by applying image retention and caching as configured."""
        if self.image_retention_config.should_retain_images():
            self._filter_images(messages)
        if self.image_retention_config.enable_caching:
            self._inject_caching(messages)
        return messages

    def _filter_images(self, messages: list[BetaMessageParam]) -> None:
        """Filter messages to retain only the specified number of most recent images."""
        tool_result_blocks = cast(
            list[BetaToolResultBlockParam],
            [
                item
                for message in messages
                for item in (message["content"] if isinstance(message["content"], list) else [])
                if isinstance(item, dict) and item.get("type") == "tool_result"
            ],
        )

        total_images = sum(
            1
            for tool_result in tool_result_blocks
            for content in tool_result.get("content", [])
            if isinstance(content, dict) and content.get("type") == "image"
        )

        images_to_remove = total_images - (self.image_retention_config.num_images_to_keep or 0)
        # Round down to nearest min_removal_threshold for better cache behavior
        images_to_remove -= images_to_remove % self.image_retention_config.min_removal_threshold

        # Remove oldest images first
        for tool_result in tool_result_blocks:
            if isinstance(tool_result.get("content"), list):
                new_content = []
                for content in tool_result.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "image":
                        if images_to_remove > 0:
                            images_to_remove -= 1
                            continue
                    new_content.append(content)
                tool_result["content"] = new_content

    def _inject_caching(self, messages: list[BetaMessageParam]) -> None:
        """Inject caching control for the most recent turns, limited to 3 blocks max to avoid API errors."""
        # Anthropic API allows a maximum of 4 blocks with cache_control
        # We use 3 here to be safe, as the system block may also have cache_control
        blocks_with_cache_control = 0
        max_cache_control_blocks = 3

        for message in reversed(messages):
            if message["role"] == "user" and isinstance(content := message["content"], list):
                # Only add cache control to the latest message in each turn
                if blocks_with_cache_control < max_cache_control_blocks:
                    blocks_with_cache_control += 1
                    # Add cache control to the last content block only
                    if content and len(content) > 0:
                        content[-1]["cache_control"] = BetaCacheControlEphemeralParam(
                            type="ephemeral"
                        )
                else:
                    # Remove any existing cache control
                    if content and len(content) > 0:
                        content[-1].pop("cache_control", None)

        # Ensure we're not exceeding the limit by checking the total
        if blocks_with_cache_control > max_cache_control_blocks:
            # If we somehow exceeded the limit, remove excess cache controls
            excess = blocks_with_cache_control - max_cache_control_blocks
            for message in messages:
                if excess <= 0:
                    break

                if message["role"] == "user" and isinstance(content := message["content"], list):
                    if content and len(content) > 0 and "cache_control" in content[-1]:
                        content[-1].pop("cache_control", None)
                        excess -= 1
