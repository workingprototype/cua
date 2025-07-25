"""
Adapters package for agent - Custom LLM adapters for LiteLLM
"""

from .huggingfacelocal_adapter import HuggingFaceLocalAdapter

__all__ = [
    "HuggingFaceLocalAdapter",
]
