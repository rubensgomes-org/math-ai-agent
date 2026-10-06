"""Abstract client for OpenAI-compatible LLM APIs."""

import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Self

from openai import AsyncOpenAI

from math_ai_agent.config.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient[ResponseT](ABC):
    """Abstract type w/common interface to models using OpenAI APIs"""

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
        self.openai_client = AsyncOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.model_base_url,
            timeout=llm_config.timeout_seconds,
        )
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
        """Close the underlying ``AsyncOpenAI`` HTTP connections."""
        logger.debug("Closing LLM client%s", type(self).__name__)
        await self.openai_client.close()

    @abstractmethod
    async def prompt(self, history: list[Any]) -> ResponseT: ...

    @staticmethod
    @abstractmethod
    def log_token_usage(response: ResponseT) -> None: ...
