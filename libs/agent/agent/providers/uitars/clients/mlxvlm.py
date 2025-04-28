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
        # Ensure the system message is included
        if not any(msg.get("role") == "system" for msg in messages):
            messages = [{"role": "system", "content": system}] + messages
            
        # Extract any images from the messages
        images = []
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "image_url":
                        image_url = item.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image/"):
                            # Extract base64 data
                            base64_data = image_url.split(',')[1]
                            
                            # Convert base64 to PIL Image
                            image_data = base64.b64decode(base64_data)
                            pil_image = Image.open(io.BytesIO(image_data))
                            images.append(pil_image)
                        else:
                            # Handle file path or URL
                            pil_image = Image.open(image_url)
                            images.append(pil_image)
        
        try:
            # Format prompt according to model requirements using the processor directly
            prompt = self.processor.apply_chat_template(
                messages,
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
