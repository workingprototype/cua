"""MLX LVM client implementation."""

import io
import logging
import base64
import tempfile
import os
import re
from typing import Dict, List, Optional, Any, cast, Tuple
from PIL import Image

from .base import BaseUITarsClient
import mlx.core as mx
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config
from transformers.tokenization_utils import PreTrainedTokenizer

logger = logging.getLogger(__name__)


class MLXVLMUITarsClient(BaseUITarsClient):
    """MLX LVM client implementation class."""

    def __init__(
        self, 
        model: str = "mlx-community/UI-TARS-1.5-7B-4bit", 
        force_resolution: Optional[Tuple[int, int]] = (1512, 982)
    ):
        """Initialize MLX LVM client.

        Args:
            model: Model name or path (defaults to mlx-community/UI-TARS-1.5-7B-4bit)
            force_resolution: Optional target resolution to resize images to (width, height).
                              If None, images will not be resized.
        """
        # Load model and processor
        model_obj, processor = load(model)
        self.config = load_config(model)
        self.model = model_obj
        self.processor = processor
        self.model_name = model
        self.force_resolution = force_resolution


    def _remap_coordinates(self, text: str, original_size: Tuple[int, int], target_size: Tuple[int, int]) -> str:
        """Remap coordinates in box tokens based on image resizing.
        
        Args:
            text: Text containing box tokens
            original_size: Original image size (width, height)
            target_size: Target image size (width, height)
            
        Returns:
            Text with remapped coordinates
        """
        # Find all box tokens
        box_pattern = r"<\|box_start\|>\((\d+),\s*(\d+)\)<\|box_end\|>"
        
        def remap_coords(match):
            x, y = int(match.group(1)), int(match.group(2))
            # Scale coordinates to new dimensions
            new_x = int(x * target_size[0] / original_size[0])
            new_y = int(y * target_size[1] / original_size[1])
            return f"<|box_start|>({new_x},{new_y})<|box_end|>"
        
        return re.sub(box_pattern, remap_coords, text)

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
        # Ensure the system message is included
        if not any(msg.get("role") == "system" for msg in messages):
            messages = [{"role": "system", "content": system}] + messages
        
        # Create a deep copy of messages to avoid modifying the original
        processed_messages = messages.copy()
        
        # Extract images and process messages if force_resolution is set
        images = []
        original_sizes = {}  # Track original sizes of images for coordinate remapping
        image_index = 0
        
        for msg_idx, msg in enumerate(messages):
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
                
            # Create a copy of the content list to modify
            processed_content = []
            
            for item_idx, item in enumerate(content):
                if item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    pil_image = None
                    
                    if image_url.startswith("data:image/"):
                        # Extract base64 data
                        base64_data = image_url.split(',')[1]
                        # Convert base64 to PIL Image
                        image_data = base64.b64decode(base64_data)
                        pil_image = Image.open(io.BytesIO(image_data))
                    else:
                        # Handle file path or URL
                        pil_image = Image.open(image_url)
                    
                    # Store original image size for coordinate mapping
                    original_sizes[image_index] = pil_image.size
                    
                    # Resize image if force_resolution is set
                    if self.force_resolution:
                        pil_image = pil_image.resize(self.force_resolution)
                    
                    images.append(pil_image)
                    image_index += 1
                
                # Copy items to processed content list
                processed_content.append(item.copy())
            
            # Update the processed message content
            processed_messages[msg_idx] = msg.copy()
            processed_messages[msg_idx]["content"] = processed_content
        
        # Remap coordinates in messages with box tokens if force_resolution is set
        if self.force_resolution and original_sizes:
            for msg_idx, msg in enumerate(processed_messages):
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                
                for item_idx, item in enumerate(content):
                    if item.get("type") == "text":
                        text_content = item.get("text", "")
                        
                        # Check if there are any box tokens to remap
                        if "<|box_start|>" in text_content:
                            # Use the first image's dimensions as reference (most common case)
                            if 0 in original_sizes:
                                orig_size = original_sizes[0]
                                processed_messages[msg_idx]["content"][item_idx]["text"] = self._remap_coordinates(
                                    text_content, orig_size, self.force_resolution
                                )
        
        try:
            # Format prompt according to model requirements using the processor directly
            prompt = self.processor.apply_chat_template(
                processed_messages,  # Use processed messages instead of original
                tokenize=False,
                add_generation_prompt=True
            )
            tokenizer = cast(PreTrainedTokenizer, self.processor)
            
            # Generate response
            output = generate(
                self.model, 
                tokenizer, 
                str(prompt), 
                images, 
                verbose=False,
                max_tokens=max_tokens
            )
            
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
        
        # Remap coordinates in the response back to original image space if needed
        if self.force_resolution and original_sizes and 0 in original_sizes:
            # Get original image size (using the first image)
            orig_size = original_sizes[0]
            
            # Check if output contains box tokens that need remapping
            if "<|box_start|>" in output:
                # Remap coordinates from model space back to original image space
                # We just swap the arguments - from force_resolution back to original size
                output = self._remap_coordinates(output, self.force_resolution, orig_size)
        
        # Format response to match OpenAI format
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": output
                    },
                    "finish_reason": "stop"
                }
            ],
            "model": self.model_name
        }
        
        return response
