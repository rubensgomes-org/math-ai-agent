"""LLM client for the OpenAI Responses API (``POST /v1/responses``)."""

import logging
from typing import Any, cast

import mcp_types
from openai import omit
from openai.types.responses import Response

from math_ai_agent.config.config import LLMConfig
from math_ai_agent.llm.llm_client import LLMClient
from math_ai_agent.llm.utils import (
    function_definition,
    omit_if_none,
    to_json,
)

logger = logging.getLogger(__name__)


class ResponsesClient(LLMClient[Response]):
    """OpenAI Responses API (``POST /v1/responses``)."""

    def __init__(
        self, llm_config: LLMConfig, tools: list[mcp_types.Tool]
    ) -> None:
        super().__init__(llm_config, self._format_tools(tools))
        self.is_stateful = llm_config.is_stateful

    @staticmethod
    def _format_tools(tools: list[mcp_types.Tool]) -> list[dict]:
        """Format MCP tools definitions for the Responses API.

        Unlike the Chat Completions format, the Responses API uses a
        flat shape with no nested ``function`` object.

        Args:
            tools: The MCP server's tools.

        Returns:
            A list of dicts in the Responses tool format::

                [
                    {
                        "type": "function",
                        "name": "add",
                        "description": "Add two numbers",
                        "parameters": { ... }
                    },
                    ...
                ]
        """
        return [
            {"type": "function", **function_definition(tool)} for tool in tools
        ]

    async def prompt(
        self, history: list[Any], previous_response_id: str | None = None
    ) -> Response:
        # The call to the LLM model has:
        # - instructions: you should always add this instruction because there
        #     is no guarantee the LLM model will save this
        # - input items: this contains the conversation history which may only
        #     require new input items for stateful connections.  The previous
        #     items are based on passing previous_response_id.
        # - tools: you should always pass when you want the LLM to consider
        #     these tools on the new request.
        logger.debug(
            "LLM client sending request with:\n"
            "model %s\n"
            "temperature %s\n"
            "instructions %s\n"
            "previous_response_id %s\n"
            "input items %s\n"
            "tools %s",
            self.model,
            self.temperature,
            self.system_instructions,
            previous_response_id,
            to_json(history),
            to_json(self.tools),
        )
        response = cast(
            Response,
            await self.openai_client.responses.create(
                model=self.model,
                input=history,
                tools=self.tools,  # type: ignore[arg-type]
                instructions=self.system_instructions,
                # ``store`` controls server-side retention of the
                # request and response.  Unlike Chat Completions, the
                # Responses API is stateful by default (depending on
                # support by the LLM model), so it must be disabled
                # explicitly when stateless.
                store=self.is_stateful,
                # ``omit`` leaves the field out of the request.
                previous_response_id=previous_response_id or omit,
                temperature=omit_if_none(self.temperature),
            ),
        )
        logger.debug("LLM response:\n%s", to_json(response))
        return response

    @staticmethod
    def log_token_usage(response: Response) -> None:
        usage = response.usage
        if usage is not None:
            logger.info(
                "Token usage in the current request:"
                " input=%d output=%d total=%d",
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
            )
        else:
            logger.warning("No token usage reported in the response.")
