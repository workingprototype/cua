"""Type definitions for the agent package."""

from .base import HostConfig, TaskResult, Annotation
from .messages import Message, Request, Response, StepMessage, DisengageMessage
from .tools import ToolInvocation, ToolInvocationState, ClientAttachment, ToolResult

__all__ = [
    # Base types
    "HostConfig",
    "TaskResult",
    "Annotation",
    # Message types
    "Message",
    "Request",
    "Response",
    "StepMessage",
    "DisengageMessage",
    # Tool types
    "ToolInvocation",
    "ToolInvocationState",
    "ClientAttachment",
    "ToolResult",
]
