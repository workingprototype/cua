"""Parser implementation for the Omni provider."""

import logging
from typing import Any, Dict, List, Optional, Tuple
import base64
from PIL import Image
from io import BytesIO
import json
import torch

# Import from the SOM package
from som import OmniParser as OmniDetectParser
from som.models import ParseResult, BoundingBox, UIElement, ImageData, ParserMetadata

logger = logging.getLogger(__name__)


class OmniParser:
    """Parser for handling responses from multiple providers."""

    # Class-level shared OmniDetectParser instance
    _shared_parser = None

    def __init__(self, force_device: Optional[str] = None):
        """Initialize the OmniParser.

        Args:
            force_device: Optional device to force for detection (cpu/cuda/mps)
        """
        self.response_buffer = []

        # Use shared parser if available, otherwise create a new one
        if OmniParser._shared_parser is None:
            logger.info("Initializing shared OmniDetectParser...")

            # Determine the best device to use
            device = force_device
            if not device:
                if torch.cuda.is_available():
                    device = "cuda"
                elif (
                    hasattr(torch, "backends")
                    and hasattr(torch.backends, "mps")
                    and torch.backends.mps.is_available()
                ):
                    device = "mps"
                else:
                    device = "cpu"

            logger.info(f"Using device: {device} for OmniDetectParser")
            self.detect_parser = OmniDetectParser(force_device=device)

            # Preload the detection model to avoid repeated loading
            try:
                # Access the detector to trigger model loading
                detector = self.detect_parser.detector
                if detector.model is None:
                    logger.info("Preloading detection model...")
                    detector.load_model()
                    logger.info("Detection model preloaded successfully")
            except Exception as e:
                logger.error(f"Error preloading detection model: {str(e)}")

            # Store as shared instance
            OmniParser._shared_parser = self.detect_parser
        else:
            logger.info("Using existing shared OmniDetectParser")
            self.detect_parser = OmniParser._shared_parser

    async def parse_screen(self, computer: Any) -> ParseResult:
        """Parse a screenshot and extract screen information.

        Args:
            computer: Computer instance

        Returns:
            ParseResult with screen elements and image data
        """
        try:
            # Get screenshot from computer
            logger.info("Taking screenshot...")
            screenshot = await computer.interface.screenshot()

            # Log screenshot info
            logger.info(f"Screenshot type: {type(screenshot)}")
            logger.info(f"Screenshot is bytes: {isinstance(screenshot, bytes)}")
            logger.info(f"Screenshot is str: {isinstance(screenshot, str)}")
            logger.info(f"Screenshot length: {len(screenshot) if screenshot else 0}")

            # If screenshot is a string (likely base64), convert it to bytes
            if isinstance(screenshot, str):
                try:
                    screenshot = base64.b64decode(screenshot)
                    logger.info("Successfully converted base64 string to bytes")
                    logger.info(f"Decoded bytes length: {len(screenshot)}")
                except Exception as e:
                    logger.error(f"Error decoding base64: {str(e)}")
                    logger.error(f"First 100 chars of screenshot string: {screenshot[:100]}")

            # Pass screenshot to OmniDetectParser
            logger.info("Passing screenshot to OmniDetectParser...")
            parse_result = self.detect_parser.parse(
                screenshot_data=screenshot, box_threshold=0.3, iou_threshold=0.1, use_ocr=True
            )
            logger.info("Screenshot parsed successfully")
            logger.info(f"Parse result has {len(parse_result.elements)} elements")

            # Log element IDs for debugging
            for i, elem in enumerate(parse_result.elements):
                logger.info(
                    f"Element {i+1} (ID: {elem.id}): {elem.type} with confidence {elem.confidence:.3f}"
                )

            return parse_result

        except Exception as e:
            logger.error(f"Error parsing screen: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

            # Create a minimal valid result for error cases
            return ParseResult(
                elements=[],
                annotated_image_base64="",
                parsed_content_list=[f"Error: {str(e)}"],
                metadata=ParserMetadata(
                    image_size=(0, 0),
                    num_icons=0,
                    num_text=0,
                    device="cpu",
                    ocr_enabled=False,
                    latency=0.0,
                ),
            )

    def parse_tool_call(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a tool call from the response.

        Args:
            response: Response from the provider

        Returns:
            Parsed tool call or None if no tool call found
        """
        try:
            # Handle Anthropic format
            if "tool_calls" in response:
                tool_call = response["tool_calls"][0]
                return {
                    "name": tool_call["function"]["name"],
                    "arguments": tool_call["function"]["arguments"],
                }

            # Handle OpenAI format
            if "function_call" in response:
                return {
                    "name": response["function_call"]["name"],
                    "arguments": response["function_call"]["arguments"],
                }

            # Handle Groq format (OpenAI-compatible)
            if "choices" in response and response["choices"]:
                choice = response["choices"][0]
                if "function_call" in choice:
                    return {
                        "name": choice["function_call"]["name"],
                        "arguments": choice["function_call"]["arguments"],
                    }

            return None

        except Exception as e:
            logger.error(f"Error parsing tool call: {str(e)}")
            return None

    def parse_response(self, response: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Parse a response from any provider.

        Args:
            response: Response from the provider

        Returns:
            Tuple of (content, metadata)
        """
        try:
            content = ""
            metadata = {}

            # Handle Anthropic format
            if "content" in response and isinstance(response["content"], list):
                for item in response["content"]:
                    if item["type"] == "text":
                        content += item["text"]

            # Handle OpenAI format
            elif "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"]

            # Handle direct content
            elif isinstance(response.get("content"), str):
                content = response["content"]

            # Extract metadata if present
            if "metadata" in response:
                metadata = response["metadata"]

            return content, metadata

        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return str(e), {"error": True}

    def format_for_provider(
        self, messages: List[Dict[str, Any]], provider: str
    ) -> List[Dict[str, Any]]:
        """Format messages for a specific provider.

        Args:
            messages: List of messages to format
            provider: Provider to format for

        Returns:
            Formatted messages
        """
        try:
            formatted = []

            for msg in messages:
                formatted_msg = {"role": msg["role"]}

                # Handle content formatting
                if isinstance(msg["content"], list):
                    # For providers that support multimodal
                    if provider in ["anthropic", "openai"]:
                        formatted_msg["content"] = msg["content"]
                    else:
                        # Extract text only for other providers
                        text_content = next(
                            (item["text"] for item in msg["content"] if item["type"] == "text"), ""
                        )
                        formatted_msg["content"] = text_content
                else:
                    formatted_msg["content"] = msg["content"]

                formatted.append(formatted_msg)

            return formatted

        except Exception as e:
            logger.error(f"Error formatting messages: {str(e)}")
            return messages  # Return original messages on error
