"""Anthropic-specific agent loop implementation."""

import logging
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, cast
from anthropic.types.beta import (
    BetaMessage,
    BetaMessageParam,
    BetaTextBlock,
    BetaContentBlockParam,
)
import base64
from datetime import datetime

# Computer
from computer import Computer

# Base imports
from ...core.loop import BaseLoop
from ...core.messages import StandardMessageManager, ImageRetentionConfig

# Anthropic provider-specific imports
from .api.client import AnthropicClientFactory, BaseAnthropicClient
from .tools.manager import ToolManager
from .prompts import SYSTEM_PROMPT
from .types import LLMProvider
from .tools import ToolResult

# Import the new modules we created
from .api_handler import AnthropicAPIHandler
from .response_handler import AnthropicResponseHandler
from .callbacks.manager import CallbackManager

# Constants
COMPUTER_USE_BETA_FLAG = "computer-use-2025-01-24"
PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"

logger = logging.getLogger(__name__)


class AnthropicLoop(BaseLoop):
    """Anthropic-specific implementation of the agent loop.

    This class extends BaseLoop to provide specialized support for Anthropic's Claude models
    with their unique tool-use capabilities, custom message formatting, and
    callback-driven approach to handling responses.
    """

    ###########################################
    # INITIALIZATION AND CONFIGURATION
    ###########################################

    def __init__(
        self,
        api_key: str,
        computer: Computer,
        model: str = "claude-3-7-sonnet-20250219",
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

        # Anthropic-specific attributes
        self.provider = LLMProvider.ANTHROPIC
        self.client = None
        self.retry_count = 0
        self.tool_manager = None
        self.callback_manager = None

        # Initialize standard message manager with image retention config
        self.message_manager = StandardMessageManager(
            config=ImageRetentionConfig(
                num_images_to_keep=only_n_most_recent_images, enable_caching=True
            )
        )

        # Message history (standard OpenAI format)
        self.message_history = []

        # Initialize handlers
        self.api_handler = AnthropicAPIHandler(self)
        self.response_handler = AnthropicResponseHandler(self)

    ###########################################
    # CLIENT INITIALIZATION - IMPLEMENTING ABSTRACT METHOD
    ###########################################

    async def initialize_client(self) -> None:
        """Initialize the Anthropic API client and tools.

        Implements abstract method from BaseLoop to set up the Anthropic-specific
        client, tool manager, message manager, and callback handlers.
        """
        try:
            logger.info(f"Initializing Anthropic client with model {self.model}...")

            # Initialize client
            self.client = AnthropicClientFactory.create_client(
                provider=self.provider, api_key=self.api_key, model=self.model
            )

            # Initialize callback manager with our callback handlers
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

    ###########################################
    # MAIN LOOP - IMPLEMENTING ABSTRACT METHOD
    ###########################################

    async def run(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the agent loop with provided messages.

        Implements abstract method from BaseLoop to handle the main agent loop
        for the AnthropicLoop implementation, using async queues and callbacks.

        Args:
            messages: List of message objects in standard OpenAI format

        Yields:
            Dict containing response data
        """
        try:
            logger.info("Starting Anthropic loop run")

            # Reset message history and add new messages in standard format
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

    ###########################################
    # AGENT LOOP IMPLEMENTATION
    ###########################################

    async def _run_loop(self, queue: asyncio.Queue) -> None:
        """Run the agent loop with current message history.

        Args:
            queue: Queue for response streaming
        """
        try:
            while True:
                # Capture screenshot
                try:
                    # Take screenshot - always returns raw PNG bytes
                    screenshot = await self.computer.interface.screenshot()

                    # Convert PNG bytes to base64
                    base64_image = base64.b64encode(screenshot).decode("utf-8")

                    # Save screenshot if requested
                    if self.save_trajectory and self.experiment_manager:
                        try:
                            self._save_screenshot(base64_image, action_type="state")
                        except Exception as e:
                            logger.error(f"Error saving screenshot: {str(e)}")

                    # Add screenshot to message history in OpenAI format
                    screen_info_msg = {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                            }
                        ],
                    }
                    self.message_history.append(screen_info_msg)
                except Exception as e:
                    logger.error(f"Error capturing or processing screenshot: {str(e)}")
                    raise

                # Create new turn directory for this API call
                self._create_turn_dir()

                # Convert standard messages to Anthropic format
                anthropic_messages, system_content = self.message_manager.to_anthropic_format(
                    self.message_history.copy()
                )

                # Use API handler to make API call with Anthropic format
                response = await self.api_handler.make_api_call(
                    messages=cast(List[BetaMessageParam], anthropic_messages),
                    system_prompt=system_content or SYSTEM_PROMPT,
                )

                # Use response handler to handle the response and convert to standard format
                # This adds the response to message_history
                if not await self.response_handler.handle_response(response, self.message_history):
                    break

                # Get the last assistant message and convert it to OpenAI computer use format
                for msg in reversed(self.message_history):
                    if msg["role"] == "assistant":
                        # Create OpenAI-compatible response and add to queue
                        openai_compatible_response = self._create_openai_compatible_response(
                            msg, response
                        )
                        await queue.put(openai_compatible_response)
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

    def _create_openai_compatible_response(
        self, assistant_msg: Dict[str, Any], original_response: Any
    ) -> Dict[str, Any]:
        """Create an OpenAI computer use agent compatible response format.

        Args:
            assistant_msg: The assistant message in standard OpenAI format
            original_response: The original API response object for ID generation

        Returns:
            A response formatted according to OpenAI's computer use agent standard
        """
        # Create a unique ID for this response
        response_id = f"resp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id(original_response)}"
        reasoning_id = f"rs_{response_id}"
        action_id = f"cu_{response_id}"
        call_id = f"call_{response_id}"

        # Extract reasoning and action details from the response
        content = assistant_msg["content"]

        # Initialize output array
        output_items = []

        # Add reasoning item if we have text content
        reasoning_text = None
        action_details = None

        # AnthropicLoop expects a list of content blocks with type "text" or "tool_use"
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    reasoning_text = item.get("text", "")
                elif isinstance(item, dict) and item.get("type") == "tool_use":
                    action_details = item
        else:
            # Fallback for string content
            reasoning_text = content if isinstance(content, str) else None

        # If we have reasoning text, add reasoning item
        if reasoning_text:
            output_items.append(
                {
                    "type": "reasoning",
                    "id": reasoning_id,
                    "summary": [
                        {
                            "type": "summary_text",
                            "text": reasoning_text[:200],  # Truncate to reasonable length
                        }
                    ],
                }
            )

        # Add computer_call item with action details if available
        computer_call = {
            "type": "computer_call",
            "id": action_id,
            "call_id": call_id,
            "action": {"type": "click", "button": "left", "x": 100, "y": 100},  # Default action
            "pending_safety_checks": [],
            "status": "completed",
        }

        # If we have action details from a tool_use, update the computer_call
        if action_details:
            # Try to map tool_use to computer_call action
            tool_input = action_details.get("input", {})
            if "click" in tool_input or "position" in tool_input:
                position = tool_input.get("click", tool_input.get("position", {}))
                if isinstance(position, dict) and "x" in position and "y" in position:
                    computer_call["action"] = {
                        "type": "click",
                        "button": "left",
                        "x": position.get("x", 100),
                        "y": position.get("y", 100),
                    }
            elif "type" in tool_input or "text" in tool_input:
                computer_call["action"] = {
                    "type": "type",
                    "text": tool_input.get("type", tool_input.get("text", "")),
                }
            elif "scroll" in tool_input:
                scroll = tool_input.get("scroll", {})
                computer_call["action"] = {
                    "type": "scroll",
                    "x": 100,
                    "y": 100,
                    "scroll_x": scroll.get("x", 0),
                    "scroll_y": scroll.get("y", 0),
                }

        output_items.append(computer_call)

        # Create the OpenAI-compatible response format
        return {
            "output": output_items,
            "id": response_id,
            # Include the original format for backward compatibility
            "response": {"choices": [{"message": assistant_msg, "finish_reason": "stop"}]},
        }

    ###########################################
    # RESPONSE AND CALLBACK HANDLING
    ###########################################

    async def _handle_response(self, response: BetaMessage, messages: List[Dict[str, Any]]) -> bool:
        """Handle the Anthropic API response.

        Args:
            response: API response
            messages: List of messages to update in standard OpenAI format

        Returns:
            True if the loop should continue, False otherwise
        """
        try:
            # Convert Anthropic response to standard OpenAI format
            response_blocks = self._response_to_blocks(response)

            # Add response to standard message history
            messages.append({"role": "assistant", "content": response_blocks})

            if self.callback_manager is None:
                raise RuntimeError(
                    "Callback manager not initialized. Call initialize_client() first."
                )

            # Handle tool use blocks and collect results
            tool_result_content = []
            for content_block in response.content:
                # Notify callback of content
                self.callback_manager.on_content(cast(BetaContentBlockParam, content_block))

                # Handle tool use - carefully check and access attributes
                if hasattr(content_block, "type") and content_block.type == "tool_use":
                    if self.tool_manager is None:
                        raise RuntimeError(
                            "Tool manager not initialized. Call initialize_client() first."
                        )

                    # Safely get attributes
                    tool_name = getattr(content_block, "name", "")
                    tool_input = getattr(content_block, "input", {})
                    tool_id = getattr(content_block, "id", "")

                    result = await self.tool_manager.execute_tool(
                        name=tool_name,
                        tool_input=cast(Dict[str, Any], tool_input),
                    )

                    # Create tool result
                    tool_result = self._make_tool_result(cast(ToolResult, result), tool_id)
                    tool_result_content.append(tool_result)

                    # Notify callback of tool result
                    self.callback_manager.on_tool_result(cast(ToolResult, result), tool_id)

            # If no tool results, we're done
            if not tool_result_content:
                # Signal completion
                self.callback_manager.on_content({"type": "text", "text": "<DONE>"})
                return False

            # Add tool results to message history in standard format
            messages.append({"role": "user", "content": tool_result_content})
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

    def _response_to_blocks(self, response: BetaMessage) -> List[Dict[str, Any]]:
        """Convert Anthropic API response to standard blocks format.

        Args:
            response: API response message

        Returns:
            List of content blocks in standard format
        """
        result = []
        for block in response.content:
            if isinstance(block, BetaTextBlock):
                result.append({"type": "text", "text": block.text})
            elif hasattr(block, "type") and block.type == "tool_use":
                # Safely access attributes after confirming it's a tool_use
                result.append(
                    {
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    }
                )
            else:
                # For other block types, convert to dict
                block_dict = {}
                for key, value in vars(block).items():
                    if not key.startswith("_"):
                        block_dict[key] = value
                result.append(block_dict)

        return result

    def _make_tool_result(self, result: ToolResult, tool_use_id: str) -> Dict[str, Any]:
        """Convert a tool result to standard format.

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
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{result.base64_image}"},
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

    ###########################################
    # CALLBACK HANDLERS
    ###########################################

    def _handle_content(self, content):
        """Handle content updates from the assistant."""
        if content.get("type") == "text":
            text = content.get("text", "")
            if text == "<DONE>":
                return
            logger.info(f"Assistant: {text}")

    def _handle_tool_result(self, result, tool_id):
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
