"""MLX LVM client implementation."""

import io
import logging
import base64
import tempfile
import os
from typing import Dict, List, Optional, Any, cast
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

    def __init__(self, model: str = "mlx-community/UI-TARS-1.5-7B-4bit"):
        """Initialize MLX LVM client.

        Args:
            model: Model name or path (defaults to mlx-community/UI-TARS-1.5-7B-4bit)
        """
        # Load model and processor
        model_obj, processor = load(model)
        self.config = load_config(model)
        self.model = model_obj
        self.processor = processor


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
        # Extract text and images from messages
        prompt_parts = []
        images = []
        
        # Add system message first
        prompt_parts.append(system)
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", [])
            
            # Handle different content formats
            if isinstance(content, str):
                # If content is a string, just add it as text
                prompt_parts.append(f"{role}: {content}")
            elif isinstance(content, list):
                # If content is a list, process each item
                text_parts = []
                
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "image_url":
                        # Extract image URL and add to images list
                        image_url = item.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image/"):
                            # Extract base64 data and convert to URL or save as temp file
                            # For now, we'll just store the URL directly
                            images.append(image_url)
                
                # Add text parts to prompt
                if text_parts:
                    prompt_parts.append(f"{role}: {''.join(text_parts)}")
        
        # Combine all text parts into a single prompt
        combined_prompt = "\n".join(prompt_parts)
        processed_images = []
        for img in images:
            if img.startswith('data:image/'):
                # Extract base64 data
                base64_data = img.split(',')[1]
                
                # Convert base64 to PIL Image directly
                image_data = base64.b64decode(base64_data)
                pil_image = Image.open(io.BytesIO(image_data))
                processed_images.append(pil_image)
            else:
                # Assume it's already a valid URL or path
                # For file paths or URLs, we'll load them with PIL
                pil_image = Image.open(img)
                processed_images.append(pil_image)
        
        try:
            # Format prompt according to model requirements
            formatted_prompt = apply_chat_template(
                self.processor, self.config, str(combined_prompt), num_images=len(processed_images)
            )
            
            # Cast processor to PreTrainedTokenizer to satisfy type checker
            tokenizer = cast(PreTrainedTokenizer, self.processor)
            
            # Generate response
            output = generate(
                self.model, 
                tokenizer, 
                str(formatted_prompt), 
                processed_images, 
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
                "model": self.model,
                "error": str(e)
            }
        
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
            "model": self.model
        }
        
        return response
