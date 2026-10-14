"""Abstract client for OpenAI-compatible LLM APIs."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self

from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI

from math_ai_agent.config.models import LLMConfig
from math_ai_agent.config.ms import entra_id

logger = logging.getLogger(__name__)

_VISIBLE_SECRET_CHARS = 4
_SECRET_MASK = "****"


class LLMClient[ResponseT](ABC):
    """Abstract type w/common interface for LLM models using OpenAI APIs"""

    def __init__(self, llm_config: LLMConfig, tools: list[dict]) -> None:
        if not tools:
            raise ValueError("tools must not be empty")
        logger.info(
            "Initializing LLM=%s with base_url=%s, model=%s, tool_count=%d",
            type(self).__name__,
            llm_config.model_base_url,
            llm_config.model,
            len(tools),
        )
        self._credential: DefaultAzureCredential | None = None
        api_key: str | Callable[[], Awaitable[str]] = llm_config.api_key
        if llm_config.is_azure:
            self._credential = DefaultAzureCredential()
            api_key = entra_id.token_provider(self._credential)
        logger.debug(
            "AsyncOpenAI client initialized with api_key=%s, base_url=%s, "
            "timeout=%s",
            "Entra ID" if callable(api_key) else _mask_secret(api_key),
            llm_config.model_base_url,
            llm_config.timeout_seconds,
        )
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=llm_config.model_base_url,
            timeout=llm_config.timeout_seconds,
        )
        self.base_url = llm_config.model_base_url
        self.tools = tools
        self.model = llm_config.model
        self.temperature = llm_config.temperature
        self.system_instructions = llm_config.system_instructions

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
