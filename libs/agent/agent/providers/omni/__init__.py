"""Omni provider implementation."""

# The OmniComputerAgent has been replaced by the unified ComputerAgent
# which can be found in agent.core.agent
from .types import LLMProvider
from .experiment import ExperimentManager
from .visualization import visualize_click, visualize_scroll, calculate_element_center
from .image_utils import (
    decode_base64_image,
    encode_image_base64,
    clean_base64_data,
    extract_base64_from_text,
    get_image_dimensions,
)

__all__ = [
    "LLMProvider",
    "ExperimentManager",
    "visualize_click",
    "visualize_scroll",
    "calculate_element_center",
    "decode_base64_image",
    "encode_image_base64",
    "clean_base64_data",
    "extract_base64_from_text",
    "get_image_dimensions",
]
