"""Hugging Face Transformers client implementation."""

import io
import logging
import base64
import tempfile
import os
import re
import math
from typing import Dict, List, Optional, Any, cast, Tuple
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

from .base import BaseUITarsClient

logger = logging.getLogger(__name__)

# Constants for smart_resize
IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200


def round_by_factor(number: float, factor: int) -> int:
    """Returns the closest integer to 'number' that is divisible by 'factor'."""
    return round(number / factor) * factor


def ceil_by_factor(number: float, factor: int) -> int:
    """Returns the smallest integer greater than or equal to 'number' that is divisible by 'factor'."""
    return math.ceil(number / factor) * factor


def floor_by_factor(number: float, factor: int) -> int:
    """Returns the largest integer less than or equal to 'number' that is divisible by 'factor'."""
    return math.floor(number / factor) * factor


def smart_resize(
    height: int, width: int, factor: int = IMAGE_FACTOR, min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS
) -> tuple[int, int]:
    """
    Rescales the image so that the following conditions are met:

    1. Both dimensions (height and width) are divisible by 'factor'.
    2. The total number of pixels is within the range ['min_pixels', 'max_pixels'].
    3. The aspect ratio of the image is maintained as closely as possible.
    """
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"absolute aspect ratio must be smaller than {MAX_RATIO}, got {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar


