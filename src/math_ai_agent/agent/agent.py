"""Agent orchestrating the LLM and the calculator MCP server."""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Self

import mcp_types
from ai_utils_lib.config.models import Model
from fastmcp.client.client import CallToolResult
from fastmcp.exceptions import ToolError
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.responses import Response, ResponseFunctionToolCall
from pydantic import BaseModel, ConfigDict

from math_ai_agent.agent.utils import (
    join_reasoning,
    reasoning_texts,
    replay_input,
)
from math_ai_agent.agent.errors import (
    AgentBusyError,
    ContentFilterError,
    LLMRateLimitedError,
    LLMRequestFailedError,
    MaxTurnsExceededError,
    TokenLimitError,
    UnexpectedResponseError,
)
from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from math_ai_agent.llm.responses_client import ResponsesClient
from math_ai_agent.llm.utils import json_for_log
from math_ai_agent.mcp.calc_client import CalcMCPClient

DEFAULT_MAX_TURNS = 10

_BANNER_RULE = "=" * 54
_RATE_LIMIT_CODE = "rate_limit_exceeded"
_CONTENT_FILTERED = "Content blocked for safety reasons on turn {turn}."

logger = logging.getLogger(__name__)


class AgentAnswer(BaseModel):
    """The final answer and any reasoning the LLM returned for a prompt."""

    model_config = ConfigDict(frozen=True)

    answer: str
    reasoning: str | None = None


