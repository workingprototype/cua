"""Utility functions for Omni provider."""

import base64
import io
import logging
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)


def compress_image_base64(
    base64_str: str, max_size_bytes: int = 5 * 1024 * 1024, quality: int = 90
) -> tuple[str, str]:
    """Compress a base64 encoded image to ensure it's below a certain size.

    Args:
        base64_str: Base64 encoded image string (with or without data URL prefix)
        max_size_bytes: Maximum size in bytes (default: 5MB)
        quality: Initial JPEG quality (0-100)

    Returns:
        tuple[str, str]: (Compressed base64 encoded image, media_type)
    """
    # Handle data URL prefix if present (e.g., "data:image/png;base64,...")
    original_prefix = ""
    media_type = "image/png"  # Default media type

    if base64_str.startswith("data:"):
        parts = base64_str.split(",", 1)
        if len(parts) == 2:
            original_prefix = parts[0] + ","
            base64_str = parts[1]
            # Try to extract media type from the prefix
            if "image/jpeg" in original_prefix.lower():
                media_type = "image/jpeg"
            elif "image/png" in original_prefix.lower():
                media_type = "image/png"

    # Check if the base64 string is small enough already
    if len(base64_str) <= max_size_bytes:
        logger.info(f"Image already within size limit: {len(base64_str)} bytes")
        return original_prefix + base64_str, media_type

    try:
        # Decode base64
        img_data = base64.b64decode(base64_str)
        img_size = len(img_data)
        logger.info(f"Original image size: {img_size} bytes")

        # Open image
        img = Image.open(io.BytesIO(img_data))

        # First, try to compress as PNG (maintains transparency if present)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        compressed_data = buffer.getvalue()
        compressed_b64 = base64.b64encode(compressed_data).decode("utf-8")

        if len(compressed_b64) <= max_size_bytes:
            logger.info(f"Compressed to {len(compressed_data)} bytes as PNG")
            return compressed_b64, "image/png"

        # Strategy 1: Try reducing quality with JPEG format
        current_quality = quality
        while current_quality > 20:
            buffer = io.BytesIO()
            # Convert to RGB if image has alpha channel (JPEG doesn't support transparency)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                logger.info("Converting transparent image to RGB for JPEG compression")
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
                rgb_img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
            else:
                img.save(buffer, format="JPEG", quality=current_quality, optimize=True)

            buffer.seek(0)
            compressed_data = buffer.getvalue()
            compressed_b64 = base64.b64encode(compressed_data).decode("utf-8")

            if len(compressed_b64) <= max_size_bytes:
                logger.info(
                    f"Compressed to {len(compressed_data)} bytes with JPEG quality {current_quality}"
                )
                return compressed_b64, "image/jpeg"

            # Reduce quality and try again
            current_quality -= 10

        # Strategy 2: If quality reduction isn't enough, reduce dimensions
        scale_factor = 0.8
        current_img = img

        while scale_factor > 0.3:
            # Resize image
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            current_img = img.resize((new_width, new_height), Image.LANCZOS)

            # Try with reduced size and quality
            buffer = io.BytesIO()
            # Convert to RGB if necessary for JPEG
            if current_img.mode in ("RGBA", "LA") or (
                current_img.mode == "P" and "transparency" in current_img.info
            ):
                rgb_img = Image.new("RGB", current_img.size, (255, 255, 255))
                rgb_img.paste(
                    current_img, mask=current_img.split()[3] if current_img.mode == "RGBA" else None
                )
                rgb_img.save(buffer, format="JPEG", quality=70, optimize=True)
            else:
                current_img.save(buffer, format="JPEG", quality=70, optimize=True)

            buffer.seek(0)
            compressed_data = buffer.getvalue()
            compressed_b64 = base64.b64encode(compressed_data).decode("utf-8")

            if len(compressed_b64) <= max_size_bytes:
                logger.info(
                    f"Compressed to {len(compressed_data)} bytes with scale {scale_factor} and JPEG quality 70"
                )
                return compressed_b64, "image/jpeg"

            # Reduce scale factor and try again
            scale_factor -= 0.1

        # If we get here, we couldn't compress enough
        logger.warning("Could not compress image below required size with quality preservation")

        # Last resort: Use minimum quality and size
        buffer = io.BytesIO()
        smallest_img = img.resize((int(img.width * 0.5), int(img.height * 0.5)), Image.LANCZOS)
        # Convert to RGB if necessary
        if smallest_img.mode in ("RGBA", "LA") or (
            smallest_img.mode == "P" and "transparency" in smallest_img.info
        ):
            rgb_img = Image.new("RGB", smallest_img.size, (255, 255, 255))
            rgb_img.paste(
                smallest_img, mask=smallest_img.split()[3] if smallest_img.mode == "RGBA" else None
            )
            rgb_img.save(buffer, format="JPEG", quality=20, optimize=True)
        else:
            smallest_img.save(buffer, format="JPEG", quality=20, optimize=True)

        buffer.seek(0)
        final_data = buffer.getvalue()
        final_b64 = base64.b64encode(final_data).decode("utf-8")

        logger.warning(f"Final compressed size: {len(final_b64)} bytes (may still exceed limit)")
        return final_b64, "image/jpeg"

    except Exception as e:
        logger.error(f"Error compressing image: {str(e)}")
        raise