class HuggingFaceUITarsClient(BaseUITarsClient):
    """Hugging Face Transformers client implementation class."""

    def __init__(
        self, 
        model: str = "microsoft/UI-TARS-7B",
        api_key: Optional[str] = None,
        device: Optional[str] = None
    ):
        """Initialize Hugging Face Transformers client.

        Args:
            model: Model name or path (defaults to microsoft/UI-TARS-7B)
            api_key: Optional API key (not used for local models)
            device: Device to run the model on (auto-detected if None)
        """
        super().__init__(api_key=api_key, model=model)
        
        # Auto-detect device if not specified
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        
        self.device = device
        logger.info(f"Using device: {self.device}")
        
        # Load model and processor
        try:
            logger.info(f"Loading model: {model}")
            self.processor = AutoProcessor.from_pretrained(model)
            self.model_obj = AutoModelForImageTextToText.from_pretrained(
                model,
                torch_dtype=torch.float16 if device != "cpu" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True
            )
            
            if device != "cuda":  # device_map="auto" handles CUDA placement
                self.model_obj = self.model_obj.to(device)
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model {model}: {str(e)}")
            raise
        
        self.model_name = model

    def _process_coordinates(self, text: str, original_size: Tuple[int, int], model_size: Tuple[int, int]) -> str:
        """Process coordinates in box tokens based on image resizing using smart_resize approach.
        
        Args:
            text: Text containing box tokens
            original_size: Original image size (width, height)
            model_size: Model processed image size (width, height)
            
        Returns:
            Text with processed coordinates
        """
        # Find all box tokens
        box_pattern = r"<\|box_start\|>\((\d+),\s*(\d+)\)<\|box_end\|>"
        
        def process_coords(match):
            model_x, model_y = int(match.group(1)), int(match.group(2))
            # Scale coordinates from model space to original image space
            # Both original_size and model_size are in (width, height) format
            orig_width, orig_height = original_size
            model_width, model_height = model_size
            
            # Calculate scaling factors
            scale_x = orig_width / model_width
            scale_y = orig_height / model_height
            
            # Apply scaling
            orig_x = int(model_x * scale_x)
            orig_y = int(model_y * scale_y)
            
            return f"<|box_start|>({orig_x}, {orig_y})<|box_end|>"
        
        return re.sub(box_pattern, process_coords, text)

    async def run_interleaved(
        self, messages: List[Dict[str, Any]], system: str, max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run interleaved chat completion.

        Args:
            messages: List of message dicts
            system: System prompt
            max_tokens: Optional max tokens override

        Returns:
            Response dict
        """
        if max_tokens is None:
            max_tokens = 2048
        
        # Process messages and extract images
        processed_messages = []
        images = []
        original_sizes = {}
        model_sizes = {}
        image_index = 0
        
        for msg_idx, msg in enumerate(messages):
            processed_content = []
            
            # Handle different message content formats
            if isinstance(msg.get("content"), str):
                # Simple text message
                processed_content = msg["content"]
            elif isinstance(msg.get("content"), list):
                # Multi-modal message with text and images
                for item in msg["content"]:
                    if item.get("type") == "text":
                        processed_content.append(item)
                    elif item.get("type") == "image_url":
                        # Extract and process image
                        image_url = item["image_url"]["url"]
                        
                        # Handle base64 encoded images
                        if image_url.startswith("data:image"):
                            # Extract base64 data
                            base64_data = image_url.split(",")[1]
                            image_data = base64.b64decode(base64_data)
                            pil_image = Image.open(io.BytesIO(image_data))
                        else:
                            # Handle file paths or URLs
                            pil_image = Image.open(image_url)
                        
                        # Convert to RGB if necessary
                        if pil_image.mode != "RGB":
                            pil_image = pil_image.convert("RGB")
                        
                        # Store original size
                        original_width, original_height = pil_image.size
                        original_sizes[image_index] = (original_width, original_height)
                        
                        # Calculate new dimensions using smart_resize
                        new_height, new_width = smart_resize(original_height, original_width)
                        model_sizes[image_index] = (new_width, new_height)
                        
                        # Resize the image using the calculated dimensions from smart_resize
                        resized_image = pil_image.resize((new_width, new_height))
                        images.append(resized_image)
                        image_index += 1
                    
                    # Copy items to processed content list
                    processed_content.append(item.copy())
            
            # Update the processed message content
            processed_messages.append(msg.copy())
            processed_messages[-1]["content"] = processed_content
        
        logger.info(f"Resized {len(images)} images from {original_sizes.get(0, 'N/A')} to {model_sizes.get(0, 'N/A')}")
        
        # Process user text input with box coordinates after image processing
        for msg_idx, msg in enumerate(processed_messages):
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                if "<|box_start|>" in msg.get("content") and original_sizes and model_sizes and 0 in original_sizes and 0 in model_sizes:
                    orig_size = original_sizes[0]
                    model_size = model_sizes[0]
                    # Swap arguments to perform inverse transformation for user input
                    processed_messages[msg_idx]["content"] = self._process_coordinates(msg["content"], model_size, orig_size)
        
        try:
            # Format prompt according to model requirements
            if hasattr(self.processor, 'apply_chat_template'):
                prompt = self.processor.apply_chat_template(
                    processed_messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                # Fallback to simple concatenation if no chat template
                prompt_parts = []
                if system:
                    prompt_parts.append(f"System: {system}")
                
                for msg in processed_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        # Extract text from multi-modal content
                        text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
                        content = " ".join(text_parts)
                    prompt_parts.append(f"{role.capitalize()}: {content}")
                
                prompt_parts.append("Assistant:")
                prompt = "\n".join(prompt_parts)
            
            logger.info("Generating response...")
            
            # Prepare inputs
            if images:
                inputs = self.processor(
                    text=prompt,
                    images=images,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
            else:
                inputs = self.processor(
                    text=prompt,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
            
            # Generate response
            with torch.no_grad():
                generated_ids = self.model_obj.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.processor.tokenizer.eos_token_id
                )
            
            # Decode response
            generated_text = self.processor.batch_decode(
                generated_ids[:, inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )[0]
            
            # Create usage statistics (approximate)
            input_tokens = inputs['input_ids'].shape[1]
            output_tokens = generated_ids.shape[1] - input_tokens
            usage = {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
            
            logger.info(f"Generated response: {generated_text[:100]}...")
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": f"Error generating response: {str(e)}"
                        },
                        "finish_reason": "error"
                    }
                ],
                "model": self.model_name,
                "error": str(e)
            }
        
        # Process coordinates in the response back to original image space
        if original_sizes and model_sizes and 0 in original_sizes and 0 in model_sizes:
            # Get original image size and model size (using the first image)
            orig_size = original_sizes[0]
            model_size = model_sizes[0]
            
            # Check if output contains box tokens that need processing
            if "<|box_start|>" in generated_text:
                # Process coordinates from model space back to original image space
                generated_text = self._process_coordinates(generated_text, orig_size, model_size)
        
        # Format response to match OpenAI format
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": generated_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "model": self.model_name,
            "usage": usage
        }
        
        return response
