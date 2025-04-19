"""UI-TARS Agent provider implementation."""

import logging
import asyncio
import base64
import re
import ast
import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple, Union

from openai import OpenAI

from computer import Computer
from ...core.base import BaseLoop
from ...core.types import AgentResponse, LLMProvider
from ...core.messages import StandardMessageManager, ImageRetentionConfig
from .prompts import COMPUTER_USE

logger = logging.getLogger(__name__)


class UITARSLoop(BaseLoop):
    """UI-TARS implementation of the agent loop.

    This class extends BaseLoop to provide specialized support for UI-TARS models
    with computer control capabilities.
    """

    def __init__(
        self,
        api_key: str,
        computer: Computer,
        model: str = "ui-tars",
        only_n_most_recent_images: Optional[int] = 2,
        base_dir: Optional[str] = "trajectories",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        save_trajectory: bool = True,
        provider_base_url: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the UI-TARS loop.

        Args:
            api_key: API key (may be empty for local deployments)
            model: Model name (if using non-default UI-TARS model)
            computer: Computer instance
            only_n_most_recent_images: Maximum number of recent screenshots to include in API requests
            base_dir: Base directory for saving experiment data
            max_retries: Maximum number of retries for API calls
            retry_delay: Delay between retries in seconds
            save_trajectory: Whether to save trajectory data
            provider_base_url: Custom endpoint URL for the model
            **kwargs: Additional provider-specific arguments
        """
        # Initialize base class with core config
        super().__init__(
            computer=computer,
            model=model,
            api_key=api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            base_dir=base_dir,
            save_trajectory=save_trajectory,
            only_n_most_recent_images=only_n_most_recent_images,
            **kwargs,
        )

        # Initialize message manager
        self.message_manager = StandardMessageManager(
            config=ImageRetentionConfig(num_images_to_keep=only_n_most_recent_images)
        )

        # UI-TARS specific attributes
        self.provider = LLMProvider.OAICOMPAT
        self.client = None
        self.api_base_url = provider_base_url or "http://localhost:1234/v1"
        
        # Runtime configuration
        self.temperature = kwargs.get("temperature", 0.0)
        self.top_k = kwargs.get("top_k", -1)
        self.top_p = kwargs.get("top_p", 0.9)
        self.max_tokens = kwargs.get("max_tokens", 500)
        self.language = kwargs.get("language", "English")
        
        # For tracking state
        self.thoughts = []
        self.actions = []
        self.observations = []
        self.history_images = []
        self.history_responses = []

    async def initialize_client(self) -> None:
        """Initialize the OpenAI API client for UI-TARS.

        Implements abstract method from BaseLoop.
        """
        try:
            # Initialize OpenAI client with the custom base URL
            self.client = OpenAI(
                base_url=self.api_base_url,
                api_key=self.api_key or "empty",  # Some servers require non-empty API key
            )
            
            # Try to list models but don't fail if it's not supported
            try:
                models = self.client.models.list()
                logger.info(f"UI-TARS client initialized. Connected to API at {self.api_base_url}")
            except Exception as e:
                # Some custom endpoints may not support listing models
                logger.warning(f"Could not list models, but continuing: {str(e)}")
                logger.info(f"UI-TARS client initialized with API at {self.api_base_url}")
                
        except Exception as e:
            logger.error(f"Error initializing UI-TARS client: {str(e)}")
            self.client = None
            raise RuntimeError(f"Failed to initialize UI-TARS client: {str(e)}")

    async def run(self, instruction: str) -> AsyncGenerator[AgentResponse, None]:
        """Run the agent loop with provided instruction.

        Args:
            instruction: User instruction for the agent

        Yields:
            Agent responses in a standardized format
        """
        try:
            logger.info("Starting UI-TARS loop run")

            # Create queue for response streaming
            queue = asyncio.Queue()

            # Start loop in background task
            loop_task = asyncio.create_task(self._run_loop(queue, instruction))

            # Process and yield messages as they arrive
            while True:
                try:
                    item = await queue.get()
                    if item is None:  # Stop signal
                        break
                    yield item
                    queue.task_done()
                except Exception as e:
                    logger.error(f"Error processing queue item: {str(e)}")
                    continue

            # Wait for loop to complete
            await loop_task

            # Send completion message
            yield {
                "role": "assistant",
                "content": "Task completed successfully.",
                "metadata": {"title": "✅ Complete"},
            }

        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            yield {
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "metadata": {"title": "❌ Error"},
            }

    async def _run_loop(self, queue: asyncio.Queue, instruction: str) -> None:
        """Run the main agent loop with the given instruction.

        Args:
            queue: Queue for streaming responses
            instruction: User instruction
        """
        try:
            screen_size = await self.computer.interface.get_screen_size()
            
            # Reset history for each run
            self.thoughts = []
            self.actions = []
            self.observations = []
            self.history_images = []
            self.history_responses = []
            
            # Capture initial screenshot
            try:
                # Take screenshot
                screenshot = await self.computer.interface.screenshot()
                logger.info("Screenshot captured successfully")

                # Convert to base64
                if isinstance(screenshot, bytes):
                    screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")
                else:
                    screenshot_base64 = str(screenshot)

                # Emit screenshot callbacks
                await self.handle_screenshot(screenshot_base64, action_type="initial_state")

                # Save screenshot if requested
                if self.save_trajectory:
                    self._save_screenshot(screenshot_base64, action_type="state")
                    logger.info("Screenshot saved to trajectory")
                
                # Add to history
                self.history_images.append(screenshot)
                
                # Create turn directory
                if self.save_trajectory:
                    self._create_turn_dir()
                
                # Process first screenshot response
                response, action_list = await self._get_ui_tars_response(instruction)
                
                # Add to history
                self.history_responses.append(response)
                self.thoughts.append(response)
                
                # Process response
                await self._process_response(response, action_list, queue)
                
                # Continue running until task is complete
                task_complete = False
                while not task_complete:
                    # Check if the last action was a "finished" or "DONE" action
                    if any(action == "DONE" for action in action_list):
                        logger.info("Task completed. Received DONE action.")
                        task_complete = True
                        continue
                        
                    # Execute the next actions
                    await self._execute_actions(action_list, queue)
                    
                    # Take a screenshot after the action
                    screenshot = await self.computer.interface.screenshot()
                    if isinstance(screenshot, bytes):
                        screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")
                    else:
                        screenshot_base64 = str(screenshot)
                    
                    # Emit screenshot callbacks
                    action_type = "after_action"
                    await self.handle_screenshot(screenshot_base64, action_type=action_type)
                    
                    # Save screenshot if requested
                    if self.save_trajectory:
                        self._save_screenshot(screenshot_base64, action_type=action_type)
                    
                    # Add to history
                    self.history_images.append(screenshot)
                    
                    # Create a new turn directory
                    if self.save_trajectory:
                        self._create_turn_dir()
                    
                    # Get next action from UI-TARS
                    response, action_list = await self._get_ui_tars_response(instruction)
                    
                    # Add to history
                    self.history_responses.append(response)
                    self.thoughts.append(response)
                    
                    # Process response
                    await self._process_response(response, action_list, queue)
                    
                    # Check for limits (to prevent infinite loops)
                    if len(self.history_responses) >= 50:  # Max 50 turns
                        logger.warning("Reached maximum number of turns (50). Stopping.")
                        task_complete = True
                    
            except Exception as e:
                logger.error(f"Error in screenshot capture: {str(e)}")
                await queue.put({
                    "role": "assistant",
                    "content": f"Error capturing screenshot: {str(e)}",
                    "metadata": {"title": "❌ Error"},
                })
                
            # Signal completion
            await queue.put(None)
                
        except Exception as e:
            logger.error(f"Error in _run_loop: {str(e)}")
            await queue.put({
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "metadata": {"title": "❌ Error"},
            })
            await queue.put(None)  # Signal completion

    async def _get_ui_tars_response(self, instruction: str) -> Tuple[str, List[str]]:
        """Get a response from the UI-TARS model.
        
        Args:
            instruction: User instruction
            
        Returns:
            Tuple of (raw_response, parsed_actions)
        """
        # Prepare the prompt with the user instruction
        user_prompt = COMPUTER_USE.format(
            instruction=instruction,
            language=self.language
        )
        
        # Prepare messages for the API call
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}]
            },
            {
                "role": "user", 
                "content": [{"type": "text", "text": user_prompt}]
            }
        ]
        
        # Add images to the conversation history
        images_to_use = self.history_images[-self.only_n_most_recent_images:] if self.only_n_most_recent_images else self.history_images
        
        # Add previous conversation turns if available
        if len(self.history_responses) > 0:
            for i, (img, resp) in enumerate(zip(images_to_use, self.history_responses[-len(images_to_use):])):
                # Convert image to base64 if needed
                if isinstance(img, bytes):
                    img_base64 = base64.b64encode(img).decode("utf-8")
                else:
                    img_base64 = img
                
                # Add the image message
                messages.append({
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}]
                })
                
                # Add the assistant's response
                messages.append({
                    "role": "assistant",
                    "content": self._add_box_token(resp)
                })
        
        # Add the latest image
        latest_image = self.history_images[-1]
        if isinstance(latest_image, bytes):
            img_base64 = base64.b64encode(latest_image).decode("utf-8")
        else:
            img_base64 = latest_image
            
        messages.append({
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}]
        })
        
        # Log the API call
        if self.save_trajectory:
            self._log_api_call("request", {"messages": messages})
        
        # Make the API call
        try:
            logger.info("Sending request to UI-TARS model")
            response = self.client.chat.completions.create( # type: ignore
                model=self.model,
                messages=messages,
                frequency_penalty=1,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p
            )
            
            # Extract the response content
            raw_response = response.choices[0].message.content.strip()
            
            # Log the API response
            if self.save_trajectory:
                self._log_api_call("response", {"messages": messages}, {"completion": raw_response})
            
            # Parse the actions from the response
            actions = self._parse_actions(raw_response)
            
            return raw_response, actions
            
        except Exception as e:
            logger.error(f"Error calling UI-TARS API: {str(e)}")
            if self.save_trajectory:
                self._log_api_call("error", {"messages": messages}, error=e)
            return str(e), ["DONE"]  # Return DONE to terminate the loop on error

    def _parse_actions(self, response: str) -> List[str]:
        """Parse actions from the UI-TARS response.
        
        Args:
            response: Raw model response text
            
        Returns:
            List of actions to execute
        """
        try:
            # Extract the action part from the response
            action_part = response.split("Action:", 1)[1].strip() if "Action:" in response else ""
            
            if not action_part:
                logger.warning("No action found in response")
                return ["DONE"]
                
            # Check for special actions
            if "finished" in action_part.lower():
                return ["DONE"]
            if "wait()" in action_part:
                return ["WAIT"]
                
            # Extract the action and parameters
            actions = []
            
            # Simplest approach: just identify the action type and prep for computer interface
            if "click" in action_part:
                # Extract coordinates from the start_box parameter
                box_match = re.search(r"start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'", action_part)
                if box_match:
                    x, y = box_match.groups()
                    actions.append(f"left_click({x},{y})")
            elif "left_double" in action_part:
                box_match = re.search(r"start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'", action_part)
                if box_match:
                    x, y = box_match.groups()
                    actions.append(f"double_click({x},{y})")
            elif "right_single" in action_part:
                box_match = re.search(r"start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'", action_part)
                if box_match:
                    x, y = box_match.groups()
                    actions.append(f"right_click({x},{y})")
            elif "drag" in action_part:
                start_box = re.search(r"start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'", action_part)
                end_box = re.search(r"end_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'", action_part)
                if start_box and end_box:
                    start_x, start_y = start_box.groups()
                    end_x, end_y = end_box.groups()
                    actions.append(f"drag({start_x},{start_y},{end_x},{end_y})")
            elif "hotkey" in action_part:
                key_match = re.search(r"key='([^']+)'", action_part)
                if key_match:
                    key = key_match.group(1)
                    actions.append(f"hotkey({key})")
            elif "type" in action_part:
                content_match = re.search(r"content='([^']*)'", action_part)
                if content_match:
                    content = content_match.group(1)
                    actions.append(f"type({content})")
            elif "scroll" in action_part:
                box_match = re.search(r"start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'", action_part)
                direction_match = re.search(r"direction='([^']+)'", action_part)
                if box_match and direction_match:
                    x, y = box_match.groups()
                    direction = direction_match.group(1)
                    actions.append(f"scroll({x},{y},{direction})")
            
            # If no actions were extracted, add a DONE action to terminate the loop
            if not actions:
                return ["DONE"]
                
            return actions
            
        except Exception as e:
            logger.error(f"Error parsing actions: {str(e)}")
            return ["DONE"]  # Return DONE to terminate the loop on error

    async def _execute_actions(self, actions: List[str], queue: asyncio.Queue) -> None:
        """Execute the given actions using the computer interface.
        
        Args:
            actions: List of actions to execute
            queue: Queue for response streaming
        """
        for action in actions:
            try:
                # Skip special actions
                if action == "DONE" or action == "WAIT":
                    continue
                    
                # Parse the action string
                if action.startswith("left_click"):
                    # Extract coordinates
                    coords = re.search(r"left_click\((\d+),(\d+)\)", action)
                    if coords:
                        x, y = int(coords.group(1)), int(coords.group(2))
                        await self.computer.interface.left_click(x, y)
                        await queue.put({
                            "role": "assistant",
                            "content": f"Clicked at position ({x}, {y})",
                            "metadata": {"title": "🖱️ Click"},
                        })
                
                elif action.startswith("double_click"):
                    # Extract coordinates
                    coords = re.search(r"double_click\((\d+),(\d+)\)", action)
                    if coords:
                        x, y = int(coords.group(1)), int(coords.group(2))
                        await self.computer.interface.double_click(x, y)
                        await queue.put({
                            "role": "assistant",
                            "content": f"Double-clicked at position ({x}, {y})",
                            "metadata": {"title": "🖱️ Double Click"},
                        })
                
                elif action.startswith("right_click"):
                    # Extract coordinates
                    coords = re.search(r"right_click\((\d+),(\d+)\)", action)
                    if coords:
                        x, y = int(coords.group(1)), int(coords.group(2))
                        await self.computer.interface.right_click(x, y)
                        await queue.put({
                            "role": "assistant",
                            "content": f"Right-clicked at position ({x}, {y})",
                            "metadata": {"title": "🖱️ Right Click"},
                        })
                
                elif action.startswith("drag"):
                    # Extract coordinates
                    coords = re.search(r"drag\((\d+),(\d+),(\d+),(\d+)\)", action)
                    if coords:
                        start_x, start_y, end_x, end_y = map(int, coords.groups())
                        await self.computer.interface.move_cursor(start_x, start_y)
                        await self.computer.interface.drag_to(end_x, end_y)
                        await queue.put({
                            "role": "assistant",
                            "content": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})",
                            "metadata": {"title": "🖱️ Drag"},
                        })
                
                elif action.startswith("hotkey"):
                    # Extract key
                    key_match = re.search(r"hotkey\(([^)]+)\)", action)
                    if key_match:
                        keys = key_match.group(1).split(",")
                        # Clean up keys
                        clean_keys = [k.strip() for k in keys]
                        for key in clean_keys:
                            await self.computer.interface.press_key(key)
                        await queue.put({
                            "role": "assistant",
                            "content": f"Pressed hotkey: {', '.join(clean_keys)}",
                            "metadata": {"title": "⌨️ Hotkey"},
                        })
                
                elif action.startswith("type"):
                    # Extract content
                    content_match = re.search(r"type\(([^)]*)\)", action)
                    if content_match:
                        content = content_match.group(1)
                        await self.computer.interface.type_text(content)
                        await queue.put({
                            "role": "assistant",
                            "content": f"Typed: {content}",
                            "metadata": {"title": "⌨️ Type"},
                        })
                
                elif action.startswith("scroll"):
                    # Extract parameters
                    params = re.search(r"scroll\((\d+),(\d+),([^)]+)\)", action)
                    if params:
                        x, y, direction = params.groups()
                        x, y = int(x), int(y)
                        direction = direction.strip("'\"")
                        
                        # Move cursor to position
                        await self.computer.interface.move_cursor(x, y)
                        
                        # Scroll based on direction
                        if direction == "down":
                            await self.computer.interface.scroll_down(5)
                        elif direction == "up":
                            await self.computer.interface.scroll_up(5)
                            
                        await queue.put({
                            "role": "assistant",
                            "content": f"Scrolled {direction} at position ({x}, {y})",
                            "metadata": {"title": "🖱️ Scroll"},
                        })
                
                # Wait a bit after each action
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error executing action {action}: {str(e)}")
                await queue.put({
                    "role": "assistant",
                    "content": f"Error executing action {action}: {str(e)}",
                    "metadata": {"title": "❌ Error"},
                })

    async def _process_response(self, response: str, actions: List[str], queue: asyncio.Queue) -> None:
        """Process the model response and send to queue.
        
        Args:
            response: Raw model response
            actions: Parsed actions
            queue: Queue for streaming responses
        """
        try:
            # Extract thought from response
            thought = ""
            if "Thought:" in response:
                thought_match = re.search(r"Thought: (.*?)(?=\s*Action:|$)", response, re.DOTALL)
                if thought_match:
                    thought = thought_match.group(1).strip()
            
            # Send thought to queue
            if thought:
                await queue.put({
                    "role": "assistant",
                    "content": thought,
                    "metadata": {"title": "🧠 Thinking"},
                })
            
            # Send the actions to queue
            action_summary = "Actions: " + ", ".join(actions)
            await queue.put({
                "role": "assistant",
                "content": action_summary,
                "metadata": {"title": "🛠️ Action Plan"},
            })
            
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            await queue.put({
                "role": "assistant",
                "content": f"Error processing response: {str(e)}",
                "metadata": {"title": "❌ Error"},
            })

    def _add_box_token(self, input_string):
        """Add box tokens to the coordinates in the model response.
        
        Args:
            input_string: Raw model response
            
        Returns:
            String with box tokens added
        """
        if "Action: " not in input_string or "start_box=" not in input_string:
            return input_string
            
        suffix = input_string.split("Action: ")[0] + "Action: "
        actions = input_string.split("Action: ")[1:]
        processed_actions = []
        
        for action in actions:
            action = action.strip()
            coordinates = re.findall(r"(start_box|end_box)='\((\d+),\s*(\d+)\)'", action)
            
            updated_action = action
            for coord_type, x, y in coordinates:
                updated_action = updated_action.replace(
                    f"{coord_type}='({x},{y})'", 
                    f"{coord_type}='<|box_start|>({x},{y})<|box_end|>'"
                )
            processed_actions.append(updated_action)
        
        return suffix + "\n\n".join(processed_actions)
