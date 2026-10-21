"""Abstract client for OpenAI-compatible LLM APIs."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Self

from ai_utils_lib.azure.entra_id import ai_token_provider
from ai_utils_lib.config.models import Model
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI

from math_ai_agent.llm.utils import json_for_log

logger = logging.getLogger(__name__)

# Retries on top of the first attempt, so a request can take up to
# (1 + _MAX_RETRIES) * model.timeout_seconds.
_MAX_RETRIES = 2
_VISIBLE_SECRET_CHARS = 4
_MIN_SECRET_LENGTH_WITH_SUFFIX = 12
_SECRET_MASK = "****"


class LLMClient[ResponseT, ToolT](ABC):
    """Abstract base for LLM clients using OpenAI-compatible APIs.

    Subclasses fill in the API-specific hooks (Template Method).  Use the
    client as an async context manager, which closes its connections.
    """

    def __init__(self, model: Model, tools: list[ToolT]) -> None:
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
        api_key = self._resolve_api_key(model)
        self.base_url = str(model.base_url)
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=model.timeout_seconds,
            max_retries=_MAX_RETRIES,
        )
        logger.debug(
            "AsyncOpenAI client initialized with api_key=%s, timeout=%s, "
            "max_retries=%d",
            "Entra ID" if callable(api_key) else _mask_secret(api_key),
            model.timeout_seconds,
            _MAX_RETRIES,
        )
        logger.debug(
            "LLM tools:\n%s\ninstructions:\n%s",
            json_for_log(tools),
            model.instructions,
        )
        self.tools = tools
        self.model_name = model.name
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
        try:
            await self.openai_client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()

    def log_token_usage(self, response: ResponseT) -> None:
        """Log the response's token counts, or warn when it has none."""
        usage = self._token_usage(response)
        if usage is None:
            logger.warning("No token usage reported in the response.")
            return
        logger.info(
            "Token usage in the current request: %s",
            " ".join(f"{name}={count}" for name, count in usage.items()),
        )

    @staticmethod
    @abstractmethod
    def _token_usage(response: ResponseT) -> dict[str, int] | None:
        """Return the response's token counts by name, or None if absent."""

    def _resolve_api_key(
        self, model: Model
    ) -> str | Callable[[], Awaitable[str]]:
        """Return the model's API key, else an Entra ID token provider.

        Entra ID is used only when no ``api_key_env`` is configured.
        """
        if model.api_key is not None:
            return model.api_key
        if model.api_key_env:
            raise ValueError(
                f"Environment variable {model.api_key_env} named by"
                " model.api_key_env is not set or is empty"
            )
        logger.info("No model.api_key_env configured; using Azure Entra ID")
        self._credential = DefaultAzureCredential()
        return ai_token_provider(self._credential)


def _mask_secret(secret: str) -> str:
    """Return ``secret`` masked, showing its last characters if long."""
    if len(secret) < _MIN_SECRET_LENGTH_WITH_SUFFIX:
        return _SECRET_MASK
    return _SECRET_MASK + secret[-_VISIBLE_SECRET_CHARS:]
