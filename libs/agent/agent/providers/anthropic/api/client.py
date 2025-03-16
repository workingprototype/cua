from typing import Any
import httpx
import asyncio
from anthropic import Anthropic, AnthropicBedrock, AnthropicVertex
from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaToolUnionParam
from ..types import LLMProvider
from .logging import log_api_interaction
import random
import logging

logger = logging.getLogger(__name__)


class APIConnectionError(Exception):
    """Error raised when there are connection issues with the API."""

    pass


class BaseAnthropicClient:
    """Base class for Anthropic API clients."""

    MAX_RETRIES = 10
    INITIAL_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 60.0
    JITTER_FACTOR = 0.1

    async def create_message(
        self,
        *,
        messages: list[BetaMessageParam],
        system: list[Any],
        tools: list[BetaToolUnionParam],
        max_tokens: int,
        betas: list[str],
    ) -> BetaMessage:
        """Create a message using the Anthropic API."""
        raise NotImplementedError

    async def _make_api_call_with_retries(self, api_call):
        """Make an API call with exponential backoff retry logic.

        Args:
            api_call: Async function that makes the actual API call

        Returns:
            API response

        Raises:
            APIConnectionError: If all retries fail
        """
        retry_count = 0
        last_error = None

        while retry_count < self.MAX_RETRIES:
            try:
                return await api_call()
            except Exception as e:
                last_error = e
                retry_count += 1

                if retry_count == self.MAX_RETRIES:
                    break

                # Calculate delay with exponential backoff and jitter
                delay = min(
                    self.INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)), self.MAX_RETRY_DELAY
                )
                # Add jitter to avoid thundering herd
                jitter = delay * self.JITTER_FACTOR * (2 * random.random() - 1)
                final_delay = delay + jitter

                logger.info(
                    f"Retrying request (attempt {retry_count}/{self.MAX_RETRIES}) "
                    f"in {final_delay:.2f} seconds after error: {str(e)}"
                )
                await asyncio.sleep(final_delay)

        raise APIConnectionError(
            f"Failed after {self.MAX_RETRIES} retries. " f"Last error: {str(last_error)}"
        )


class AnthropicDirectClient(BaseAnthropicClient):
    """Direct Anthropic API client implementation."""

    def __init__(self, api_key: str, model: str):
        self.model = model
        self.client = Anthropic(api_key=api_key, http_client=self._create_http_client())

    def _create_http_client(self) -> httpx.Client:
        """Create an HTTP client with appropriate settings."""
        return httpx.Client(
            verify=True,
            timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
            transport=httpx.HTTPTransport(
                retries=3,
                verify=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            ),
        )

    async def create_message(
        self,
        *,
        messages: list[BetaMessageParam],
        system: list[Any],
        tools: list[BetaToolUnionParam],
        max_tokens: int,
        betas: list[str],
    ) -> BetaMessage:
        """Create a message using the direct Anthropic API with retry logic."""

        async def api_call():
            response = self.client.beta.messages.with_raw_response.create(
                max_tokens=max_tokens,
                messages=messages,
                model=self.model,
                system=system,
                tools=tools,
                betas=betas,
            )
            log_api_interaction(response.http_response.request, response.http_response, None)
            return response.parse()

        try:
            return await self._make_api_call_with_retries(api_call)
        except Exception as e:
            log_api_interaction(None, None, e)
            raise


class AnthropicVertexClient(BaseAnthropicClient):
    """Google Cloud Vertex AI implementation of Anthropic client."""

    def __init__(self, model: str):
        self.model = model
        self.client = AnthropicVertex()

    async def create_message(
        self,
        *,
        messages: list[BetaMessageParam],
        system: list[Any],
        tools: list[BetaToolUnionParam],
        max_tokens: int,
        betas: list[str],
    ) -> BetaMessage:
        """Create a message using Vertex AI with retry logic."""

        async def api_call():
            response = self.client.beta.messages.with_raw_response.create(
                max_tokens=max_tokens,
                messages=messages,
                model=self.model,
                system=system,
                tools=tools,
                betas=betas,
            )
            log_api_interaction(response.http_response.request, response.http_response, None)
            return response.parse()

        try:
            return await self._make_api_call_with_retries(api_call)
        except Exception as e:
            log_api_interaction(None, None, e)
            raise


class AnthropicBedrockClient(BaseAnthropicClient):
    """AWS Bedrock implementation of Anthropic client."""

    def __init__(self, model: str):
        self.model = model
        self.client = AnthropicBedrock()

    async def create_message(
        self,
        *,
        messages: list[BetaMessageParam],
        system: list[Any],
        tools: list[BetaToolUnionParam],
        max_tokens: int,
        betas: list[str],
    ) -> BetaMessage:
        """Create a message using AWS Bedrock with retry logic."""

        async def api_call():
            response = self.client.beta.messages.with_raw_response.create(
                max_tokens=max_tokens,
                messages=messages,
                model=self.model,
                system=system,
                tools=tools,
                betas=betas,
            )
            log_api_interaction(response.http_response.request, response.http_response, None)
            return response.parse()

        try:
            return await self._make_api_call_with_retries(api_call)
        except Exception as e:
            log_api_interaction(None, None, e)
            raise


class AnthropicClientFactory:
    """Factory for creating appropriate Anthropic client implementations."""

    @staticmethod
    def create_client(provider: LLMProvider, api_key: str, model: str) -> BaseAnthropicClient:
        """Create an appropriate client based on the provider."""
        if provider == LLMProvider.ANTHROPIC:
            return AnthropicDirectClient(api_key, model)
        elif provider == LLMProvider.VERTEX:
            return AnthropicVertexClient(model)
        elif provider == LLMProvider.BEDROCK:
            return AnthropicBedrockClient(model)
        raise ValueError(f"Unsupported provider: {provider}")
