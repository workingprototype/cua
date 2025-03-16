"""Omni-specific agent loop implementation."""

import logging
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator, Union
import base64
from PIL import Image
from io import BytesIO
import json
import re
import os
from datetime import datetime
import asyncio
from httpx import ConnectError, ReadTimeout
import shutil
import copy

from .parser import OmniParser, ParseResult, ParserMetadata, UIElement
from ...core.loop import BaseLoop
from computer import Computer
from .types import LLMProvider
from .clients.base import BaseOmniClient
from .clients.openai import OpenAIClient
from .clients.groq import GroqClient
from .clients.anthropic import AnthropicClient
from .prompts import SYSTEM_PROMPT
from .utils import compress_image_base64
from .visualization import visualize_click, visualize_scroll, calculate_element_center
from .image_utils import decode_base64_image, clean_base64_data
from ...core.messages import ImageRetentionConfig
from .messages import OmniMessageManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_data(input_string: str, data_type: str) -> str:
    """Extract content from code blocks."""
    pattern = f"```{data_type}" + r"(.*?)(```|$)"
    matches = re.findall(pattern, input_string, re.DOTALL)
    return matches[0][0].strip() if matches else input_string


class OmniLoop(BaseLoop):
    """Omni-specific implementation of the agent loop."""

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
        image_retention_config = ImageRetentionConfig(num_images_to_keep=only_n_most_recent_images)
        self.message_manager = OmniMessageManager(config=image_retention_config)

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

    def _should_save_debug_image(self) -> bool:
        """Check if debug images should be saved.

        Returns:
            bool: Always returns False as debug image saving has been disabled.
        """
        # Debug image saving functionality has been removed
        return False

    def _extract_and_save_images(self, data: Any, prefix: str) -> None:
        """Extract and save images from API data.

        This method is now a no-op as image extraction functionality has been removed.

        Args:
            data: Data to extract images from
            prefix: Prefix for the extracted image filenames
        """
        # Image extraction functionality has been removed
        return

    def _save_debug_image(self, image_data: str, filename: str) -> None:
        """Save a debug image to the current turn directory.

        This method is now a no-op as debug image saving functionality has been removed.

        Args:
            image_data: Base64 encoded image data
            filename: Name to use for the saved image
        """
        # Debug image saving functionality has been removed
        return

    def _visualize_action(self, x: int, y: int, img_base64: str) -> None:
        """Visualize an action by drawing on the screenshot."""
        if (
            not self.save_trajectory
            or not hasattr(self, "experiment_manager")
            or not self.experiment_manager
        ):
            return

        try:
            # Use the visualization utility
            img = visualize_click(x, y, img_base64)

            # Save the visualization
            self.experiment_manager.save_action_visualization(img, "click", f"x{x}_y{y}")
        except Exception as e:
            logger.error(f"Error visualizing action: {str(e)}")

    def _visualize_scroll(self, direction: str, clicks: int, img_base64: str) -> None:
        """Visualize a scroll action by drawing arrows on the screenshot."""
        if (
            not self.save_trajectory
            or not hasattr(self, "experiment_manager")
            or not self.experiment_manager
        ):
            return

        try:
            # Use the visualization utility
            img = visualize_scroll(direction, clicks, img_base64)

            # Save the visualization
            self.experiment_manager.save_action_visualization(
                img, "scroll", f"{direction}_{clicks}"
            )
        except Exception as e:
            logger.error(f"Error visualizing scroll: {str(e)}")

    def _save_action_visualization(
        self, img: Image.Image, action_name: str, details: str = ""
    ) -> str:
        """Save a visualization of an action."""
        if hasattr(self, "experiment_manager") and self.experiment_manager:
            return self.experiment_manager.save_action_visualization(img, action_name, details)
        return ""

    async def initialize_client(self) -> None:
        """Initialize the appropriate client based on provider."""
        try:
            logger.info(f"Initializing {self.provider} client with model {self.model}...")

            if self.provider == LLMProvider.OPENAI:
                self.client = OpenAIClient(api_key=self.api_key, model=self.model)
            elif self.provider == LLMProvider.GROQ:
                self.client = GroqClient(api_key=self.api_key, model=self.model)
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

                # Set the provider in message manager based on current provider
                provider_name = str(self.provider).split(".")[-1].lower()  # Extract name from enum
                self.message_manager.set_provider(provider_name)

                # Apply image retention and prepare messages
                # This will limit the number of images based on only_n_most_recent_images
                prepared_messages = self.message_manager.get_formatted_messages(provider_name)

                # Filter out system messages for Anthropic
                if self.provider == LLMProvider.ANTHROPIC:
                    filtered_messages = [
                        msg for msg in prepared_messages if msg["role"] != "system"
                    ]
                else:
                    filtered_messages = prepared_messages

                # Log request
                request_data = {"messages": filtered_messages, "max_tokens": self.max_tokens}

                if self.provider == LLMProvider.ANTHROPIC:
                    request_data["system"] = self._get_system_prompt()
                else:
                    request_data["system"] = system_prompt

                self._log_api_call("request", request_data)

                # Make API call with appropriate parameters
                if self.client is None:
                    raise RuntimeError("Client not initialized. Call initialize_client() first.")

                # Check if the method is async by inspecting the client implementation
                run_method = self.client.run_interleaved
                is_async = asyncio.iscoroutinefunction(run_method)

                if is_async:
                    # For async implementations (AnthropicClient)
                    if self.provider == LLMProvider.ANTHROPIC:
                        response = await run_method(
                            messages=filtered_messages,
                            system=self._get_system_prompt(),
                            max_tokens=self.max_tokens,
                        )
                    else:
                        response = await run_method(
                            messages=messages,
                            system=system_prompt,
                            max_tokens=self.max_tokens,
                        )
                else:
                    # For non-async implementations (GroqClient, etc.)
                    if self.provider == LLMProvider.ANTHROPIC:
                        response = run_method(
                            messages=filtered_messages,
                            system=self._get_system_prompt(),
                            max_tokens=self.max_tokens,
                        )
                    else:
                        response = run_method(
                            messages=messages,
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

    async def _handle_response(
        self, response: Any, messages: List[Dict[str, Any]], parsed_screen: Dict[str, Any]
    ) -> Tuple[bool, bool]:
        """Handle API response.

        Returns:
            Tuple of (should_continue, action_screenshot_saved)
        """
        action_screenshot_saved = False
        try:
            # Handle Anthropic response format
            if self.provider == LLMProvider.ANTHROPIC:
                if hasattr(response, "content") and isinstance(response.content, list):
                    # Extract text from content blocks
                    for block in response.content:
                        if hasattr(block, "type") and block.type == "text":
                            content = block.text

                            # Try to find JSON in the content
                            try:
                                # First look for JSON block
                                json_content = extract_data(content, "json")
                                parsed_content = json.loads(json_content)
                                logger.info("Successfully parsed JSON from code block")
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
                                    else:
                                        logger.error(f"No JSON found in content: {content}")
                                        continue
                                except json.JSONDecodeError as e:
                                    logger.error(f"Failed to parse JSON from text: {str(e)}")
                                    continue

                            # Clean up Box ID format
                            if "Box ID" in parsed_content and isinstance(
                                parsed_content["Box ID"], str
                            ):
                                parsed_content["Box ID"] = parsed_content["Box ID"].replace(
                                    "Box #", ""
                                )

                            # Add any explanatory text as reasoning if not present
                            if "Explanation" not in parsed_content:
                                # Extract any text before the JSON as reasoning
                                text_before_json = content.split("{")[0].strip()
                                if text_before_json:
                                    parsed_content["Explanation"] = text_before_json

                            # Log the parsed content for debugging
                            logger.info(f"Parsed content: {json.dumps(parsed_content, indent=2)}")

                            # Add response to messages
                            messages.append(
                                {"role": "assistant", "content": json.dumps(parsed_content)}
                            )

                            try:
                                # Execute action with current parsed screen info
                                await self._execute_action(parsed_content, parsed_screen)
                                action_screenshot_saved = True
                            except Exception as e:
                                logger.error(f"Error executing action: {str(e)}")
                                # Add error message to conversation
                                messages.append(
                                    {
                                        "role": "assistant",
                                        "content": f"Error executing action: {str(e)}",
                                        "metadata": {"title": "❌ Error"},
                                    }
                                )
                                return False, action_screenshot_saved

                            # Check if task is complete
                            if parsed_content.get("Action") == "None":
                                return False, action_screenshot_saved
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

                # Add response to messages with stringified content
                messages.append({"role": "assistant", "content": json.dumps(parsed_content)})

                try:
                    # Execute action with current parsed screen info
                    await self._execute_action(parsed_content, parsed_screen)
                    action_screenshot_saved = True
                except Exception as e:
                    logger.error(f"Error executing action: {str(e)}")
                    # Add error message to conversation
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Error executing action: {str(e)}",
                            "metadata": {"title": "❌ Error"},
                        }
                    )
                    return False, action_screenshot_saved

                # Check if task is complete
                if parsed_content.get("Action") == "None":
                    return False, action_screenshot_saved

                return True, action_screenshot_saved
            elif isinstance(content, dict):
                # Handle case where content is already a dictionary
                messages.append({"role": "assistant", "content": json.dumps(content)})

                try:
                    # Execute action with current parsed screen info
                    await self._execute_action(content, parsed_screen)
                    action_screenshot_saved = True
                except Exception as e:
                    logger.error(f"Error executing action: {str(e)}")
                    # Add error message to conversation
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Error executing action: {str(e)}",
                            "metadata": {"title": "❌ Error"},
                        }
                    )
                    return False, action_screenshot_saved

                # Check if task is complete
                if content.get("Action") == "None":
                    return False, action_screenshot_saved

                return True, action_screenshot_saved

            return True, action_screenshot_saved

        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Error: {str(e)}",
                    "metadata": {"title": "❌ Error"},
                }
            )
            raise

    async def _get_parsed_screen_som(self, save_screenshot: bool = True) -> ParseResult:
        """Get parsed screen information with SOM.

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

    async def _process_screen(
        self, parsed_screen: ParseResult, messages: List[Dict[str, Any]]
    ) -> None:
        """Process and add screen info to messages."""
        try:
            # Only add message if we have an image and provider supports it
            if self.provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC]:
                image = parsed_screen.annotated_image_base64 or None
                if image:
                    # Save screen info to current turn directory
                    if self.current_turn_dir:
                        # Save elements as JSON
                        elements_path = os.path.join(self.current_turn_dir, "elements.json")
                        with open(elements_path, "w") as f:
                            # Convert elements to dicts for JSON serialization
                            elements_json = [elem.model_dump() for elem in parsed_screen.elements]
                            json.dump(elements_json, f, indent=2)
                            logger.info(f"Saved elements to {elements_path}")

                    # Format the image content based on the provider
                    if self.provider == LLMProvider.ANTHROPIC:
                        # Compress the image before sending to Anthropic (5MB limit)
                        image_size = len(image)
                        logger.info(f"Image base64 is present, length: {image_size}")

                        # Anthropic has a 5MB limit - check against base64 string length
                        # which is what matters for the API call payload
                        # Use slightly smaller limit (4.9MB) to account for request overhead
                        max_size = int(4.9 * 1024 * 1024)  # 4.9MB

                        # Default media type (will be overridden if compression is needed)
                        media_type = "image/png"

                        # Check if the image already has a media type prefix
                        if image.startswith("data:"):
                            parts = image.split(",", 1)
                            if len(parts) == 2 and "image/jpeg" in parts[0].lower():
                                media_type = "image/jpeg"
                            elif len(parts) == 2 and "image/png" in parts[0].lower():
                                media_type = "image/png"

                        if image_size > max_size:
                            logger.info(
                                f"Image size ({image_size} bytes) exceeds Anthropic limit ({max_size} bytes), compressing..."
                            )
                            image, media_type = compress_image_base64(image, max_size)
                            logger.info(
                                f"Image compressed to {len(image)} bytes with media_type {media_type}"
                            )

                        # Anthropic uses "type": "image"
                        screen_info_msg = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image,
                                    },
                                }
                            ],
                        }
                    else:
                        # OpenAI and others use "type": "image_url"
                        screen_info_msg = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{image}"},
                                }
                            ],
                        }
                    messages.append(screen_info_msg)

        except Exception as e:
            logger.error(f"Error processing screen info: {str(e)}")
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the model."""
        return SYSTEM_PROMPT

    async def _execute_action(self, content: Dict[str, Any], parsed_screen: ParseResult) -> None:
        """Execute the action specified in the content using the tool manager.

        Args:
            content: Dictionary containing the action details
            parsed_screen: Current parsed screen information
        """
        try:
            action = content.get("Action", "").lower()
            if not action:
                return

            # Track if we saved an action-specific screenshot
            action_screenshot_saved = False

            try:
                # Prepare kwargs based on action type
                kwargs = {}

                if action in ["left_click", "right_click", "double_click", "move_cursor"]:
                    try:
                        box_id = int(content["Box ID"])
                        logger.info(f"Processing Box ID: {box_id}")

                        # Calculate click coordinates
                        x, y = await self._calculate_click_coordinates(box_id, parsed_screen)
                        logger.info(f"Calculated coordinates: x={x}, y={y}")

                        kwargs["x"] = x
                        kwargs["y"] = y

                        # Visualize action if screenshot is available
                        if parsed_screen.annotated_image_base64:
                            img_data = parsed_screen.annotated_image_base64
                            # Remove data URL prefix if present
                            if img_data.startswith("data:image"):
                                img_data = img_data.split(",")[1]
                            # Only save visualization for coordinate-based actions
                            self._visualize_action(x, y, img_data)
                            action_screenshot_saved = True

                    except ValueError as e:
                        logger.error(f"Error processing Box ID: {str(e)}")
                        return

                elif action == "drag_to":
                    try:
                        box_id = int(content["Box ID"])
                        x, y = await self._calculate_click_coordinates(box_id, parsed_screen)
                        kwargs.update(
                            {
                                "x": x,
                                "y": y,
                                "button": content.get("button", "left"),
                                "duration": float(content.get("duration", 0.5)),
                            }
                        )

                        # Visualize drag destination if screenshot is available
                        if parsed_screen.annotated_image_base64:
                            img_data = parsed_screen.annotated_image_base64
                            # Remove data URL prefix if present
                            if img_data.startswith("data:image"):
                                img_data = img_data.split(",")[1]
                            # Only save visualization for coordinate-based actions
                            self._visualize_action(x, y, img_data)
                            action_screenshot_saved = True

                    except ValueError as e:
                        logger.error(f"Error processing drag coordinates: {str(e)}")
                        return

                elif action == "type_text":
                    kwargs["text"] = content["Value"]
                    # For type_text, store the value in the action type
                    action_type = f"type_{content['Value'][:20]}"  # Truncate if too long
                elif action == "press_key":
                    kwargs["key"] = content["Value"]
                    action_type = f"press_{content['Value']}"
                elif action == "hotkey":
                    if isinstance(content.get("Value"), list):
                        keys = content["Value"]
                        action_type = f"hotkey_{'_'.join(keys)}"
                    else:
                        # Simply split string format like "command+space" into a list
                        keys = [k.strip() for k in content["Value"].lower().split("+")]
                        action_type = f"hotkey_{content['Value'].replace('+', '_')}"
                    logger.info(f"Preparing hotkey with keys: {keys}")
                    # Get the method but call it with *args instead of **kwargs
                    method = getattr(self.computer.interface, action)
                    await method(*keys)  # Unpack the keys list as positional arguments
                    logger.info(f"Tool execution completed successfully: {action}")

                    # For hotkeys, take a screenshot after the action
                    try:
                        # Get a new screenshot after the action and save it with the action type
                        new_parsed_screen = await self._get_parsed_screen_som(save_screenshot=False)
                        if new_parsed_screen and new_parsed_screen.annotated_image_base64:
                            img_data = new_parsed_screen.annotated_image_base64
                            # Remove data URL prefix if present
                            if img_data.startswith("data:image"):
                                img_data = img_data.split(",")[1]
                            # Save with action type to indicate this is a post-action screenshot
                            self._save_screenshot(img_data, action_type=action_type)
                            action_screenshot_saved = True
                    except Exception as screenshot_error:
                        logger.error(
                            f"Error taking post-hotkey screenshot: {str(screenshot_error)}"
                        )

                    return

                elif action in ["scroll_down", "scroll_up"]:
                    clicks = int(content.get("amount", 1))
                    kwargs["clicks"] = clicks
                    action_type = f"scroll_{action.split('_')[1]}_{clicks}"

                    # Visualize scrolling if screenshot is available
                    if parsed_screen.annotated_image_base64:
                        img_data = parsed_screen.annotated_image_base64
                        # Remove data URL prefix if present
                        if img_data.startswith("data:image"):
                            img_data = img_data.split(",")[1]
                        direction = "down" if action == "scroll_down" else "up"
                        # For scrolling, we only save the visualization to avoid duplicate images
                        self._visualize_scroll(direction, clicks, img_data)
                        action_screenshot_saved = True

                else:
                    logger.warning(f"Unknown action: {action}")
                    return

                # Execute tool and handle result
                try:
                    method = getattr(self.computer.interface, action)
                    logger.info(f"Found method for action '{action}': {method}")
                    await method(**kwargs)
                    logger.info(f"Tool execution completed successfully: {action}")

                    # For non-coordinate based actions that don't already have visualizations,
                    # take a new screenshot after the action
                    if not action_screenshot_saved:
                        # Take a new screenshot
                        try:
                            # Get a new screenshot after the action and save it with the action type
                            new_parsed_screen = await self._get_parsed_screen_som(
                                save_screenshot=False
                            )
                            if new_parsed_screen and new_parsed_screen.annotated_image_base64:
                                img_data = new_parsed_screen.annotated_image_base64
                                # Remove data URL prefix if present
                                if img_data.startswith("data:image"):
                                    img_data = img_data.split(",")[1]
                                # Save with action type to indicate this is a post-action screenshot
                                if "action_type" in locals():
                                    self._save_screenshot(img_data, action_type=action_type)
                                else:
                                    self._save_screenshot(img_data, action_type=action)
                                # Update the action screenshot flag for this turn
                                action_screenshot_saved = True
                        except Exception as screenshot_error:
                            logger.error(
                                f"Error taking post-action screenshot: {str(screenshot_error)}"
                            )

                except AttributeError as e:
                    logger.error(f"Method not found for action '{action}': {str(e)}")
                    return
                except Exception as tool_error:
                    logger.error(f"Tool execution failed: {str(tool_error)}")
                    return

            except Exception as e:
                logger.error(f"Error executing action {action}: {str(e)}")
                return

        except Exception as e:
            logger.error(f"Error in _execute_action: {str(e)}")
            return

    async def _calculate_click_coordinates(
        self, box_id: int, parsed_screen: ParseResult
    ) -> Tuple[int, int]:
        """Calculate click coordinates based on box ID.

        Args:
            box_id: The ID of the box to click
            parsed_screen: The parsed screen information

        Returns:
            Tuple of (x, y) coordinates

        Raises:
            ValueError: If box_id is invalid or missing from parsed screen
        """
        # First try to use structured elements data
        logger.info(f"Elements count: {len(parsed_screen.elements)}")

        # Try to find element with matching ID
        for element in parsed_screen.elements:
            if element.id == box_id:
                logger.info(f"Found element with ID {box_id}: {element}")
                bbox = element.bbox

                # Get screen dimensions from the metadata if available, or fallback
                width = parsed_screen.metadata.width if parsed_screen.metadata else 1920
                height = parsed_screen.metadata.height if parsed_screen.metadata else 1080
                logger.info(f"Screen dimensions: width={width}, height={height}")

                # Calculate center of the box in pixels
                center_x = int((bbox.x1 + bbox.x2) / 2 * width)
                center_y = int((bbox.y1 + bbox.y2) / 2 * height)
                logger.info(f"Calculated center: ({center_x}, {center_y})")

                # Validate coordinates - if they're (0,0) or unreasonably small,
                # use a default position in the center of the screen
                if center_x == 0 and center_y == 0:
                    logger.warning("Got (0,0) coordinates, using fallback position")
                    center_x = width // 2
                    center_y = height // 2
                    logger.info(f"Using fallback center: ({center_x}, {center_y})")

                return center_x, center_y

        # If we couldn't find the box, use center of screen
        logger.error(
            f"Box ID {box_id} not found in structured elements (count={len(parsed_screen.elements)})"
        )

        # Use center of screen as fallback
        width = parsed_screen.metadata.width if parsed_screen.metadata else 1920
        height = parsed_screen.metadata.height if parsed_screen.metadata else 1080
        logger.warning(f"Using fallback position in center of screen ({width//2}, {height//2})")
        return width // 2, height // 2

    async def run(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the agent loop with provided messages.

        Args:
            messages: List of message objects

        Yields:
            Dict containing response data
        """
        # Keep track of conversation history
        conversation_history = messages.copy()

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

                # Process screen info and update messages
                await self._process_screen(parsed_screen, conversation_history)

                # Get system prompt
                system_prompt = self._get_system_prompt()

                # Make API call with retries
                response = await self._make_api_call(conversation_history, system_prompt)

                # Handle the response (may execute actions)
                # Returns: (should_continue, action_screenshot_saved)
                should_continue, new_screenshot_saved = await self._handle_response(
                    response, conversation_history, parsed_screen
                )

                # Update whether an action screenshot was saved this turn
                action_screenshot_saved = action_screenshot_saved or new_screenshot_saved

                # Yield the response to the caller
                yield {"response": response}

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
