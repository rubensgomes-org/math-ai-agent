# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review and
# refinement have occurred, users should be aware that the output may contain
# inaccuracies, errors, or security vulnerabilities
#
# **Third-Party Content Notice**
#
# This software may include components or snippets derived from third-party
# sources. The software's users and distributors are responsible for ensuring
# compliance with any underlying licenses applicable to such components.
#
# **Copyright Status Statement**
#
# Copyright protection, if any, is limited to the original
# human contributions and modifications made to this project.
# The AI-generated portions of the code and
# documentation are not subject to copyright and are considered to be in the
# public domain.
#
# **Limitation of liability**
#
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

"""Agent orchestrating the LLM and the calculator MCP server.

Provides the ``Agent`` class, which holds one calculator MCP
connection and one LLM client for reuse across prompts.  ``Agent.run``
dispatches to the agent loop matching the ``llm.api_style`` setting
in ``config.yaml``.

The LLM transports themselves live in
:mod:`math_ai_agent.llm.client`; this module owns the system
prompt, the control flow, and the tool dispatch.
"""

import asyncio
import json
import logging
from typing import Any

from fastmcp.exceptions import ToolError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseReasoningItem,
)

from math_ai_agent.config.config import get_api_key, get_config
from math_ai_agent.llm.client import ChatCompletionClient, ResponsesClient
from math_ai_agent.mcp.calc_connection import CalcMCPConnection

logger = logging.getLogger(__name__)

_EMPTY_SECTION = "(none)"


def _reasoning_texts(response: Response) -> list[str]:
    """Return the reasoning text in a response's reasoning items.

    An item's ``summary`` is used only when it has no ``content``: some
    providers repeat the content in the summary, and others, such as
    OpenAI, return only the summary.
    """
    return [
        part.text
        for item in response.output
        if isinstance(item, ResponseReasoningItem)
        for part in item.content or item.summary
    ]


def _next_turn_input(
    stateful: bool,
    input_items: list[Any],
    response: Response,
    tool_outputs: list[Any],
) -> tuple[list[Any], str | None]:
    """Return the input items and previous response ID for the next turn.

    Stateful turns send only the tool outputs and continue the stored
    ``response``.  Stateless turns replay the whole conversation,
    including reasoning items, so the model keeps its context.
    """
    if stateful:
        logger.debug("LLM model is operating in stateful mode")
        return tool_outputs, response.id
    logger.debug("LLM model is operating in stateless mode.")
    output_items = [
        item.model_dump(exclude_none=True) for item in response.output
    ]
    return [*input_items, *output_items, *tool_outputs], None


def _format_answer(reasoning: list[str], final_response: str) -> str:
    """Format the answer as reasoning and final response sections.

    Surrounding whitespace is stripped from each text, so sections are
    separated by exactly one blank line and turns by a line break.  Each
    section shows ``(none)`` when the LLM returned no text for it.
    """
    sections = {
        "reasoning": "\n".join(
            text.strip() for text in reasoning if text.strip()
        ),
        "final response": final_response.strip(),
    }
    return "\n\n".join(
        f"{heading}:\n{text or _EMPTY_SECTION}"
        for heading, text in sections.items()
    )


def _tool_error(tool_name: str, message: str) -> str:
    """Log a failed tool call and return the error text for the LLM."""
    logger.warning("Calculator MCP tool %s failed: %s", tool_name, message)
    return message


class AgentBusyError(RuntimeError):
    """Raised when the maximum number of prompts is already running."""


class TokenLimitError(RuntimeError):
    """Raised when the LLM stops because it reached its token limit."""


class ContentFilterError(RuntimeError):
    """Raised when the LLM provider blocks content for safety reasons."""


class LLMRequestFailedError(RuntimeError):
    """Raised when the LLM provider reports the response as failed."""

    def __init__(self, message: str, code: str | None = None) -> None:
        """Create the error.

        Args:
            message: Error description.
            code: Provider error code, such as ``server_error``.
        """
        super().__init__(message)
        self.code = code


