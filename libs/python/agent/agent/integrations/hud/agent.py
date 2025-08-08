"""HUD ComputerAgent wrapper for OSWorld benchmarking."""

import logging
from typing import Any, Literal, Optional, Union, List, Dict
import asyncio

from agent import ComputerAgent as BaseComputerAgent
from hud.adapters import Adapter
from hud.agent.base import Agent
from hud.utils.common import Observation
from hud.adapters.common.types import LogType
from hud.types import Gym

from .adapter import ComputerAgentAdapter
from .computer_handler import HUDComputerHandler

logger = logging.getLogger(__name__)


class ComputerAgent(Agent[BaseComputerAgent, dict[str, Any]]):
    """
    A ComputerAgent wrapper for HUD integration.
    
    This agent wraps the base ComputerAgent to work with HUD environments,
    providing the same interface as OperatorAgent but using ComputerAgent internally.
    """
    
    transfer_gyms: dict[Gym, Gym] = {"qa": "hud-browser"}

    def __init__(
        self,
        model: str = "anthropic/claude-3-5-sonnet-20241022",
        environment: Literal["windows", "mac", "linux", "browser"] = "browser",
        adapter: Optional[Adapter] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize the ComputerAgent for HUD.

        Args:
            model: The model string for ComputerAgent (e.g., "anthropic/claude-3-5-sonnet-20241022")
            environment: The environment type (windows, mac, linux, browser)
            adapter: The adapter to use for preprocessing and postprocessing
            name: The name of the agent
            **kwargs: Additional arguments passed to ComputerAgent
        """
        # Create adapter if not provided
        adapter = adapter or ComputerAgentAdapter()
        
        if name is None:
            name = f"computeragent-{model.split('/')[-1]}"

        # Initialize the base Agent class without client (we'll create it later)
        super().__init__(client=None, adapter=adapter, name=name)

        self.model = model
        self.environment = environment
        self.kwargs = kwargs

        # Default dimensions
        self.width = 1024
        self.height = 768

        # Update dimensions if adapter is provided
        if self.adapter:
            self.width = self.adapter.agent_width
            self.height = self.adapter.agent_height

        # Create HUD computer handler
        self.hud_computer = HUDComputerHandler(
            environment=environment,
            dimensions=(self.width, self.height)
        )

        # Initialize ComputerAgent with HUD computer handler
        self.computer_agent = BaseComputerAgent(
            model=model,
            tools=[self.hud_computer],
            **kwargs
        )
        
        # Set the client to the computer_agent for compatibility
        self.client = self.computer_agent

        # State tracking
        self.conversation_history: List[Dict[str, Any]] = []
        self.initial_prompt: Optional[str] = None

        # System prompt for computer use tasks
        self.base_system_prompt = """
        You are an autonomous computer-using agent. Follow these guidelines:

        1. Be decisive and complete tasks without asking for confirmation unless absolutely necessary.
        2. If you need user confirmation for safety-critical actions, use the formal safety check mechanism.
        3. Do NOT ask questions like "Should I proceed?" or "Would you like me to continue?" - just proceed with the task.
        4. When you find what you're looking for (e.g., a file to upload), proceed with the action directly.
        5. Only stop when the task is fully complete or if you encounter an error that prevents completion.
        6. Trust that the user wants you to complete the entire task they've requested.

        Remember: You have been given permission to complete the requested task autonomously.
        """

    async def fetch_response(self, observation: Observation) -> tuple[list[dict[str, Any]], bool]:
        """
        Fetch a response from ComputerAgent based on the observation.

        Args:
            observation: The preprocessed observation

        Returns:
            tuple[list[dict[str, Any]], bool, list[LogType] | None]: A tuple containing the list of raw actions,
                                             boolean indicating if the agent believes the task is complete.
        """
        try:
            # Update the computer handler with the current screenshot
            if observation.screenshot:
                self.hud_computer.update_screenshot(observation.screenshot)

            # Set up action callback to capture actions
            captured_actions = []
            action_done = False

            async def action_callback(action: Dict[str, Any]) -> None:
                """Callback to capture actions from ComputerAgent."""
                nonlocal captured_actions, action_done
                captured_actions.append(action)

            # Set the action callback
            self.hud_computer.set_action_callback(action_callback)

            # Prepare the message for ComputerAgent
            if not self.conversation_history:
                # First interaction - use the observation text as initial prompt
                if observation.text:
                    self.initial_prompt = observation.text
                    message = f"{self.base_system_prompt}\n\nTask: {observation.text}"
                else:
                    message = f"{self.base_system_prompt}\n\nPlease analyze the current screen and determine what action to take."
                
                self.conversation_history.append({"role": "user", "content": message})
            else:
                # Subsequent interactions - add context about the current state
                message = "Continue with the task based on the current screen state."
                self.conversation_history.append({"role": "user", "content": message})

            # Run ComputerAgent
            try:
                # ComputerAgent.run returns an async generator
                async for result in self.computer_agent.run(self.conversation_history, stream=False):
                    # Update conversation history with the output
                    self.conversation_history += result["output"]
                
                # Check if we captured any actions
                if captured_actions:
                    # Extract reasoning from the conversation history
                    reasoning = ""
                    # Look for the latest reasoning message
                    for msg in reversed(self.conversation_history):
                        if msg.get("type") == "reasoning" and msg.get("summary"):
                            reasoning = " ".join([s.get("text", "") for s in msg["summary"] if s.get("type") == "summary_text"])
                            break
                        elif msg.get("type") == "message" and msg.get("role") == "assistant":
                            content = msg.get("content", [])
                            if isinstance(content, list):
                                reasoning = " ".join([c.get("text", "") for c in content if c.get("type") == "output_text"])
                            break
                    
                    # Add reasoning and logs to each action
                    for action in captured_actions:
                        action["reasoning"] = reasoning
                        action["logs"] = {"conversation_length": len(self.conversation_history)}
                    
                    # Check if task is done by looking for assistant message indicating completion
                    done = False
                    for msg in reversed(self.conversation_history):
                        if msg.get("type") == "message" and msg.get("role") == "assistant":
                            content = msg.get("content", [])
                            for c in content:
                                if c.get("type") == "output_text" and "task completed" in c.get("text", "").lower():
                                    done = True
                                    break
                            break
                    
                    return captured_actions, done
                else:
                    # No actions captured, task is likely complete
                    response_text = "Task completed."
                    for msg in reversed(self.conversation_history):
                        if msg.get("type") == "message" and msg.get("role") == "assistant":
                            content = msg.get("content", [])
                            for c in content:
                                if c.get("type") == "output_text":
                                    response_text = c.get("text", response_text)
                                    break
                            break
                    
                    response_action = {
                        "type": "response",
                        "text": response_text,
                        "reasoning": response_text,
                        "logs": {"conversation_length": len(self.conversation_history)}
                    }
                    
                    # Check if this indicates task completion or failure
                    done = True
                    if "task is infeasible" in response_text.lower():
                        response_action = {"type": "custom", "action": "FAIL"}
                    
                    return [response_action], done

            except Exception as e:
                logger.error(f"Error running ComputerAgent: {e}")
                # Return an error response
                error_action = {
                    "type": "response", 
                    "text": f"Error occurred: {str(e)}",
                    "reasoning": f"ComputerAgent encountered an error: {str(e)}",
                    "logs": {"error": str(e)}
                }
                return [error_action], True

        except Exception as e:
            logger.error(f"Error in fetch_response: {e}")
            error_action = {
                "type": "response",
                "text": f"Error in agent processing: {str(e)}",
                "reasoning": f"Agent processing error: {str(e)}",
                "logs": {"error": str(e)}
            }
            return [error_action], True
