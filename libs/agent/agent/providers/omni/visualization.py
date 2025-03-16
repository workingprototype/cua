"""Visualization utilities for the Cua provider."""

import base64
import logging
from io import BytesIO
from typing import Tuple
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def visualize_click(x: int, y: int, img_base64: str) -> Image.Image:
    """Visualize a click action by drawing on the screenshot.

    Args:
        x: X coordinate of the click
        y: Y coordinate of the click
        img_base64: Base64 encoded image to draw on

    Returns:
        PIL Image with visualization
    """
    try:
        # Decode the base64 image
        img_data = base64.b64decode(img_base64)
        img = Image.open(BytesIO(img_data))

        # Create a drawing context
        draw = ImageDraw.Draw(img)

        # Draw concentric circles at the click position
        small_radius = 10
        large_radius = 30

        # Draw filled inner circle
        draw.ellipse(
            [(x - small_radius, y - small_radius), (x + small_radius, y + small_radius)],
            fill="red",
        )

        # Draw outlined outer circle
        draw.ellipse(
            [(x - large_radius, y - large_radius), (x + large_radius, y + large_radius)],
            outline="red",
            width=3,
        )

        return img

    except Exception as e:
        logger.error(f"Error visualizing click: {str(e)}")
        # Return a blank image in case of error
        return Image.new("RGB", (800, 600), color="white")


def visualize_scroll(direction: str, clicks: int, img_base64: str) -> Image.Image:
    """Visualize a scroll action by drawing arrows on the screenshot.

    Args:
        direction: 'up' or 'down'
        clicks: Number of scroll clicks
        img_base64: Base64 encoded image to draw on

    Returns:
        PIL Image with visualization
    """
    try:
        # Decode the base64 image
        img_data = base64.b64decode(img_base64)
        img = Image.open(BytesIO(img_data))

        # Get image dimensions
        width, height = img.size

        # Create a drawing context
        draw = ImageDraw.Draw(img)

        # Determine arrow direction and positions
        center_x = width // 2
        arrow_width = 100

        if direction.lower() == "up":
            # Draw up arrow in the middle of the screen
            arrow_y = height // 2
            # Arrow points
            points = [
                (center_x, arrow_y - 50),  # Top point
                (center_x - arrow_width // 2, arrow_y + 50),  # Bottom left
                (center_x + arrow_width // 2, arrow_y + 50),  # Bottom right
            ]
            color = "blue"
        else:  # down
            # Draw down arrow in the middle of the screen
            arrow_y = height // 2
            # Arrow points
            points = [
                (center_x, arrow_y + 50),  # Bottom point
                (center_x - arrow_width // 2, arrow_y - 50),  # Top left
                (center_x + arrow_width // 2, arrow_y - 50),  # Top right
            ]
            color = "green"

        # Draw filled arrow
        draw.polygon(points, fill=color)

        # Add text showing number of clicks
        text_y = arrow_y + 70 if direction.lower() == "down" else arrow_y - 70
        draw.text((center_x - 40, text_y), f"{clicks} clicks", fill="black")

        return img

    except Exception as e:
        logger.error(f"Error visualizing scroll: {str(e)}")
        # Return a blank image in case of error
        return Image.new("RGB", (800, 600), color="white")


def calculate_element_center(box: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Calculate the center coordinates of a bounding box.

    Args:
        box: Tuple of (left, top, right, bottom) coordinates

    Returns:
        Tuple of (center_x, center_y) coordinates
    """
    left, top, right, bottom = box
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    return center_x, center_y
