"""
Adapters package for agent - Custom LLM adapters for LiteLLM
"""

from .huggingfacelocal_adapter import HuggingFaceLocalAdapter
from .human_adapter import HumanAdapter

__all__ = [
    "HuggingFaceLocalAdapter",
    "HumanAdapter",
]
