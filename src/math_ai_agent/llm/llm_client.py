"""Abstract client for OpenAI-compatible LLM APIs."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self

from ai_utils_lib.config.azure.entra_id import token_provider
from ai_utils_lib.config.models import Model
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_VISIBLE_SECRET_CHARS = 4
_SECRET_MASK = "****"


class LLMClient[ResponseT](ABC):
    """Abstract type w/common interface for LLM models using OpenAI APIs"""

    def __init__(self, model: Model, tools: list[dict]) -> None:
        if not tools:
            raise ValueError("tools must not be empty")
        logger.info(
            "Initializing LLM=%s with base_url=%s, model=%s, tool_count=%d",
            type(self).__name__,
            model.base_url,
            model.name,
            len(tools),
        )
        self._credential: DefaultAzureCredential | None = None
        api_key: str | Callable[[], Awaitable[str]] = model.api_key
        if model.api_key is None:
            logger.info("api_key not found. using Azure credential.")
            self._credential = DefaultAzureCredential()
            api_key = token_provider(self._credential)
        logger.debug(
            "AsyncOpenAI client initialized with api_key=%s, base_url=%s, "
            "timeout=%s",
            "Entra ID" if callable(api_key) else _mask_secret(api_key),
            model.base_url,
            model.timeout_seconds,
        )
        self.base_url = str(model.base_url)
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=model.timeout_seconds,
        )
        self.tools = tools
        self.model = model.name
        self.temperature = model.temperature
        self.system_instructions = model.instructions

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the ``AsyncOpenAI`` connections and any Azure credential."""
        logger.debug("Closing LLM OpenAI client %s", type(self).__name__)
        await self.openai_client.close()
        if self._credential:
            await self._credential.close()

    @abstractmethod
    async def prompt(self, history: list[Any]) -> ResponseT: ...

    @staticmethod
    @abstractmethod
    def log_token_usage(response: ResponseT) -> None: ...


def _mask_secret(secret: str) -> str:
    """Return ``secret`` masked except for its last few characters."""
    if len(secret) <= _VISIBLE_SECRET_CHARS:
        return _SECRET_MASK
    return _SECRET_MASK + secret[-_VISIBLE_SECRET_CHARS:]
