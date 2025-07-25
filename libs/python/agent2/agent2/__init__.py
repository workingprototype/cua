"""
Agent2 - Decorator-based Computer Use Agent with liteLLM integration
"""

from .decorators import agent_loop
from .agent import ComputerAgent
from .types import Messages, AgentResponse

# Import loops to register them
from . import loops

__all__ = [
    "agent_loop",
    "ComputerAgent",
    "Messages",
    "AgentResponse"
]

__version__ = "0.1.0"
