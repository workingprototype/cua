"""Message-related type definitions."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

from .tools import ToolInvocation

class Message(BaseModel):
    """Base message type."""
    model_config = ConfigDict(extra='forbid')
    role: str
    content: str
    annotations: Optional[List[Dict[str, Any]]] = None
    toolInvocations: Optional[List[ToolInvocation]] = None
    data: Optional[List[Dict[str, Any]]] = None
    errors: Optional[List[str]] = None

class Request(BaseModel):
    """Request type."""
    model_config = ConfigDict(extra='forbid')
    messages: List[Message]
    selectedModel: str

class Response(BaseModel):
    """Response type."""
    model_config = ConfigDict(extra='forbid')
    messages: List[Message]
    vm_url: str

class StepMessage(Message):
    """Message for a single step."""
    pass

class DisengageMessage(BaseModel):
    """Message indicating disengagement."""
    pass
