"""Provider-specific configurations and constants."""

from ..providers.omni.types import LLMProvider

# Default models for different providers
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.ANTHROPIC: "claude-3-7-sonnet-20250219",
    LLMProvider.OLLAMA: "qwen2.5:7b",
}

# Map providers to their environment variable names
ENV_VARS = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.OLLAMA: "OLLAMA_API_KEY",
}
