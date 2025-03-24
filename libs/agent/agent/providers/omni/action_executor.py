"""Action execution for the Omni agent."""

import logging
from typing import Dict, Any, Tuple
import json

from .parser import ParseResult

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes UI actions based on model instructions."""

    def __init__(self, loop):
        """Initialize the action executor.

        Args:
            loop: Reference to the parent loop instance that provides context
        """
        self.loop = loop

    async def execute_action(self, content: Dict[str, Any], parsed_screen: ParseResult) -> bool:
        """Execute the action specified in the content.

        Args:
            content: Dictionary containing the action details
            parsed_screen: Current parsed screen information

        Returns:
            Whether an action-specific screenshot was saved
        """
        try:
            action = content.get("Action", "").lower()
            if not action:
                return False

            # Track if we saved an action-specific screenshot
            action_screenshot_saved = False

            try:
                # Prepare kwargs based on action type
                kwargs = {}

                if action in ["left_click", "right_click", "double_click", "move_cursor"]:
                    try:
                        box_id = int(content["Box ID"])
                        logger.info(f"Processing Box ID: {box_id}")

                        # Calculate click coordinates using parser
                        x, y = await self.loop.parser.calculate_click_coordinates(
                            box_id, parsed_screen
                        )
                        logger.info(f"Calculated coordinates: x={x}, y={y}")

                        kwargs["x"] = x
                        kwargs["y"] = y

                        # Visualize action if screenshot is available
                        if parsed_screen.annotated_image_base64:
                            img_data = parsed_screen.annotated_image_base64
                            # Remove data URL prefix if present
                            if img_data.startswith("data:image"):
                                img_data = img_data.split(",")[1]
                            # Only save visualization for coordinate-based actions
                            self.loop.viz_helper.visualize_action(x, y, img_data)
                            action_screenshot_saved = True

                    except ValueError as e:
                        logger.error(f"Error processing Box ID: {str(e)}")
                        return False

                elif action == "drag_to":
                    try:
                        box_id = int(content["Box ID"])
                        x, y = await self.loop.parser.calculate_click_coordinates(
                            box_id, parsed_screen
                        )
                        kwargs.update(
                            {
                                "x": x,
                                "y": y,
                                "button": content.get("button", "left"),
                                "duration": float(content.get("duration", 0.5)),
                            }
                        )

                        # Visualize drag destination if screenshot is available
                        if parsed_screen.annotated_image_base64:
                            img_data = parsed_screen.annotated_image_base64
                            # Remove data URL prefix if present
                            if img_data.startswith("data:image"):
                                img_data = img_data.split(",")[1]
                            # Only save visualization for coordinate-based actions
                            self.loop.viz_helper.visualize_action(x, y, img_data)
                            action_screenshot_saved = True

                    except ValueError as e:
                        logger.error(f"Error processing drag coordinates: {str(e)}")
                        return False

                elif action == "type_text":
                    kwargs["text"] = content["Value"]
                    # For type_text, store the value in the action type
                    action_type = f"type_{content['Value'][:20]}"  # Truncate if too long
                elif action == "press_key":
                    kwargs["key"] = content["Value"]
                    action_type = f"press_{content['Value']}"
                elif action == "hotkey":
                    if isinstance(content.get("Value"), list):
                        keys = content["Value"]
                        action_type = f"hotkey_{'_'.join(keys)}"
                    else:
                        # Simply split string format like "command+space" into a list
                        keys = [k.strip() for k in content["Value"].lower().split("+")]
                        action_type = f"hotkey_{content['Value'].replace('+', '_')}"
                    logger.info(f"Preparing hotkey with keys: {keys}")
                    # Get the method but call it with *args instead of **kwargs
                    method = getattr(self.loop.computer.interface, action)
                    await method(*keys)  # Unpack the keys list as positional arguments
                    logger.info(f"Tool execution completed successfully: {action}")

                    # For hotkeys, take a screenshot after the action
                    try:
                        # Get a new screenshot after the action and save it with the action type
                        new_parsed_screen = await self.loop._get_parsed_screen_som(
                            save_screenshot=False
                        )
                        if new_parsed_screen and new_parsed_screen.annotated_image_base64:
                            img_data = new_parsed_screen.annotated_image_base64
                            # Remove data URL prefix if present
                            if img_data.startswith("data:image"):
                                img_data = img_data.split(",")[1]
                            # Save with action type to indicate this is a post-action screenshot
                            self.loop._save_screenshot(img_data, action_type=action_type)
                            action_screenshot_saved = True
                    except Exception as screenshot_error:
                        logger.error(
                            f"Error taking post-hotkey screenshot: {str(screenshot_error)}"
                        )

                    return action_screenshot_saved

                elif action in ["scroll_down", "scroll_up"]:
                    clicks = int(content.get("amount", 1))
                    kwargs["clicks"] = clicks
                    action_type = f"scroll_{action.split('_')[1]}_{clicks}"

                    # Visualize scrolling if screenshot is available
                    if parsed_screen.annotated_image_base64:
                        img_data = parsed_screen.annotated_image_base64
                        # Remove data URL prefix if present
                        if img_data.startswith("data:image"):
                            img_data = img_data.split(",")[1]
                        direction = "down" if action == "scroll_down" else "up"
                        # For scrolling, we only save the visualization to avoid duplicate images
                        self.loop.viz_helper.visualize_scroll(direction, clicks, img_data)
                        action_screenshot_saved = True

                else:
                    logger.warning(f"Unknown action: {action}")
                    return False

                # Execute tool and handle result
                try:
                    method = getattr(self.loop.computer.interface, action)
                    logger.info(f"Found method for action '{action}': {method}")
                    await method(**kwargs)
                    logger.info(f"Tool execution completed successfully: {action}")

                    # For non-coordinate based actions that don't already have visualizations,
                    # take a new screenshot after the action
                    if not action_screenshot_saved:
                        # Take a new screenshot
                        try:
                            # Get a new screenshot after the action and save it with the action type
                            new_parsed_screen = await self.loop._get_parsed_screen_som(
                                save_screenshot=False
                            )
                            if new_parsed_screen and new_parsed_screen.annotated_image_base64:
                                img_data = new_parsed_screen.annotated_image_base64
                                # Remove data URL prefix if present
                                if img_data.startswith("data:image"):
                                    img_data = img_data.split(",")[1]
                                # Save with action type to indicate this is a post-action screenshot
                                if "action_type" in locals():
                                    self.loop._save_screenshot(img_data, action_type=action_type)
                                else:
                                    self.loop._save_screenshot(img_data, action_type=action)
                                # Update the action screenshot flag for this turn
                                action_screenshot_saved = True
                        except Exception as screenshot_error:
                            logger.error(
                                f"Error taking post-action screenshot: {str(screenshot_error)}"
                            )

                except AttributeError as e:
                    logger.error(f"Method not found for action '{action}': {str(e)}")
                    return False
                except Exception as tool_error:
                    logger.error(f"Tool execution failed: {str(tool_error)}")
                    return False

                return action_screenshot_saved

            except Exception as e:
                logger.error(f"Error executing action {action}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error in execute_action: {str(e)}")
            return False
