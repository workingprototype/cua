"""Omni-specific agent loop implementation."""

import logging
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator, Union
from PIL import Image
import json
import re
import os
from datetime import datetime
import asyncio
from httpx import ConnectError, ReadTimeout
from typing import cast

from .parser import OmniParser, ParseResult, ParserMetadata, UIElement
from ...core.loop import BaseLoop
from ...core.visualization import VisualizationHelper
from ...core.messages import StandardMessageManager, ImageRetentionConfig
from computer import Computer
from .types import LLMProvider
from .clients.openai import OpenAIClient
from .clients.anthropic import AnthropicClient
from .prompts import SYSTEM_PROMPT
from .utils import compress_image_base64
from .image_utils import decode_base64_image, clean_base64_data
from .api_handler import OmniAPIHandler
from .action_executor import ActionExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_data(input_string: str, data_type: str) -> str:
    """Extract content from code blocks."""
    pattern = f"```{data_type}" + r"(.*?)(```|$)"
    matches = re.findall(pattern, input_string, re.DOTALL)
    return matches[0][0].strip() if matches else input_string


class OmniLoop(BaseLoop):
    """Omni-specific implementation of the agent loop.

    This class extends BaseLoop to provide support for multimodal models
    from various providers (OpenAI, Anthropic, etc.) with UI parsing
    and desktop automation capabilities.
    """

    ###########################################
    # INITIALIZATION AND CONFIGURATION
    ###########################################

    def __init__(
        self,
        parser: OmniParser,
        provider: LLMProvider,
        api_key: str,
        model: str,
        computer: Computer,
        only_n_most_recent_images: Optional[int] = 2,
        base_dir: Optional[str] = "trajectories",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        save_trajectory: bool = True,
        **kwargs,
    ):
        """Initialize the loop.

        Args:
            parser: Parser instance
            provider: API provider
            api_key: API key
            model: Model name
            computer: Computer instance
            only_n_most_recent_images: Maximum number of recent screenshots to include in API requests
            base_dir: Base directory for saving experiment data
            max_retries: Maximum number of retries for API calls
            retry_delay: Delay between retries in seconds
            save_trajectory: Whether to save trajectory data
        """
        # Set parser and provider before initializing base class
        self.parser = parser
        self.provider = provider

        # Initialize message manager with image retention config
        self.message_manager = StandardMessageManager(
            config=ImageRetentionConfig(num_images_to_keep=only_n_most_recent_images)
        )

        # Initialize base class (which will set up experiment manager)
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

        # Set API client attributes
        self.client = None
        self.retry_count = 0

        # Initialize handlers
        self.api_handler = OmniAPIHandler(self)
        self.action_executor = ActionExecutor(self)
        self.viz_helper = VisualizationHelper(self)

        logger.info("OmniLoop initialized with StandardMessageManager")

    ###########################################
    # CLIENT INITIALIZATION - IMPLEMENTING ABSTRACT METHOD
    ###########################################

    async def initialize_client(self) -> None:
        """Initialize the appropriate client based on provider.

        Implements abstract method from BaseLoop to set up the specific
        provider client (OpenAI, Anthropic, etc.).
        """
        try:
            logger.info(f"Initializing {self.provider} client with model {self.model}...")

            if self.provider == LLMProvider.OPENAI:
                self.client = OpenAIClient(api_key=self.api_key, model=self.model)
            elif self.provider == LLMProvider.ANTHROPIC:
                self.client = AnthropicClient(
                    api_key=self.api_key,
                    model=self.model,
                    max_retries=self.max_retries,
                    retry_delay=self.retry_delay,
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            logger.info(f"Initialized {self.provider} client with model {self.model}")
        except Exception as e:
            logger.error(f"Error initializing client: {str(e)}")
            self.client = None
            raise RuntimeError(f"Failed to initialize client: {str(e)}")

    ###########################################
    # API CALL HANDLING
    ###########################################

    async def _make_api_call(self, messages: List[Dict[str, Any]], system_prompt: str) -> Any:
        """Make API call to provider with retry logic."""
        # Create new turn directory for this API call
        self._create_turn_dir()

        request_data = None
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Ensure client is initialized
                if self.client is None:
                    logger.info(
                        f"Client not initialized in _make_api_call (attempt {attempt+1}), initializing now..."
                    )
                    await self.initialize_client()
                    if self.client is None:
                        raise RuntimeError("Failed to initialize client")

                # Get messages in standard format from the message manager
                self.message_manager.messages = messages.copy()
                prepared_messages = self.message_manager.get_messages()

                # Special handling for Anthropic
                if self.provider == LLMProvider.ANTHROPIC:
                    # Convert to Anthropic format
                    anthropic_messages, anthropic_system = self.message_manager.to_anthropic_format(
                        prepared_messages
                    )

                    # Filter out any empty/invalid messages
                    filtered_messages = [
                        msg
                        for msg in anthropic_messages
                        if msg.get("role") in ["user", "assistant"]
                    ]

                    # Ensure there's at least one message for Anthropic
                    if not filtered_messages:
                        logger.warning(
                            "No valid messages found for Anthropic API call. Adding a default user message."
                        )
                        filtered_messages = [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Please help with this task."}
                                ],
                            }
                        ]

                    # Combine system prompts if needed
                    final_system_prompt = anthropic_system or system_prompt

                    # Log request
                    request_data = {
                        "messages": filtered_messages,
                        "max_tokens": self.max_tokens,
                        "system": final_system_prompt,
                    }

                    self._log_api_call("request", request_data)

                    # Make API call
                    response = await self.client.run_interleaved(
                        messages=filtered_messages,
                        system=final_system_prompt,
                        max_tokens=self.max_tokens,
                    )
                else:
                    # For OpenAI and others, use standard format directly
                    # Log request
                    request_data = {
                        "messages": prepared_messages,
                        "max_tokens": self.max_tokens,
                        "system": system_prompt,
                    }

                    self._log_api_call("request", request_data)

                    # Make API call
                    response = await self.client.run_interleaved(
                        messages=prepared_messages,
                        system=system_prompt,
                        max_tokens=self.max_tokens,
                    )

                # Log success response
                self._log_api_call("response", request_data, response)

                return response

            except (ConnectError, ReadTimeout) as e:
                last_error = e
                logger.warning(
                    f"Connection error on attempt {attempt + 1}/{self.max_retries}: {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    # Reset client on connection errors to force re-initialization
                    self.client = None
                continue

            except RuntimeError as e:
                # Handle client initialization errors specifically
                last_error = e
                self._log_api_call("error", request_data, error=e)
                logger.error(
                    f"Client initialization error (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    # Reset client to force re-initialization
                    self.client = None
                    await asyncio.sleep(self.retry_delay)
                continue

            except Exception as e:
                # Log unexpected error
                last_error = e
                self._log_api_call("error", request_data, error=e)
                logger.error(f"Unexpected error in API call: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue

        # If we get here, all retries failed
        error_message = f"API call failed after {self.max_retries} attempts"
        if last_error:
            error_message += f": {str(last_error)}"

        logger.error(error_message)
        raise RuntimeError(error_message)

    ###########################################
    # RESPONSE AND ACTION HANDLING
    ###########################################

    async def _handle_response(
        self, response: Any, messages: List[Dict[str, Any]], parsed_screen: ParseResult
    ) -> Tuple[bool, bool]:
        """Handle API response.

        Args:
            response: API response
            messages: List of messages to update
            parsed_screen: Current parsed screen information

        Returns:
            Tuple of (should_continue, action_screenshot_saved)
        """
        action_screenshot_saved = False

        # Helper function to safely add assistant messages using the message manager
        def add_assistant_message(content):
            if isinstance(content, str):
                # Convert string to proper format
                formatted_content = [{"type": "text", "text": content}]
                self.message_manager.add_assistant_message(formatted_content)
                logger.info("Added formatted text assistant message")
            elif isinstance(content, list):
                # Already in proper format
                self.message_manager.add_assistant_message(content)
                logger.info("Added structured assistant message")
            else:
                # Default case - convert to string
                formatted_content = [{"type": "text", "text": str(content)}]
                self.message_manager.add_assistant_message(formatted_content)
                logger.info("Added converted assistant message")

        try:
            # Handle Anthropic response format
            if self.provider == LLMProvider.ANTHROPIC:
                if hasattr(response, "content") and isinstance(response.content, list):
                    # First convert Anthropic response to standard format
                    standard_content = []
                    for block in response.content:
                        if hasattr(block, "type"):
                            if block.type == "text":
                                standard_content.append({"type": "text", "text": block.text})
                                content = block.text
                            else:
                                # Add other block types
                                block_dict = {}
                                for key, value in vars(block).items():
                                    if not key.startswith("_"):
                                        block_dict[key] = value
                                standard_content.append(block_dict)
                                continue

                    # Add standard format response to messages using the message manager
                    add_assistant_message(standard_content)

                    # Now extract JSON from the content for action execution
                    # Try to find JSON in the text blocks
                    json_content = None
                    parsed_content = None

                    for block in response.content:
                        if hasattr(block, "type") and block.type == "text":
                            content = block.text
                            try:
                                # First look for JSON block
                                json_content = extract_data(content, "json")
                                parsed_content = json.loads(json_content)
                                logger.info("Successfully parsed JSON from code block")
                                break
                            except (json.JSONDecodeError, IndexError):
                                # If no JSON block, try to find JSON object in the text
                                try:
                                    # Look for JSON object pattern
                                    json_pattern = r"\{[^}]+\}"
                                    json_match = re.search(json_pattern, content)
                                    if json_match:
                                        json_str = json_match.group(0)
                                        parsed_content = json.loads(json_str)
                                        logger.info("Successfully parsed JSON from text")
                                        break
                                except json.JSONDecodeError:
                                    continue

                    if parsed_content:
                        # Clean up Box ID format
                        if "Box ID" in parsed_content and isinstance(parsed_content["Box ID"], str):
                            parsed_content["Box ID"] = parsed_content["Box ID"].replace("Box #", "")

                        # Add any explanatory text as reasoning if not present
                        if "Explanation" not in parsed_content:
                            # Extract any text before the JSON as reasoning
                            if content:
                                text_before_json = content.split("{")[0].strip()
                                if text_before_json:
                                    parsed_content["Explanation"] = text_before_json

                        # Log the parsed content for debugging
                        logger.info(f"Parsed content: {json.dumps(parsed_content, indent=2)}")

                        try:
                            # Execute action with current parsed screen info using the ActionExecutor
                            action_screenshot_saved = await self.action_executor.execute_action(
                                parsed_content, cast(ParseResult, parsed_screen)
                            )
                        except Exception as e:
                            logger.error(f"Error executing action: {str(e)}")
                            # Update the last assistant message with error
                            error_message = [
                                {"type": "text", "text": f"Error executing action: {str(e)}"}
                            ]
                            # Replace the last assistant message with the error
                            self.message_manager.add_assistant_message(error_message)
                            return False, action_screenshot_saved

                        # Check if task is complete
                        if parsed_content.get("Action") == "None":
                            return False, action_screenshot_saved
                        return True, action_screenshot_saved
                    else:
                        logger.warning("No JSON found in response content")
                        return True, action_screenshot_saved

                logger.warning("No text block found in Anthropic response")
                return True, action_screenshot_saved

            # Handle other providers' response formats
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
            else:
                content = response

            # Parse JSON content
            if isinstance(content, str):
                try:
                    # First try to parse the whole content as JSON
                    parsed_content = json.loads(content)
                except json.JSONDecodeError:
                    try:
                        # Try to find JSON block
                        json_content = extract_data(content, "json")
                        parsed_content = json.loads(json_content)
                    except (json.JSONDecodeError, IndexError):
                        try:
                            # Look for JSON object pattern
                            json_pattern = r"\{[^}]+\}"
                            json_match = re.search(json_pattern, content)
                            if json_match:
                                json_str = json_match.group(0)
                                parsed_content = json.loads(json_str)
                            else:
                                logger.error(f"No JSON found in content: {content}")
                                return True, action_screenshot_saved
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON from text: {str(e)}")
                            return True, action_screenshot_saved

                # Clean up Box ID format
                if "Box ID" in parsed_content and isinstance(parsed_content["Box ID"], str):
                    parsed_content["Box ID"] = parsed_content["Box ID"].replace("Box #", "")

                # Add any explanatory text as reasoning if not present
                if "Explanation" not in parsed_content:
                    # Extract any text before the JSON as reasoning
                    text_before_json = content.split("{")[0].strip()
                    if text_before_json:
                        parsed_content["Explanation"] = text_before_json

                # Add response to messages with stringified content using our helper
                add_assistant_message([{"type": "text", "text": json.dumps(parsed_content)}])

                try:
                    # Execute action with current parsed screen info using the ActionExecutor
                    action_screenshot_saved = await self.action_executor.execute_action(
                        parsed_content, cast(ParseResult, parsed_screen)
                    )
                except Exception as e:
                    logger.error(f"Error executing action: {str(e)}")
                    # Add error message using the message manager
                    error_message = [{"type": "text", "text": f"Error executing action: {str(e)}"}]
                    self.message_manager.add_assistant_message(error_message)
                    return False, action_screenshot_saved

                # Check if task is complete
                if parsed_content.get("Action") == "None":
                    return False, action_screenshot_saved

                return True, action_screenshot_saved
            elif isinstance(content, dict):
                # Handle case where content is already a dictionary
                add_assistant_message([{"type": "text", "text": json.dumps(content)}])

                try:
                    # Execute action with current parsed screen info using the ActionExecutor
                    action_screenshot_saved = await self.action_executor.execute_action(
                        content, cast(ParseResult, parsed_screen)
                    )
                except Exception as e:
                    logger.error(f"Error executing action: {str(e)}")
                    # Add error message using the message manager
                    error_message = [{"type": "text", "text": f"Error executing action: {str(e)}"}]
                    self.message_manager.add_assistant_message(error_message)
                    return False, action_screenshot_saved

                # Check if task is complete
                if content.get("Action") == "None":
                    return False, action_screenshot_saved

                return True, action_screenshot_saved

            return True, action_screenshot_saved

        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            # Add error message using the message manager
            error_message = [{"type": "text", "text": f"Error: {str(e)}"}]
            self.message_manager.add_assistant_message(error_message)
            raise

    ###########################################
    # SCREEN PARSING - IMPLEMENTING ABSTRACT METHOD
    ###########################################

    async def _get_parsed_screen_som(self, save_screenshot: bool = True) -> ParseResult:
        """Get parsed screen information with Screen Object Model.

        Extends the base class method to use the OmniParser to parse the screen
        and extract UI elements.

        Args:
            save_screenshot: Whether to save the screenshot (set to False when screenshots will be saved elsewhere)

        Returns:
            ParseResult containing screen information and elements
        """
        try:
            # Use the parser's parse_screen method which handles the screenshot internally
            parsed_screen = await self.parser.parse_screen(computer=self.computer)

            # Log information about the parsed results
            logger.info(
                f"Parsed screen with {len(parsed_screen.elements) if parsed_screen.elements else 0} elements"
            )

            # Save screenshot if requested and if we have image data
            if save_screenshot and self.save_trajectory and parsed_screen.annotated_image_base64:
                try:
                    # Extract just the image data (remove data:image/png;base64, prefix)
                    img_data = parsed_screen.annotated_image_base64
                    if "," in img_data:
                        img_data = img_data.split(",")[1]
                    # Save with a generic "state" action type to indicate this is the current screen state
                    self._save_screenshot(img_data, action_type="state")
                except Exception as e:
                    logger.error(f"Error saving screenshot: {str(e)}")

            return parsed_screen

        except Exception as e:
            logger.error(f"Error getting parsed screen: {str(e)}")
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the model."""
        return SYSTEM_PROMPT

    ###########################################
    # MAIN LOOP - IMPLEMENTING ABSTRACT METHOD
    ###########################################

    async def run(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the agent loop with provided messages.

        Implements abstract method from BaseLoop to handle the main agent loop
        for the OmniLoop implementation.

        Args:
            messages: List of message objects in standard OpenAI format

        Yields:
            Dict containing response data
        """
        # Initialize the message manager with the provided messages
        self.message_manager.messages = messages.copy()
        logger.info(f"Starting OmniLoop run with {len(self.message_manager.messages)} messages")

        # Continue running until explicitly told to stop
        running = True
        turn_created = False
        # Track if an action-specific screenshot has been saved this turn
        action_screenshot_saved = False

        attempt = 0
        max_attempts = 3

        while running and attempt < max_attempts:
            try:
                # Create a new turn directory if it's not already created
                if not turn_created:
                    self._create_turn_dir()
                    turn_created = True

                # Ensure client is initialized
                if self.client is None:
                    logger.info("Initializing client...")
                    await self.initialize_client()
                    if self.client is None:
                        raise RuntimeError("Failed to initialize client")
                    logger.info("Client initialized successfully")

                # Get up-to-date screen information
                parsed_screen = await self._get_parsed_screen_som()

                # Process screen info and update messages in standard format
                try:
                    # Get image from parsed screen
                    image = parsed_screen.annotated_image_base64 or None
                    if image:
                        # Save elements as JSON if we have a turn directory
                        if self.current_turn_dir and hasattr(parsed_screen, "elements"):
                            elements_path = os.path.join(self.current_turn_dir, "elements.json")
                            with open(elements_path, "w") as f:
                                # Convert elements to dicts for JSON serialization
                                elements_json = [
                                    elem.model_dump() for elem in parsed_screen.elements
                                ]
                                json.dump(elements_json, f, indent=2)
                                logger.info(f"Saved elements to {elements_path}")

                        # Remove data URL prefix if present
                        if "," in image:
                            image = image.split(",")[1]

                        # Add screenshot to message history using message manager
                        self.message_manager.add_user_message(
                            [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{image}"},
                                }
                            ]
                        )
                        logger.info("Added screenshot to message history")
                except Exception as e:
                    logger.error(f"Error processing screen info: {str(e)}")
                    raise

                # Get system prompt
                system_prompt = self._get_system_prompt()

                # Make API call with retries using the APIHandler
                response = await self.api_handler.make_api_call(
                    self.message_manager.messages, system_prompt
                )

                # Handle the response (may execute actions)
                # Returns: (should_continue, action_screenshot_saved)
                should_continue, new_screenshot_saved = await self._handle_response(
                    response, self.message_manager.messages, parsed_screen
                )

                # Update whether an action screenshot was saved this turn
                action_screenshot_saved = action_screenshot_saved or new_screenshot_saved

                # Create OpenAI-compatible response format
                openai_compatible_response = await self._create_openai_compatible_response(
                    response, self.message_manager.messages, parsed_screen
                )

                # Yield the response to the caller
                yield openai_compatible_response

                # Check if we should continue this conversation
                running = should_continue

                # Create a new turn directory if we're continuing
                if running:
                    turn_created = False

                # Reset attempt counter on success
                attempt = 0

            except Exception as e:
                attempt += 1
                error_msg = f"Error in run method (attempt {attempt}/{max_attempts}): {str(e)}"
                logger.error(error_msg)

                # If this is our last attempt, provide more info about the error
                if attempt >= max_attempts:
                    logger.error(f"Maximum retry attempts reached. Last error was: {str(e)}")

                yield {
                    "error": str(e),
                    "metadata": {"title": "❌ Error"},
                }

                # Create a brief delay before retrying
                await asyncio.sleep(1)

    async def _create_openai_compatible_response(
        self,
        response: Any,
        messages: List[Dict[str, Any]],
        parsed_screen: Optional[ParseResult] = None,
    ) -> Dict[str, Any]:
        """Create an OpenAI computer use agent compatible response format.

        Args:
            response: The original API response
            messages: List of messages in standard OpenAI format
            parsed_screen: Optional pre-parsed screen information

        Returns:
            A response formatted according to OpenAI's computer use agent standard
        """
        from datetime import datetime
        import time

        # Create a unique ID for this response
        response_id = f"resp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id(response)}"
        reasoning_id = f"rs_{response_id}"
        action_id = f"cu_{response_id}"
        call_id = f"call_{response_id}"

        # Extract the last assistant message
        assistant_msg = None
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                assistant_msg = msg
                break

        if not assistant_msg:
            # If no assistant message found, create a default one
            assistant_msg = {"role": "assistant", "content": "No response available"}

        # Initialize output array
        output_items = []

        # Extract reasoning and action details from the response
        content = assistant_msg["content"]
        reasoning_text = None
        action_details = None

        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    # Try to parse JSON from text block
                    text_content = item.get("text", "")
                    parsed_json = json.loads(text_content)

                    # Get reasoning text
                    if reasoning_text is None:
                        reasoning_text = parsed_json.get("Explanation", "")

                    # Extract action details
                    action = parsed_json.get("Action", "").lower()
                    text_input = parsed_json.get("Text", "")
                    value = parsed_json.get("Value", "")  # Also handle Value field
                    box_id = parsed_json.get("Box ID")  # Extract Box ID

                    if action in ["click", "left_click"]:
                        # Always calculate coordinates from Box ID for click actions
                        x, y = 100, 100  # Default fallback values

                        if parsed_screen and box_id is not None:
                            try:
                                box_id_int = (
                                    box_id
                                    if isinstance(box_id, int)
                                    else int(str(box_id)) if str(box_id).isdigit() else None
                                )
                                if box_id_int is not None:
                                    # Use the ActionExecutor's method to calculate coordinates with await
                                    x, y = await self.action_executor.calculate_click_coordinates(
                                        box_id_int, parsed_screen
                                    )
                                    logger.info(
                                        f"Extracted coordinates for Box ID {box_id_int}: ({x}, {y})"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Error extracting coordinates for Box ID {box_id}: {str(e)}"
                                )

                        action_details = {
                            "type": "click",
                            "button": "left",
                            "box_id": (
                                (
                                    box_id
                                    if isinstance(box_id, int)
                                    else int(box_id) if str(box_id).isdigit() else None
                                )
                                if box_id is not None
                                else None
                            ),
                            "x": x,
                            "y": y,
                        }
                    elif action in ["type", "type_text"] and (text_input or value):
                        action_details = {
                            "type": "type",
                            "text": text_input or value,
                        }
                    elif action == "hotkey" and value:
                        action_details = {
                            "type": "hotkey",
                            "keys": value,
                        }
                    elif action == "scroll":
                        # Use default coordinates for scrolling
                        delta_x = 0
                        delta_y = 0
                        # Try to extract scroll delta values from content if available
                        scroll_data = parsed_json.get("Scroll", {})
                        if scroll_data:
                            delta_x = scroll_data.get("delta_x", 0)
                            delta_y = scroll_data.get("delta_y", 0)
                        action_details = {
                            "type": "scroll",
                            "x": 100,
                            "y": 100,
                            "scroll_x": delta_x,
                            "scroll_y": delta_y,
                        }
                    elif action == "none":
                        # Handle case when action is None (task completion)
                        action_details = {"type": "none", "description": "Task completed"}
                except json.JSONDecodeError:
                    # If not JSON, just use as reasoning text
                    if reasoning_text is None:
                        reasoning_text = ""
                    reasoning_text += item.get("text", "")

        # Add reasoning item if we have text content
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

        # If no action details extracted, use default
        if not action_details:
            action_details = {
                "type": "click",
                "button": "left",
                "x": 100,
                "y": 100,
            }

        # Add computer_call item
        computer_call = {
            "type": "computer_call",
            "id": action_id,
            "call_id": call_id,
            "action": action_details,
            "pending_safety_checks": [],
            "status": "completed",
        }
        output_items.append(computer_call)

        # Create the OpenAI-compatible response format with all expected fields
        return {
            "id": response_id,
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": None,
            "model": self.model,
            "output": output_items,
            "parallel_tool_calls": True,
            "previous_response_id": None,
            "reasoning": {"effort": "medium", "generate_summary": "concise"},
            "store": True,
            "temperature": 1.0,
            "text": {"format": {"type": "text"}},
            "tool_choice": "auto",
            "tools": [
                {
                    "type": "computer_use_preview",
                    "display_height": 768,
                    "display_width": 1024,
                    "environment": "mac",
                }
            ],
            "top_p": 1.0,
            "truncation": "auto",
            "usage": {
                "input_tokens": 0,  # Placeholder values
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 0,  # Placeholder values
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 0,  # Placeholder values
            },
            "user": None,
            "metadata": {},
            # Include the original response for backward compatibility
            "response": {"choices": [{"message": assistant_msg, "finish_reason": "stop"}]},
        }
