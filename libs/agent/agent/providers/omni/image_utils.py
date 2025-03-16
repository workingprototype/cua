"""Image processing utilities for the Cua provider."""

import base64
import logging
import re
from io import BytesIO
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


def decode_base64_image(img_base64: str) -> Optional[Image.Image]:
    """Decode a base64 encoded image to a PIL Image.

    Args:
        img_base64: Base64 encoded image, may include data URL prefix

    Returns:
        PIL Image or None if decoding fails
    """
    try:
        # Remove data URL prefix if present
        if img_base64.startswith("data:image"):
            img_base64 = img_base64.split(",")[1]

        # Decode base64 to bytes
        img_data = base64.b64decode(img_base64)

        # Convert bytes to PIL Image
        return Image.open(BytesIO(img_data))
    except Exception as e:
        logger.error(f"Error decoding base64 image: {str(e)}")
        return None


def encode_image_base64(img: Image.Image, format: str = "PNG") -> str:
    """Encode a PIL Image to base64.

    Args:
        img: PIL Image to encode
        format: Image format (PNG, JPEG, etc.)

    Returns:
        Base64 encoded image string
    """
    try:
        buffered = BytesIO()
        img.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        return ""


def clean_base64_data(img_base64: str) -> str:
    """Clean base64 image data by removing data URL prefix.

    Args:
        img_base64: Base64 encoded image, may include data URL prefix

    Returns:
        Clean base64 string without prefix
    """
    if img_base64.startswith("data:image"):
        return img_base64.split(",")[1]
    return img_base64


def extract_base64_from_text(text: str) -> Optional[str]:
    """Extract base64 image data from a text string.

    Args:
        text: Text potentially containing base64 image data

    Returns:
        Base64 string or None if not found
    """
    # Look for data URL pattern
    data_url_pattern = r"data:image/[^;]+;base64,([a-zA-Z0-9+/=]+)"
    match = re.search(data_url_pattern, text)
    if match:
        return match.group(1)

    # Look for plain base64 pattern (basic heuristic)
    base64_pattern = r"([a-zA-Z0-9+/=]{100,})"
    match = re.search(base64_pattern, text)
    if match:
        return match.group(1)

    return None


def get_image_dimensions(img_base64: str) -> Tuple[int, int]:
    """Get the dimensions of a base64 encoded image.

    Args:
        img_base64: Base64 encoded image

    Returns:
        Tuple of (width, height) or (0, 0) if decoding fails
    """
    img = decode_base64_image(img_base64)
    if img:
        return img.size
    return (0, 0)
