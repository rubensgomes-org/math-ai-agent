"""LLM client for the OpenAI Responses API (``POST /v1/responses``)."""

import logging
from typing import final

import mcp_types
from ai_utils_lib.config.models import Model
from openai import omit
from openai.types.responses import (
    FunctionToolParam,
    Response,
    ResponseIncludable,
    ResponseInputItemParam,
)

from math_ai_agent.llm.llm_client import LLMClient
from math_ai_agent.llm.utils import omit_if_none, json_for_log

logger = logging.getLogger(__name__)

_ENCRYPTED_REASONING: ResponseIncludable = "reasoning.encrypted_content"


@final
class ResponsesClient(LLMClient[Response, FunctionToolParam]):
    """OpenAI Responses API (``POST /v1/responses``)."""

    def __init__(self, model: Model, tools: list[mcp_types.Tool]) -> None:
        super().__init__(model, self._format_tools(tools))
        self.is_stateful = model.is_stateful

    async def prompt(
        self,
        history: list[ResponseInputItemParam],
        previous_response_id: str | None = None,
    ) -> Response:
        """Send the input items, continuing ``previous_response_id``."""
        if previous_response_id is not None and not self.is_stateful:
            raise ValueError("previous_response_id requires a stateful client")
        logger.debug(
            "LLM client sending %d input item(s) to model %s,"
            " previous_response_id=%s, temperature=%s",
            len(history),
            self.model_name,
            previous_response_id,
            self.temperature,
        )
        response = await self.openai_client.responses.create(
            model=self.model_name,
            input=history,
            tools=self.tools,
            # Instructions do not carry over from a previous response.
            instructions=self.system_instructions,
            # ``store`` defaults to true in the Responses API, so it is
            # disabled explicitly when stateless.
            store=self.is_stateful,
            # ``omit`` leaves the field out of the request.
            previous_response_id=previous_response_id or omit,
            # OpenAI accepts replayed reasoning items with ``store`` off
            # only with their encrypted content; other providers may
            # ignore this.
            include=(omit if self.is_stateful else [_ENCRYPTED_REASONING]),
            temperature=omit_if_none(self.temperature),
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("LLM response:\n%s", json_for_log(response))
        return response

    @staticmethod
    def _format_tools(
        tools: list[mcp_types.Tool],
    ) -> list[FunctionToolParam]:
        """Format MCP tools as flat, non-strict Responses function tools."""
        return [_function_tool(tool) for tool in tools]

    @staticmethod
    def _token_usage(response: Response) -> dict[str, int] | None:
        usage = response.usage
        if usage is None:
            return None
        return {
            "input": usage.input_tokens,
            "cached": usage.input_tokens_details.cached_tokens,
            "output": usage.output_tokens,
            "reasoning": usage.output_tokens_details.reasoning_tokens,
            "total": usage.total_tokens,
        }


def _function_tool(tool: mcp_types.Tool) -> FunctionToolParam:
    function_tool: FunctionToolParam = {
        "type": "function",
        "name": tool.name,
        "parameters": tool.input_schema,
        "strict": False,
    }
    if tool.description:
        function_tool["description"] = tool.description
    return function_tool