class Agent:
    """Runs prompts through the LLM and the calculator MCP server."""

    def __init__(
        self,
        calc: CalcMCPClient,
        model: Model,
        llm: ChatCompletionsClient | ResponsesClient | None = None,
        max_turns: int = DEFAULT_MAX_TURNS,
    ) -> None:
        """Create an agent from an open MCP connection.

        When ``llm`` is omitted, the client for ``model`` is built on
        entering the agent's context.  The agent closes ``llm`` on exit.
        A prompt fails after ``max_turns`` LLM calls without an answer.
        """
        self._calc = calc
        self._model = model
        self._llm = llm
        self._max_turns = max_turns
        self._exit_stack = AsyncExitStack()
        # Allows model.max_concurrent_prompts prompts to run at once.
        self._prompt_slots = asyncio.Semaphore(model.max_concurrent_prompts)

    async def __aenter__(self) -> Self:
        if self._llm is None:
            self._llm = await self._create_llm()
        # Registers self._llm to be closed when the agent exits.
        await self._exit_stack.enter_async_context(self._llm)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        logger.info("Closing agent")
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def run(self, user_prompt: str) -> AgentAnswer:
        """Run the agent loop for the configured OpenAI API style."""
        # Narrows the optional self._llm, assigned in __aenter__, for mypy.
        if self._llm is None:
            raise RuntimeError("Agent must be entered before calling run()")
        if self._prompt_slots.locked():
            logger.warning("Rejecting prompt: all prompt slots are in use")
            raise AgentBusyError("Too many prompts are running")
        async with self._prompt_slots:
            if isinstance(self._llm, ResponsesClient):
                logger.debug("Using Responses API to prompt LLM")
                return await self._run_responses(self._llm, user_prompt)
            logger.debug("Using Chat Completions API to prompt LLM")
            return await self._run_chat(self._llm, user_prompt)

    @staticmethod
    def _first_choice(
        response: ChatCompletion,
    ) -> tuple[ChatCompletionMessage, str]:
        """Return the first choice's message and finish reason."""
        if not response.choices:
            raise UnexpectedResponseError("LLM response has no choices")
        choice = response.choices[0]
        return choice.message, choice.finish_reason

    @staticmethod
    def _raise_for_status(response: Response, turn: int) -> None:
        """Raise an error unless the response status is completed."""
        logger.debug("LLM response status: %s", response.status)
        match response.status:
            case "completed":
                return
            case "incomplete":
                details = response.incomplete_details
                reason = details.reason if details is not None else None
                if reason == "max_output_tokens":
                    raise TokenLimitError("Token limit reached.")
                if reason == "content_filter":
                    raise ContentFilterError(
                        _CONTENT_FILTERED.format(turn=turn)
                    )
                raise UnexpectedResponseError(
                    f"Unknown incomplete reason: {reason}"
                )
            case "failed":
                err = response.error
                detail = err.message if err is not None else "unknown error"
                code = err.code if err is not None else None
                error_class = (
                    LLMRateLimitedError
                    if code == _RATE_LIMIT_CODE
                    else LLMRequestFailedError
                )
                raise error_class(f"LLM request failed: {detail} (code={code})")
            case _:
                # Only regular create calls are made, without background
                # or streaming, so "queued" and "in_progress" are
                # unexpected.
                raise UnexpectedResponseError(
                    f"Non-supported response status: {response.status}"
                )

    @staticmethod
    def _tool_error(message: str) -> str:
        """Log a failed tool call and return the error text for the LLM."""
        logger.warning("Calculator MCP tool call failed: %s", message)
        return message

    @staticmethod
    def _tool_result_text(result: CallToolResult) -> str:
        """Return the tool's structured data, else its text content."""
        if result.data is not None:
            return str(result.data)
        return "\n".join(
            block.text
            for block in result.content
            if isinstance(block, mcp_types.TextContent)
        )

    async def _create_llm(self) -> ChatCompletionsClient | ResponsesClient:
        """Discover the MCP tools and build the configured LLM client."""
        tools: list[mcp_types.Tool] = await self._calc.list_tools()
        logger.info(
            "Creating LLM client using api_style=%s", self._model.api_style
        )
        if self._model.api_style == "responses":
            return ResponsesClient(self._model, tools)
        return ChatCompletionsClient(self._model, tools)

    async def _call_calc_tool(self, tool_name: str, arguments: str) -> str:
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError as error:
            return self._tool_error(
                f"Error calling tool '{tool_name}': invalid JSON arguments:"
                f" {error}"
            )
        if not isinstance(args, dict):
            return self._tool_error(
                f"Error calling tool '{tool_name}': arguments must be a JSON"
                " object"
            )
        try:
            logger.debug(
                "Calling calculator MCP tool %s with %s", tool_name, args
            )
            result = await self._calc.call_tool(tool_name, args)
        except ToolError as error:
            return self._tool_error(str(error))
        logger.debug(
            "Calculator MCP tool %s result:\n%s",
            tool_name,
            json.dumps(result.structured_content, indent=2, ensure_ascii=False),
        )
        return self._tool_result_text(result)

    async def _run_chat(
        self, llm: ChatCompletionsClient, user_prompt: str
    ) -> AgentAnswer:
        """Run the agent loop against the Chat Completions API."""
        history: list[Any] = [{"role": "user", "content": user_prompt}]
        logger.debug("user prompt: %s", user_prompt)
        _log_loop_start()
        for turn in range(1, self._max_turns + 1):
            _log_turn(turn, history)
            response: ChatCompletion = await llm.prompt(history)
            llm.log_token_usage(response)
            message, finish_reason = self._first_choice(response)
            logger.debug("LLM finish_reason: %s", finish_reason)

            match finish_reason:
                case "stop":
                    _log_loop_end(message.content)
                    return AgentAnswer(answer=(message.content or "").strip())
                case "tool_calls":
                    history.append(message.model_dump(exclude_none=True))
                    history.extend(await self._chat_tool_messages(message))
                case "length":
                    raise TokenLimitError("Token limit reached.")
                case "content_filter":
                    raise ContentFilterError(
                        _CONTENT_FILTERED.format(turn=turn)
                    )
                case _:
                    raise UnexpectedResponseError(
                        f"Non-supported finish_reason: {finish_reason}"
                    )
        raise MaxTurnsExceededError(f"No answer after {self._max_turns} turns.")

    async def _chat_tool_messages(
        self, message: ChatCompletionMessage
    ) -> list[dict[str, str]]:
        """Call each tool the message requests and return the tool messages."""
        if not message.tool_calls:
            raise UnexpectedResponseError("LLM requested no tool calls")
        logger.info("LLM is asking us to call tool(s): %s", message.tool_calls)
        tool_messages = []
        for tool_call in message.tool_calls:
            if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
                raise UnexpectedResponseError(
                    f"Non-supported tool call type: {tool_call.type}"
                )
            result = await self._call_calc_tool(
                tool_call.function.name, tool_call.function.arguments
            )
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )
        return tool_messages

    async def _run_responses(
        self, llm: ResponsesClient, user_prompt: str
    ) -> AgentAnswer:
        """Run the agent loop against the Responses API."""
        # The system_instructions is sent as the top-level `instructions`
        # parameter, so it is not part of the history.
        history: list[Any] = [{"role": "user", "content": user_prompt}]
        previous_response_id: str | None = None
        # Reasoning collected from every turn, for the answer.
        reasoning: list[str] = []
        logger.debug("user prompt: %s", user_prompt)
        logger.debug(
            "LLM model is operating in %s mode",
            "stateful" if llm.is_stateful else "stateless",
        )
        _log_loop_start()
        for turn in range(1, self._max_turns + 1):
            _log_turn(turn, history)
            response: Response = await llm.prompt(history, previous_response_id)
            llm.log_token_usage(response)
            self._raise_for_status(response, turn)
            reasoning.extend(reasoning_texts(response))

            tool_calls = [
                item
                for item in response.output
                if isinstance(item, ResponseFunctionToolCall)
            ]
            if not tool_calls:
                _log_loop_end(response.output_text)
                return AgentAnswer(
                    answer=response.output_text.strip(),
                    reasoning=join_reasoning(reasoning),
                )

            tool_outputs = await self._responses_tool_outputs(tool_calls)
            if llm.is_stateful:
                history = tool_outputs
                previous_response_id = response.id
            else:
                history = replay_input(history, response.output, tool_outputs)
        raise MaxTurnsExceededError(f"No answer after {self._max_turns} turns.")

    async def _responses_tool_outputs(
        self, tool_calls: list[ResponseFunctionToolCall]
    ) -> list[Any]:
        """Call each requested tool and return the function call outputs."""
        logger.info("LLM requested to call tool(s): %s", tool_calls)
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
        return tool_outputs


def _log_loop_start() -> None:
    logger.info(
        "\n%s\n========= >>> START AGENT LOOP <<<\n%s",
        _BANNER_RULE,
        _BANNER_RULE,
    )


def _log_turn(turn: int, history: list[Any]) -> None:
    logger.info("========= >>> START LOOP TURN %d <<<", turn)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("history: %s", json_for_log(history))


def _log_loop_end(answer: str | None) -> None:
    logger.info("========= >>> LLM TASK COMPLETED <<<")
    logger.debug("response: %s", answer)
    logger.info(
        "\n%s\n========= >>> END AGENT LOOP <<<\n%s",
        _BANNER_RULE,
        _BANNER_RULE,
    )
