"""Anthropic-specific agent loop implementation."""

import logging
import asyncio
import json
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, cast
import base64
from datetime import datetime
from httpx import ConnectError, ReadTimeout

# Anthropic-specific imports
from anthropic import AsyncAnthropic
from anthropic.types.beta import (
    BetaMessage,
    BetaMessageParam,
    BetaTextBlock,
    BetaTextBlockParam,
    BetaToolUseBlockParam,
    BetaContentBlockParam,
)

# Computer
from computer import Computer

# Base imports
from ...core.loop import BaseLoop
from ...core.messages import ImageRetentionConfig as CoreImageRetentionConfig

# Anthropic provider-specific imports
from .api.client import AnthropicClientFactory, BaseAnthropicClient
from .tools.manager import ToolManager
from .messages.manager import MessageManager, ImageRetentionConfig
from .callbacks.manager import CallbackManager
from .prompts import SYSTEM_PROMPT
from .types import LLMProvider
from .tools import ToolResult

# Constants
COMPUTER_USE_BETA_FLAG = "computer-use-2025-01-24"
PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"

logger = logging.getLogger(__name__)


class AnthropicLoop(BaseLoop):
    """Anthropic-specific implementation of the agent loop."""

    def __init__(
        self,
        api_key: str,
        computer: Computer,
        model: str = "claude-3-7-sonnet-20250219",  # Fixed model
        only_n_most_recent_images: Optional[int] = 2,
        base_dir: Optional[str] = "trajectories",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        save_trajectory: bool = True,
        **kwargs,
    ):
        """Initialize the Anthropic loop.

        Args:
            api_key: Anthropic API key
            model: Model name (fixed to claude-3-7-sonnet-20250219)
            computer: Computer instance
            only_n_most_recent_images: Maximum number of recent screenshots to include in API requests
            base_dir: Base directory for saving experiment data
            max_retries: Maximum number of retries for API calls
            retry_delay: Delay between retries in seconds
            save_trajectory: Whether to save trajectory data
        """
        # Initialize base class with core config
        super().__init__(
            computer=computer,
            model=model,
            api_key=api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            base_dir=base_dir,
            save_trajectory=save_trajectory,
            only_n_most_recent_images=only_n_most_recent_images,
            **kwargs,
        )

        # Ensure model is always the fixed one
        self.model = "claude-3-7-sonnet-20250219"

        # Anthropic-specific attributes
        self.provider = LLMProvider.ANTHROPIC
        self.client = None
        self.retry_count = 0
        self.tool_manager = None
        self.message_manager = None
        self.callback_manager = None

        # Configure image retention with core config
        self.image_retention_config = CoreImageRetentionConfig(
            num_images_to_keep=only_n_most_recent_images
        )

        # Message history
        self.message_history = []

    async def initialize_client(self) -> None:
        """Initialize the Anthropic API client and tools."""
        try:
            logger.info(f"Initializing Anthropic client with model {self.model}...")

            # Initialize client
            self.client = AnthropicClientFactory.create_client(
                provider=self.provider, api_key=self.api_key, model=self.model
            )

            # Initialize message manager
            self.message_manager = MessageManager(
                image_retention_config=ImageRetentionConfig(
                    num_images_to_keep=self.only_n_most_recent_images, enable_caching=True
                )
            )

            # Initialize callback manager
            self.callback_manager = CallbackManager(
                content_callback=self._handle_content,
                tool_callback=self._handle_tool_result,
                api_callback=self._handle_api_interaction,
            )

            # Initialize tool manager
            self.tool_manager = ToolManager(self.computer)
            await self.tool_manager.initialize()

            logger.info(f"Initialized Anthropic client with model {self.model}")
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {str(e)}")
            self.client = None
            raise RuntimeError(f"Failed to initialize Anthropic client: {str(e)}")

    async def _process_screen(
        self, parsed_screen: Dict[str, Any], messages: List[Dict[str, Any]]
    ) -> None:
        """Process screen information and add to messages.

        Args:
            parsed_screen: Dictionary containing parsed screen info
            messages: List of messages to update
        """
        try:
            # Extract screenshot from parsed screen
            screenshot_base64 = parsed_screen.get("screenshot_base64")

            if screenshot_base64:
                # Remove data URL prefix if present
                if "," in screenshot_base64:
                    screenshot_base64 = screenshot_base64.split(",")[1]

                # Create Anthropic-compatible message with image
                screen_info_msg = {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_base64,
                            },
                        }
                    ],
                }

                # Add screen info message to messages
                messages.append(screen_info_msg)

        except Exception as e:
            logger.error(f"Error processing screen info: {str(e)}")
            raise

    async def run(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the agent loop with provided messages.

        Args:
            messages: List of message objects

        Yields:
            Dict containing response data
        """
        try:
            logger.info("Starting Anthropic loop run")

            # Reset message history and add new messages
            self.message_history = []
            self.message_history.extend(messages)

            # Create queue for response streaming
            queue = asyncio.Queue()

            # Ensure client is initialized
            if self.client is None or self.tool_manager is None:
                logger.info("Initializing client...")
                await self.initialize_client()
                if self.client is None:
                    raise RuntimeError("Failed to initialize client")
                logger.info("Client initialized successfully")

            # Start loop in background task
            loop_task = asyncio.create_task(self._run_loop(queue))

            # Process and yield messages as they arrive
            while True:
                try:
                    item = await queue.get()
                    if item is None:  # Stop signal
                        break
                    yield item
                    queue.task_done()
                except Exception as e:
                    logger.error(f"Error processing queue item: {str(e)}")
                    continue

            # Wait for loop to complete
            await loop_task

            # Send completion message
            yield {
                "role": "assistant",
                "content": "Task completed successfully.",
                "metadata": {"title": "✅ Complete"},
            }

        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            yield {
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "metadata": {"title": "❌ Error"},
            }

    async def _run_loop(self, queue: asyncio.Queue) -> None:
        """Run the agent loop with current message history.

        Args:
            queue: Queue for response streaming
        """
        try:
            while True:
                # Get up-to-date screen information
                parsed_screen = await self._get_parsed_screen_som()

                # Process screen info and update messages
                await self._process_screen(parsed_screen, self.message_history)

                # Prepare messages and make API call
                if self.message_manager is None:
                    raise RuntimeError(
                        "Message manager not initialized. Call initialize_client() first."
                    )
                prepared_messages = self.message_manager.prepare_messages(
                    cast(List[BetaMessageParam], self.message_history.copy())
                )

                # Create new turn directory for this API call
                self._create_turn_dir()

                # Use _make_api_call instead of direct client call to ensure logging
                response = await self._make_api_call(prepared_messages)

                # Handle the response
                if not await self._handle_response(response, self.message_history):
                    break

            # Signal completion
            await queue.put(None)

        except Exception as e:
            logger.error(f"Error in _run_loop: {str(e)}")
            await queue.put(
                {
                    "role": "assistant",
                    "content": f"Error in agent loop: {str(e)}",
                    "metadata": {"title": "❌ Error"},
                }
            )
            await queue.put(None)

    async def _make_api_call(self, messages: List[BetaMessageParam]) -> BetaMessage:
        """Make API call to Anthropic with retry logic.

        Args:
            messages: List of messages to send to the API

        Returns:
            API response
        """
        if self.client is None:
            raise RuntimeError("Client not initialized. Call initialize_client() first.")
        if self.tool_manager is None:
            raise RuntimeError("Tool manager not initialized. Call initialize_client() first.")

        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Log request
                request_data = {
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "system": SYSTEM_PROMPT,
                }
                # Let ExperimentManager handle sanitization
                self._log_api_call("request", request_data)

                # Setup betas and system
                system = BetaTextBlockParam(
                    type="text",
                    text=SYSTEM_PROMPT,
                )

                betas = [COMPUTER_USE_BETA_FLAG]
                # Temporarily disable prompt caching due to "A maximum of 4 blocks with cache_control may be provided" error
                # if self.message_manager.image_retention_config.enable_caching:
                #     betas.append(PROMPT_CACHING_BETA_FLAG)
                #     system["cache_control"] = {"type": "ephemeral"}

                # Make API call
                response = await self.client.create_message(
                    messages=messages,
                    system=[system],
                    tools=self.tool_manager.get_tool_params(),
                    max_tokens=self.max_tokens,
                    betas=betas,
                )

                # Let ExperimentManager handle sanitization
                self._log_api_call("response", request_data, response)

                return response
            except Exception as e:
                last_error = e
                logger.error(
                    f"Error in API call (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                self._log_api_call("error", {"messages": messages}, error=e)

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                continue

        # If we get here, all retries failed
        error_message = f"API call failed after {self.max_retries} attempts"
        if last_error:
            error_message += f": {str(last_error)}"

        logger.error(error_message)
        raise RuntimeError(error_message)

    async def _handle_response(self, response: BetaMessage, messages: List[Dict[str, Any]]) -> bool:
        """Handle the Anthropic API response.

        Args:
            response: API response
            messages: List of messages to update

        Returns:
            True if the loop should continue, False otherwise
        """
        try:
            # Convert response to parameter format
            response_params = self._response_to_params(response)

            # Add response to messages
            messages.append(
                {
                    "role": "assistant",
                    "content": response_params,
                }
            )

            if self.callback_manager is None:
                raise RuntimeError(
                    "Callback manager not initialized. Call initialize_client() first."
                )

            # Handle tool use blocks and collect results
            tool_result_content = []
            for content_block in response_params:
                # Notify callback of content
                self.callback_manager.on_content(cast(BetaContentBlockParam, content_block))

                # Handle tool use
                if content_block.get("type") == "tool_use":
                    if self.tool_manager is None:
                        raise RuntimeError(
                            "Tool manager not initialized. Call initialize_client() first."
                        )
                    result = await self.tool_manager.execute_tool(
                        name=content_block["name"],
                        tool_input=cast(Dict[str, Any], content_block["input"]),
                    )

                    # Create tool result and add to content
                    tool_result = self._make_tool_result(
                        cast(ToolResult, result), content_block["id"]
                    )
                    tool_result_content.append(tool_result)

                    # Notify callback of tool result
                    self.callback_manager.on_tool_result(
                        cast(ToolResult, result), content_block["id"]
                    )

            # If no tool results, we're done
            if not tool_result_content:
                # Signal completion
                self.callback_manager.on_content({"type": "text", "text": "<DONE>"})
                return False

            # Add tool results to message history
            messages.append({"content": tool_result_content, "role": "user"})
            return True

        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Error: {str(e)}",
                }
            )
            return False

    def _response_to_params(
        self,
        response: BetaMessage,
    ) -> List[Dict[str, Any]]:
        """Convert API response to message parameters.

        Args:
            response: API response message

        Returns:
            List of content blocks
        """
        result = []
        for block in response.content:
            if isinstance(block, BetaTextBlock):
                result.append({"type": "text", "text": block.text})
            else:
                result.append(cast(Dict[str, Any], block.model_dump()))
        return result

    def _make_tool_result(self, result: ToolResult, tool_use_id: str) -> Dict[str, Any]:
        """Convert a tool result to API format.

        Args:
            result: Tool execution result
            tool_use_id: ID of the tool use

        Returns:
            Formatted tool result
        """
        if result.content:
            return {
                "type": "tool_result",
                "content": result.content,
                "tool_use_id": tool_use_id,
                "is_error": bool(result.error),
            }

        tool_result_content = []
        is_error = False

        if result.error:
            is_error = True
            tool_result_content = [
                {
                    "type": "text",
                    "text": self._maybe_prepend_system_tool_result(result, result.error),
                }
            ]
        else:
            if result.output:
                tool_result_content.append(
                    {
                        "type": "text",
                        "text": self._maybe_prepend_system_tool_result(result, result.output),
                    }
                )
            if result.base64_image:
                tool_result_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": result.base64_image,
                        },
                    }
                )

        return {
            "type": "tool_result",
            "content": tool_result_content,
            "tool_use_id": tool_use_id,
            "is_error": is_error,
        }

    def _maybe_prepend_system_tool_result(self, result: ToolResult, result_text: str) -> str:
        """Prepend system information to tool result if available.

        Args:
            result: Tool execution result
            result_text: Text to prepend to

        Returns:
            Text with system information prepended if available
        """
        if result.system:
            result_text = f"<s>{result.system}</s>\n{result_text}"
        return result_text

    def _handle_content(self, content: BetaContentBlockParam) -> None:
        """Handle content updates from the assistant."""
        if content.get("type") == "text":
            text_content = cast(BetaTextBlockParam, content)
            text = text_content["text"]
            if text == "<DONE>":
                return
            logger.info(f"Assistant: {text}")

    def _handle_tool_result(self, result: ToolResult, tool_id: str) -> None:
        """Handle tool execution results."""
        if result.error:
            logger.error(f"Tool {tool_id} error: {result.error}")
        else:
            logger.info(f"Tool {tool_id} output: {result.output}")

    def _handle_api_interaction(
        self, request: Any, response: Any, error: Optional[Exception]
    ) -> None:
        """Handle API interactions."""
        if error:
            logger.error(f"API error: {error}")
            self._log_api_call("error", request, error=error)
        else:
            logger.debug(f"API request: {request}")
            if response:
                self._log_api_call("response", request, response)
            else:
                self._log_api_call("request", request)
