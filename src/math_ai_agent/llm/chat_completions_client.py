"""LLM client for the legacy OpenAI Chat Completions API
(``POST /v1/chat/completions``).
"""

import logging
from typing import final

import mcp_types
from ai_utils_lib.config.models import Model
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionFunctionToolParam,
    ChatCompletionMessageParam,
)
from openai.types.shared_params import FunctionDefinition

from math_ai_agent.llm.llm_client import LLMClient
from math_ai_agent.llm.utils import json_for_log, omit_if_none

logger = logging.getLogger(__name__)


@final
class ChatCompletionsClient(
    LLMClient[ChatCompletion, ChatCompletionFunctionToolParam]
):
    """OpenAI Chat Completions API (``POST /v1/chat/completions``)."""

    def __init__(self, model: Model, tools: list[mcp_types.Tool]) -> None:
        if model.is_stateful:
            raise ValueError(
                "The Chat Completions API is stateless; set"
                " model.is_stateful to false"
            )
        super().__init__(model, self._format_tools(tools))

    async def prompt(
        self, history: list[ChatCompletionMessageParam]
    ) -> ChatCompletion:
        """Send the system message and conversation messages to the model."""
        logger.debug(
            "LLM client sending %d message(s) to model %s, temperature=%s",
            len(history),
            self.model_name,
            self.temperature,
        )
        response = await self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_instructions},
                *history,
            ],
            tools=self.tools,
            temperature=omit_if_none(self.temperature),
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("LLM response:\n%s", json_for_log(response))
        return response

    @staticmethod
    def _format_tools(
        tools: list[mcp_types.Tool],
    ) -> list[ChatCompletionFunctionToolParam]:
        """Format MCP tools as nested Chat Completions function tools."""
        return [
            {"type": "function", "function": _function_definition(tool)}
            for tool in tools
        ]

    @staticmethod
    def _token_usage(response: ChatCompletion) -> dict[str, int] | None:
        usage = response.usage
        if usage is None:
            return None
        prompt_details = usage.prompt_tokens_details
        completion_details = usage.completion_tokens_details
        counts = {
            "prompt": usage.prompt_tokens,
            "cached": (
                prompt_details.cached_tokens
                if prompt_details is not None
                else None
            ),
            "completion": usage.completion_tokens,
            "reasoning": (
                completion_details.reasoning_tokens
                if completion_details is not None
                else None
            ),
            "total": usage.total_tokens,
        }
        return {
            name: count for name, count in counts.items() if count is not None
        }


def _function_definition(tool: mcp_types.Tool) -> FunctionDefinition:
    definition: FunctionDefinition = {
        "name": tool.name,
        "parameters": tool.input_schema,
    }
    if tool.description:
        definition["description"] = tool.description
    return definition
