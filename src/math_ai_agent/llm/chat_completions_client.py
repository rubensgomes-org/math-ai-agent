"""LLM client for the legacy OpenAI Chat Completions API
(``POST /v1/chat/completions``).
"""

import logging
from typing import Any, cast, final

import mcp_types
from openai.types.chat import ChatCompletion

from math_ai_agent.config.config import LLMConfig
from math_ai_agent.llm.llm_client import LLMClient
from math_ai_agent.llm.utils import (
    function_definition,
    omit_if_none,
    to_json,
)

logger = logging.getLogger(__name__)

@final
class ChatCompletionsClient(LLMClient[ChatCompletion]):
    """OpenAI ChatCompletions API (``POST /v1/chat/completions``)."""

    def __init__(
        self, llm_config: LLMConfig, tools: list[mcp_types.Tool]
    ) -> None:
        super().__init__(llm_config, self._format_tools(tools))

    @staticmethod
    def _format_tools(tools: list[mcp_types.Tool]) -> list[dict]:
        """Format MCP tools definitions for the Chat Completions API.
        Returns:
            A list of dicts in the Chat Completions tool format::

                [
                    {
                        "type": "function",
                        "function": {
                            "name": "add",
                            "description": "Add two numbers",
                            "parameters": { ... }
                        }
                    },
                    ...
                ]
        """
        return [
            {"type": "function", "function": function_definition(tool)}
            for tool in tools
        ]

    async def prompt(self, history: list[Any]) -> ChatCompletion:
        logger.debug(
            "LLM client sending %d message(s) to model %s\n"
            "Messages:\n%s\n"
            "Tools:\n%s",
            len(history),
            self.model,
            to_json(history),
            to_json(self.tools),
        )
        response = cast(
            ChatCompletion,
            await self.openai_client.chat.completions.create(
                model=self.model,
                messages=history,
                tools=self.tools,  # type: ignore[arg-type]
                temperature=omit_if_none(self.temperature),
            ),
        )
        logger.debug("LLM response:\n%s", to_json(response))
        return response

    @staticmethod
    def log_token_usage(response: ChatCompletion) -> None:
        usage = response.usage
        if usage is not None:
            logger.info(
                "Token usage in the current request:"
                " prompt=%d completion=%d total=%d",
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )
        else:
            logger.warning("No token usage reported in the response.")