class Agent:
    """Runs prompts through the LLM and the calculator MCP server.

    Holds one ``CalcMCPConnection`` and one LLM client, so they are
    reused across prompts.  The caller owns the MCP connection and
    must keep it open while the agent is in use.
    """

    def __init__(
        self,
        calc: CalcMCPConnection,
        llm: ChatCompletionClient | ResponsesClient,
        system_instructions: str,
        max_concurrent_prompts: int,
    ) -> None:
        """Create an agent from an open MCP connection and an LLM client."""
        self._calc = calc
        self._llm = llm
        self._system_instructions = system_instructions
        self._prompt_slots = asyncio.Semaphore(max_concurrent_prompts)

    @classmethod
    async def create(cls, calc: CalcMCPConnection) -> "Agent":
        """Discover the MCP tools and build the configured LLM client.

        Args:
            calc: An open calculator MCP connection.

        Returns:
            An agent using the ``llm.api_style`` set in ``config.yaml``.

        Raises:
            RuntimeError: If the configured API key environment
                variable is not set.
        """
        llm_config = get_config().llm
        logger.info(
            "Creating AI agent using LLM api_style=%s, "
            "model_base_url=%s, model=%s, temperature=%s",
            llm_config.api_style,
            llm_config.model_base_url,
            llm_config.model,
            llm_config.temperature,
        )
        llm: ChatCompletionClient | ResponsesClient
        if llm_config.api_style == "responses":
            llm = ResponsesClient(
                get_api_key(),
                llm_config.model_base_url,
                llm_config.model,
                await calc.to_responses_tools(),
                llm_config.timeout_seconds,
                llm_config.temperature,
                llm_config.stateful,
                llm_config.reasoning_summary,
            )
        else:
            llm = ChatCompletionClient(
                get_api_key(),
                llm_config.model_base_url,
                llm_config.model,
                await calc.to_chat_completions_tools(),
                llm_config.timeout_seconds,
                llm_config.temperature,
            )
        return cls(
            calc,
            llm,
            llm_config.system_instructions,
            llm_config.max_concurrent_prompts,
        )

    async def run(
        self, user_prompt: str, display_reasoning: bool = True
    ) -> str:
        """Run the agent loop for the configured OpenAI API style.

        Args:
            user_prompt: The math question from the user.
            display_reasoning: Include the reasoning section in the
                Responses API answer.  Chat Completions answers have
                no reasoning, so it is ignored there.

        Returns:
            The LLM's answer.  The Responses API answer also includes
            a reasoning section when ``display_reasoning`` is ``True``.

        Raises:
            AgentBusyError: If ``max_concurrent_prompts`` prompts are
                already running.
        """
        if self._prompt_slots.locked():
            logger.warning("Rejecting prompt: all prompt slots are in use")
            raise AgentBusyError("Too many prompts are running")
        async with self._prompt_slots:
            if isinstance(self._llm, ResponsesClient):
                logger.debug("Using Responses API to send LLM request")
                return await self._run_responses(
                    self._llm, user_prompt, display_reasoning
                )
            logger.debug("Using Chat Completions API to send LLM request")
            return await self._run_chat(self._llm, user_prompt)

    async def _call_tool(self, tool_name: str, arguments: str) -> str:
        """Call a calculator MCP tool and return its result as text.

        Invalid JSON arguments and tool errors, such as division by
        zero, are returned as error text so the LLM can recover.

        Args:
            tool_name: The name of the MCP tool to invoke.
            arguments: The tool arguments as a JSON object string.
        """
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError as error:
            return _tool_error(
                tool_name,
                f"Error calling tool '{tool_name}': invalid JSON arguments:"
                f" {error}",
            )
        if not isinstance(args, dict):
            return _tool_error(
                tool_name,
                f"Error calling tool '{tool_name}': arguments must be a JSON"
                " object",
            )
        logger.debug("Calling calculator MCP tool %s with %s", tool_name, args)
        try:
            result = await self._calc.call_tool(tool_name, args)
        except ToolError as error:
            return _tool_error(tool_name, str(error))
        logger.debug(
            "Calculator MCP tool %s result:\n%s",
            tool_name,
            json.dumps(result.structured_content, indent=2),
        )
        return str(result.data)

    async def _run_chat(
        self, llm: ChatCompletionClient, user_prompt: str
    ) -> str:
        """Run the agent loop against the Chat Completions API.

        Sends the user prompt to the LLM and dispatches any tool
        calls to the calculator MCP server until the LLM produces
        a final text response.

        Args:
            llm: The Chat Completions client.
            user_prompt: The math question from the user.

        Returns:
            The final text response from the LLM.

        Raises:
            TokenLimitError: If the token limit is reached.
            ContentFilterError: If the content is blocked by a safety
                filter.
            ValueError: If the LLM returns an unknown finish
                reason.
        """
        logger.debug("Starting AI LLM agent loop (chat completions)")
        history: list[Any] = [
            {"role": "system", "content": self._system_instructions}
        ]
        history.append({"role": "user", "content": user_prompt})
        logger.debug("Sending user prompt: %s", user_prompt)

        # -------------------------
        # Agent Loop
        # -------------------------
        logger.debug("=== >>> START AGENT LOOP")
        while True:
            response: ChatCompletion = await llm.create_response(history)
            llm_msg: ChatCompletionMessage = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
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

            logger.debug("LLM finish_reason: %s", finish_reason)
            match finish_reason:
                case "stop":
                    logger.info(
                        "=== >>> LLM TASK COMPLETED response: %s",
                        llm_msg.content,
                    )
                    break

                case "length":
                    error = "Token limit reached."
                    logger.error(error)
                    raise TokenLimitError(error)

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
                        result = await self._call_tool(tool_name, fn.arguments)
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
                    logger.error(error)
                    raise ContentFilterError(error)

                case _:
                    error = f"Non-supported finish_reason: {finish_reason}"
                    logger.error(error)
                    raise ValueError(error)

        logger.info("END AGENT LOOP <<< ===")
        return llm_msg.content or ""

    async def _run_responses(
        self,
        llm: ResponsesClient,
        user_prompt: str,
        display_reasoning: bool = True,
    ) -> str:
        """Run the agent loop against the Responses API.

        Sends the user prompt to the LLM and dispatches any
        ``function_call`` items to the calculator MCP server until the
        LLM produces a final text response.

        When the API server does not store responses (``stateful`` is
        ``False``), every output Item is echoed back as input on the
        next turn.  When it does, the next turn sends only the tool
        outputs and continues the stored response with
        ``previous_response_id``.

        Args:
            llm: The Responses API client.
            user_prompt: The math question from the user.
            display_reasoning: Include the reasoning section.

        Returns:
            The reasoning text from every turn and the final response,
            as labeled sections, or only the final response text when
            ``display_reasoning`` is ``False``.

        Raises:
            TokenLimitError: If the token limit is reached.
            ContentFilterError: If the content is blocked by a safety
                filter.
            LLMRequestFailedError: If the LLM reports the response as
                failed.
            ValueError: If the LLM returns an unknown response status
                or an unknown incomplete reason.
        """
        logger.info("Starting AI LLM agent loop using the Responses API")
        # The system prompt is sent as the top-level `instructions`
        # parameter, so it is not part of the input items.
        input_items: list[Any] = [{"role": "user", "content": user_prompt}]
        previous_response_id: str | None = None
        # Reasoning collected from every turn, for the formatted answer.
        reasoning: list[str] = []
        logger.debug("Sending user prompt: %s", user_prompt)

        # -------------------------
        # Agent Loop
        # -------------------------
        logger.info("=== >>> START AGENT LOOP")
        while True:
            response: Response = await llm.create_response(
                input_items, self._system_instructions, previous_response_id
            )
            logger.debug("LLM response status: %s", response.status)
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

            match response.status:
                case "completed":
                    reasoning.extend(_reasoning_texts(response))

                    # check if the LLM is asking us to run any tool
                    tool_calls = [
                        item
                        for item in response.output
                        if isinstance(item, ResponseFunctionToolCall)
                    ]

                    if tool_calls:
                        logger.info(
                            "LLM is asking us to call tool(s): %s", tool_calls
                        )
                    else:
                        logger.info(
                            "=== >>> LLM TASK COMPLETED response: %s",
                            response.output_text,
                        )
                        break

                    tool_outputs: list[Any] = []
                    for tool_call in tool_calls:
                        logger.debug(
                            "Calling call_id: %s, tool_name: %s",
                            tool_call.call_id,
                            tool_call.name,
                        )
                        result = await self._call_tool(
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
                    input_items, previous_response_id = _next_turn_input(
                        llm.stateful, input_items, response, tool_outputs
                    )
                    continue

                case "incomplete":
                    details = response.incomplete_details
                    reason = details.reason if details is not None else None
                    if reason == "max_output_tokens":
                        error = "Token limit reached."
                        logger.error(error)
                        raise TokenLimitError(error)
                    if reason == "content_filter":
                        error = (
                            f"Content [{input_items}] blocked for safety "
                            f"reasons."
                        )
                        logger.error(error)
                        raise ContentFilterError(error)
                    error = f"Unknown incomplete reason: {reason}"
                    logger.error(error)
                    raise ValueError(error)

                case "failed":
                    err = response.error
                    detail = err.message if err is not None else "unknown error"
                    code = err.code if err is not None else None
                    error = f"LLM request failed: {detail} (code={code})"
                    logger.error(error)
                    raise LLMRequestFailedError(error, code)

                case _:
                    # this project only supports regular create call without
                    # background or streaming.  Therefore, other response
                    # status like "queued", "in_progress" are not supported.
                    error = (
                        f"Non-supported response status:" f" {response.status}"
                    )
                    logger.error(error)
                    raise ValueError(error)

        logger.info("END AGENT LOOP <<< ===")
        if not display_reasoning:
            return response.output_text.strip()
        return _format_answer(reasoning, response.output_text)
