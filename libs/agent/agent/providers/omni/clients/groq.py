"""Groq client implementation."""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple

from groq import Groq
import re
from .utils import is_image_path
from .base import BaseOmniClient

logger = logging.getLogger(__name__)


class GroqClient(BaseOmniClient):
    """Client for making Groq API calls."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-r1-distill-llama-70b",
        max_tokens: int = 4096,
        temperature: float = 0.6,
    ):
        """Initialize Groq client.

        Args:
            api_key: Groq API key (if not provided, will try to get from env)
            model: Model name to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
        """
        super().__init__(api_key=api_key, model=model)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("No Groq API key provided")

        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = Groq(api_key=self.api_key)
        self.model: str = model  # Add explicit type annotation

    def run_interleaved(
        self, messages: List[Dict[str, Any]], system: str, max_tokens: Optional[int] = None
    ) -> tuple[str, int]:
        """Run interleaved chat completion.

        Args:
            messages: List of message dicts
            system: System prompt
            max_tokens: Optional max tokens override

        Returns:
            Tuple of (response text, token usage)
        """
        # Avoid using system messages for R1
        final_messages = [{"role": "user", "content": system}]

        # Process messages
        if isinstance(messages, list):
            for item in messages:
                if isinstance(item, dict):
                    # For dict items, concatenate all text content, ignoring images
                    text_contents = []
                    for cnt in item["content"]:
                        if isinstance(cnt, str):
                            if not is_image_path(cnt):  # Skip image paths
                                text_contents.append(cnt)
                        else:
                            text_contents.append(str(cnt))

                    if text_contents:  # Only add if there's text content
                        message = {"role": "user", "content": " ".join(text_contents)}
                        final_messages.append(message)
                else:  # str
                    message = {"role": "user", "content": item}
                    final_messages.append(message)

        elif isinstance(messages, str):
            final_messages.append({"role": "user", "content": messages})

        try:
            completion = self.client.chat.completions.create(  # type: ignore
                model=self.model,
                messages=final_messages,  # type: ignore
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                top_p=0.95,
                stream=False,
            )

            response = completion.choices[0].message.content
            final_answer = response.split("</think>\n")[-1] if "</think>" in response else response
            final_answer = final_answer.replace("<output>", "").replace("</output>", "")
            token_usage = completion.usage.total_tokens

            return final_answer, token_usage

        except Exception as e:
            logger.error(f"Error in Groq API call: {e}")
            raise
