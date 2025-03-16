"""Base type definitions."""

from enum import Enum, auto
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict


class Provider(str, Enum):
    """Available AI providers."""

    UNKNOWN = "unknown"  # Default provider for base class
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    OMNI = "omni"
    GROQ = "groq"


class HostConfig(BaseModel):
    """Host configuration."""

    model_config = ConfigDict(extra="forbid")
    hostname: str
    port: int

    @property
    def address(self) -> str:
        return f"{self.hostname}:{self.port}"


class TaskResult(BaseModel):
    """Result of a task execution."""

    model_config = ConfigDict(extra="forbid")
    result: str
    vnc_password: str


class Annotation(BaseModel):
    """Annotation metadata."""

    model_config = ConfigDict(extra="forbid")
    id: str
    vm_url: str


class AgentLoop(Enum):
    """Enumeration of available loop types."""

    ANTHROPIC = auto()  # Anthropic implementation
    OPENAI = auto()  # OpenAI implementation
    OMNI = auto()  # OmniLoop implementation
    # Add more loop types as needed
