"""Agent orchestrating the LLM and the calculator MCP server."""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Self

import mcp_types
from fastmcp.exceptions import ToolError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.responses import Response, ResponseFunctionToolCall

from math_ai_agent.agent.utils import (
    format_answer,
    next_turn_input,
    reasoning_texts,
    tool_error,
)
from math_ai_agent.config.config import get_config
from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from math_ai_agent.llm.llm_errors import (
    AgentBusyError,
    ContentFilterError,
    LLMRequestFailedError,
    TokenLimitError,
)
from math_ai_agent.llm.responses_client import ResponsesClient
from math_ai_agent.llm.utils import to_json
from math_ai_agent.mcp.calc_client import CalcMCPClient

logger = logging.getLogger(__name__)


class Agent:
    """Runs prompts through the LLM and the calculator MCP server."""

    def __init__(
        self,
        calc: CalcMCPClient,
        llm: ChatCompletionsClient | ResponsesClient | None = None,
    ) -> None:
        """Create an agent from an open MCP connection.

        When ``llm`` is omitted, the configured LLM client is built on
        entering the agent's context.
        """
        self._calc = calc
        self._llm = llm
        # Allows llm.max_concurrent_prompts from config.yaml prompts to run
        # at once.
        self._exit_stack = AsyncExitStack()
        self._prompt_slots = asyncio.Semaphore(
            get_config().llm.max_concurrent_prompts
        )

    async def __aenter__(self) -> Self:
        if self._llm is None:
            self._llm = await self._create_llm()
        # 1. opens self._llm: async __aenter__
        # 2. register self._llm async __axit__ callback function
        await self._exit_stack.enter_async_context(self._llm)
        return self

    async def _create_llm(self) -> ChatCompletionsClient | ResponsesClient:
        """Discover the MCP tools and build the configured LLM client."""
        tools: list[mcp_types.Tool] = await self._calc.list_tools()
        llm_config = get_config().llm
        logger.info(
            "Creating LLM client using api_style=%s", llm_config.api_style
        )
        if llm_config.api_style == "responses":
            return ResponsesClient(llm_config, tools)
        return ChatCompletionsClient(llm_config, tools)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        logger.info("Closing agent")
        # hands the agent's cleanup over to the AsyncExitStack
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def run(
        self, user_prompt: str, display_reasoning: bool = True
    ) -> str:
        """Run the agent loop for the configured OpenAI API style."""
        if self._prompt_slots.locked():
            logger.warning("Rejecting prompt: all prompt slots are in use")
            raise AgentBusyError("Too many prompts are running")
        async with self._prompt_slots:
            if isinstance(self._llm, ResponsesClient):
                logger.debug("Using Responses API to prompt LLM")
                return await self._run_responses(
                    self._llm, user_prompt, display_reasoning
                )
            logger.debug("Using Chat Completions API to prompt LLM")
            return await self._run_chat(self._llm, user_prompt)

    async def _call_calc_tool(self, tool_name: str, arguments: str) -> str:
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError as error:
            return tool_error(
                tool_name,
                f"Error calling tool '{tool_name}': invalid JSON arguments:"
                f" {error}",
            )
        if not isinstance(args, dict):
            return tool_error(
                tool_name,
                f"Error calling tool '{tool_name}': arguments must be a JSON"
                " object",
            )
        try:
            logger.debug("Calling calculator MCP tool %s with %s", tool_name,
                         args)
            result = await self._calc.call_tool(tool_name, args)
        except ToolError as error:
            return tool_error(tool_name, str(error))
        logger.debug(
            "Calculator MCP tool %s result:\n%s",
            tool_name,
            json.dumps(result.structured_content, indent=2, ensure_ascii=False),
        )
        return str(result.data)

    async def _run_chat(
        self, llm: ChatCompletionsClient, user_prompt: str
    ) -> str:
        """Run the agent loop against the Chat Completions API."""
        logger.debug("Starting agent loop for the ChatCompletions API")
        history: list[Any] = [
            {"role": "system", "content": llm.system_instructions},
            {"role": "user", "content": user_prompt},
        ]
        logger.debug("user prompt: %s", user_prompt)

        # -------------------------
        # Agent Loop
        # -------------------------
        logger.info(
            "\n======================================================\n"
            "========= >>> START AGENT LOOP <<< ===================\n"
            "======================================================"
        )
        loop_turn: int = 0
        while True:
            loop_turn += 1
            logger.info(
                "\n========= >>> START LOOP TURN <<< ===================\n"
                "loop turn: %s\nhistory: %s",
                loop_turn,
                to_json(history),
            )
            response: ChatCompletion = await llm.prompt(history)
            llm_msg: ChatCompletionMessage = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            logger.debug("LLM finish_reason: %s", finish_reason)
            llm.log_token_usage(response)

            match finish_reason:
                case "stop":
                    logger.info(
                        "\n========= >>> LLM TASK COMPLETED <<< ============\n"
                        "response: %s",
                        llm_msg.content,
                    )
                    break

                case "length":
                    raise TokenLimitError("Token limit reached.")

                case "tool_calls":
                    history.append(llm_msg)
                    assert llm_msg.tool_calls is not None
                    logger.info(
                        "LLM is asking us to call tool(s): %s",
                        llm_msg.tool_calls,
                    )
                    for tool_call in llm_msg.tool_calls:
                        fn = tool_call.function  # type: ignore[union-attr]
                        tool_name = fn.name
                        tool_call_id = tool_call.id
                        logger.debug(
                            "Calling tool_call_id: %s, tool_name: %s",
                            tool_call_id,
                            tool_name,
                        )
                        result = await self._call_calc_tool(
                            tool_name, fn.arguments
                        )
                        history.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": result,
                            }
                        )
                    continue

                case "content_filter":
                    error = f"Content [{history}] blocked for safety reasons."
                    raise ContentFilterError(error)

                case _:
                    error = f"Non-supported finish_reason: {finish_reason}"
                    raise ValueError(error)

        logger.info(
            "\n======================================================\n"
            "========= >>> END AGENT LOOP <<< =====================\n"
            "======================================================"
        )
        return llm_msg.content or ""

    async def _run_responses(
        self,
        llm: ResponsesClient,
        user_prompt: str,
        display_reasoning: bool = True,
    ) -> str:
        """Run the agent loop against the Responses API."""
        logger.debug("Starting agent loop for the Responses API")
        # The system_instructions is sent as the top-level `instructions`
        # parameter, so it is not part of the history.
        history: list[Any] = [{"role": "user", "content": user_prompt}]
        previous_response_id: str | None = None
        # Reasoning collected from every turn, for the formatted answer.
        reasoning: list[str] = []
        logger.info("user_prompt: %s", user_prompt)

        # -------------------------
        # Agent Loop
        # -------------------------
        logger.info(
            "\n======================================================\n"
            "========= >>> START AGENT LOOP <<< ===================\n"
            "======================================================"
        )
        loop_turn: int = 0
        while True:
            loop_turn += 1
            logger.info(
                "\n========= >>> START LOOP TURN <<< ===================\n"
                "loop turn: %s\nhistory: %s",
                loop_turn,
                to_json(history),
            )
            response: Response = await llm.prompt(history, previous_response_id)
            logger.debug("LLM response status: %s", response.status)
            llm.log_token_usage(response)

            match response.status:
                case "completed":
                    reasoning.extend(reasoning_texts(response))

                    # check if the LLM is asking us to run any tool
                    tool_calls = [
                        item
                        for item in response.output
                        if isinstance(item, ResponseFunctionToolCall)
                    ]

                    if tool_calls:
                        logger.info(
                            "LLM requested to call tool(s): %s", tool_calls
                        )
                    else:
                        logger.info(
                            "\n========= >>> LLM TASK COMPLETED <<< "
                            "=================\n"
                            "response: %s",
                            response.output_text,
                        )
                        break

                    tool_outputs: list[Any] = []
                    for tool_call in tool_calls:
                        result = await self._call_calc_tool(
                            tool_call.name, tool_call.arguments
                        )
                        logger.debug("Tool call result: %s", result)
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": tool_call.call_id,
                                "output": result,
                            }
                        )
                    history = next_turn_input(
                        llm.is_stateful, history, response.output, tool_outputs
                    )
                    previous_response_id = (
                        response.id if llm.is_stateful else None
                    )
                    continue

                case "incomplete":
                    details = response.incomplete_details
                    reason = details.reason if details is not None else None
                    if reason == "max_output_tokens":
                        raise TokenLimitError("Token limit reached.")
                    if reason == "content_filter":
                        error = (
                            f"Content [{history}] blocked for safety "
                            f"reasons."
                        )
                        raise ContentFilterError(error)
                    error = f"Unknown incomplete reason: {reason}"
                    raise ValueError(error)

                case "failed":
                    err = response.error
                    detail = err.message if err is not None else "unknown error"
                    code = err.code if err is not None else None
                    error = f"LLM request failed: {detail} (code={code})"
                    raise LLMRequestFailedError(error, code)

                case _:
                    # this project only supports regular create call without
                    # background or streaming.  Therefore, other response
                    # status like "queued", "in_progress" are not supported.
                    error = (
                        f"Non-supported response status:" f" {response.status}"
                    )
                    raise ValueError(error)

        logger.info(
            "\n======================================================\n"
            "========= >>> END AGENT LOOP <<< =====================\n"
            "======================================================"
        )
        if not display_reasoning:
            return response.output_text.strip()
        return format_answer(reasoning, response.output_text)
