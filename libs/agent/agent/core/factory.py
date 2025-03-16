"""Factory for creating provider-specific agents."""

from typing import Optional, Dict, Any, List

from computer import Computer
from ..types.base import Provider
from .base_agent import BaseComputerAgent

# Import provider-specific implementations
_ANTHROPIC_AVAILABLE = False
_OPENAI_AVAILABLE = False
_OLLAMA_AVAILABLE = False
_OMNI_AVAILABLE = False

# Try importing providers
try:
    import anthropic
    from ..providers.anthropic.agent import AnthropicComputerAgent

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

try:
    import openai

    _OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    from ..providers.omni.agent import OmniComputerAgent

    _OMNI_AVAILABLE = True
except ImportError:
    pass


class AgentFactory:
    """Factory for creating provider-specific agent implementations."""

    @staticmethod
    def create(
        provider: Provider, computer: Optional[Computer] = None, **kwargs: Any
    ) -> BaseComputerAgent:
        """Create an agent based on the specified provider.

        Args:
            provider: The AI provider to use
            computer: Optional Computer instance
            **kwargs: Additional provider-specific arguments

        Returns:
            A provider-specific agent implementation

        Raises:
            ImportError: If provider dependencies are not installed
            ValueError: If provider is not supported
        """
        # Create a Computer instance if none is provided
        if computer is None:
            computer = Computer()

        if provider == Provider.ANTHROPIC:
            if not _ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "Anthropic provider requires additional dependencies. "
                    "Install them with: pip install cua-agent[anthropic]"
                )
            return AnthropicComputerAgent(max_retries=3, computer=computer, **kwargs)
        elif provider == Provider.OPENAI:
            if not _OPENAI_AVAILABLE:
                raise ImportError(
                    "OpenAI provider requires additional dependencies. "
                    "Install them with: pip install cua-agent[openai]"
                )
            raise NotImplementedError("OpenAI provider not yet implemented")
        elif provider == Provider.OLLAMA:
            if not _OLLAMA_AVAILABLE:
                raise ImportError(
                    "Ollama provider requires additional dependencies. "
                    "Install them with: pip install cua-agent[ollama]"
                )
            # Only import ollama when actually creating an Ollama agent
            try:
                import ollama
                from ..providers.ollama.agent import OllamaComputerAgent

                return OllamaComputerAgent(max_retries=3, computer=computer, **kwargs)
            except ImportError:
                raise ImportError(
                    "Failed to import ollama package. " "Install it with: pip install ollama"
                )
        elif provider == Provider.OMNI:
            if not _OMNI_AVAILABLE:
                raise ImportError(
                    "Omni provider requires additional dependencies. "
                    "Install them with: pip install cua-agent[omni]"
                )
            return OmniComputerAgent(max_retries=3, computer=computer, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
