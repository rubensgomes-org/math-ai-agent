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

from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.responses import Response, ResponseFunctionToolCall

from math_ai_agent.config.config import get_api_key, get_config
from math_ai_agent.llm.client import ChatCompletionClient, ResponsesClient
from math_ai_agent.mcp.calc_connection import CalcMCPConnection

logger = logging.getLogger(__name__)


class AgentBusyError(RuntimeError):
    """Raised when the maximum number of prompts is already running."""


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
        logger.info("Creating agent (api_style=%s)", llm_config.api_style)
        llm: ChatCompletionClient | ResponsesClient
        if llm_config.api_style == "responses":
            llm = ResponsesClient(
                get_api_key(),
                llm_config.model_base_url,
                llm_config.model,
                await calc.to_responses_tools(),
                llm_config.timeout_seconds,
            )
        else:
            llm = ChatCompletionClient(
                get_api_key(),
                llm_config.model_base_url,
                llm_config.model,
                await calc.to_openai_tools(),
                llm_config.timeout_seconds,
            )
        return cls(
            calc,
            llm,
            llm_config.system_instructions,
            llm_config.max_concurrent_prompts,
        )

    async def run(self, user_prompt: str) -> str:
        """Run the agent loop for the configured OpenAI API style.

        Args:
            user_prompt: The math question from the user.

        Returns:
            The final text response from the LLM.

        Raises:
            AgentBusyError: If ``max_concurrent_prompts`` prompts are
                already running.
        """
        if self._prompt_slots.locked():
            logger.warning("Rejecting prompt: all prompt slots are in use")
            raise AgentBusyError("Too many prompts are running")
        async with self._prompt_slots:
            if isinstance(self._llm, ResponsesClient):
                return await self._run_responses(self._llm, user_prompt)
            return await self._run_chat(self._llm, user_prompt)

    async def _call_tool(self, tool_name: str, args: dict) -> str:
        """Call a calculator MCP tool and return its result as text."""
        logger.debug("Calling calculator MCP tool %s with %s", tool_name, args)
        result = await self._calc.call_tool(tool_name, args)
        logger.debug(
            "Tool %s result:\n%s",
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
            RuntimeError: If the token limit is reached or the
                content is blocked by a safety filter.
            ValueError: If the LLM returns an unknown finish
                reason.
        """
        logger.debug("Starting AI LLM agent loop (chat completions)")
        history: list[Any] = [
            {"role": "system", "content": self._system_instructions}
        ]
        history.append({"role": "user", "content": user_prompt})
        logger.debug("Sending user prompt: %s", user_prompt)

        logger.debug("==============================================")
        logger.debug("========== >>> START AGENT LOOP <<< ==========")

        # -------------------------
        # Agent Loop
        # -------------------------
        while True:
            response: ChatCompletion = await llm.create_response(history)
            llm_msg: ChatCompletionMessage = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            usage = response.usage
            if usage is not None:
                logger.debug(
                    "Token usage in the current request:"
                    " prompt=%d completion=%d total=%d",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                )
            else:
                logger.debug("No token usage reported in the response.")

            logger.debug("finish_reason: %s", finish_reason)
            match finish_reason:
                case "stop":
                    logger.info("Assistant (LLM) response: %s", llm_msg.content)
                    break

                case "length":
                    error = "Token limit reached."
                    logger.error(error)
                    raise RuntimeError(error)

                case "tool_calls":
                    history.append(llm_msg)
                    assert llm_msg.tool_calls is not None
                    for tool_call in llm_msg.tool_calls:
                        fn = tool_call.function  # type: ignore[union-attr]
                        tool_name = fn.name
                        tool_call_id = tool_call.id
                        args = json.loads(fn.arguments)
                        logger.debug(
                            "Calling tool_call_id: %s, tool_name: %s",
                            tool_call_id,
                            tool_name,
                        )
                        result = await self._call_tool(tool_name, args)
                        history.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": result,
                            }
                        )
                    continue

                case "content_filter":
                    error = (
                        f"The content [{history}] was blocked"
                        " for safety reasons."
                    )
                    logger.error(error)
                    raise RuntimeError(error)

                case None:
                    # Happens during streaming before final chunk
                    logger.debug("Streaming before final chunk. Continue ...")
                    continue

                case _:
                    error = f"Unknown finish_reason: {finish_reason}"
                    logger.error(error)
                    raise ValueError(error)

        logger.debug("Returning final response message from LLM.")
        return llm_msg.content or ""

    async def _run_responses(
        self, llm: ResponsesClient, user_prompt: str
    ) -> str:
        """Run the agent loop against the Responses API.

        Sends the user prompt to the LLM and dispatches any
        ``function_call`` items to the calculator MCP server until the
        LLM produces a final text response.

        The loop is stateless: ``store`` is ``False`` and every output
        Item is echoed back as input on the next turn, so no
        ``previous_response_id`` is used.

        Args:
            llm: The Responses API client.
            user_prompt: The math question from the user.

        Returns:
            The final text response from the LLM.

        Raises:
            RuntimeError: If the token limit is reached, the content
                is blocked by a safety filter, or the request fails.
            ValueError: If the LLM returns an unknown response status
                or an unknown incomplete reason.
        """
        logger.debug("Starting AI LLM agent loop (responses)")
        # The system prompt is sent as the top-level `instructions`
        # parameter, so it is not part of the input items.
        history: list[Any] = [{"role": "user", "content": user_prompt}]
        logger.debug("Sending user prompt: %s", user_prompt)

        logger.debug("==============================================")
        logger.debug("========== >>> START AGENT LOOP <<< ==========")

        # -------------------------
        # Agent Loop
        # -------------------------
        while True:
            response: Response = await llm.create_response(
                history, self._system_instructions
            )
            logger.debug("LLM response status: %s", response.status)
            usage = response.usage
            if usage is not None:
                logger.debug(
                    "Token usage in the current request:"
                    " input=%d output=%d total=%d",
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.total_tokens,
                )
            else:
                logger.warning("No token usage reported in the response.")

            logger.debug("response.status: %s", response.status)
            match response.status:
                case "completed":
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
                            "LLM is done with final response (status=%s): %s",
                            response.status,
                            response.output_text,
                        )
                        break

                    # ---------- >>> STATELESS REPLAY <<< ---------
                    # Every output item is added back to history, so the
                    # model keeps its context. This is required because
                    # the model is Stateless.
                    logger.debug(
                        "STATELESS REPLAY: echo every output Item back "
                        "as input so the model keeps its reasoning "
                        "context."
                    )
                    history.extend(
                        item.model_dump(exclude_none=True)
                        for item in response.output
                    )
                    for tool_call in tool_calls:
                        args = json.loads(tool_call.arguments)
                        logger.debug(
                            "Calling call_id: %s, tool_name: %s",
                            tool_call.call_id,
                            tool_call.name,
                        )
                        result = await self._call_tool(tool_call.name, args)
                        history.append(
                            {
                                "type": "function_call_output",
                                "call_id": tool_call.call_id,
                                "output": result,
                            }
                        )
                    continue

                case "incomplete":
                    details = response.incomplete_details
                    reason = details.reason if details is not None else None
                    if reason == "max_output_tokens":
                        error = (
                            "Token limit reached."
                            f" (status={response.status},"
                            f" reason={reason})"
                        )
                        logger.error(error)
                        raise RuntimeError(error)
                    if reason == "content_filter":
                        error = (
                            f"The content [{history}] was blocked"
                            " for safety reasons."
                            f" (status={response.status}, reason={reason})"
                        )
                        logger.error(error)
                        raise RuntimeError(error)
                    error = (
                        f"Unknown incomplete reason: {reason}"
                        f" (status={response.status})"
                    )
                    logger.error(error)
                    raise ValueError(error)

                case "failed":
                    err = response.error
                    detail = err.message if err is not None else "unknown error"
                    error = (
                        f"LLM request failed: {detail}"
                        f" (status={response.status})"
                    )
                    logger.error(error)
                    logger.debug(
                        "====== >>> END AGENT LOOP W/FAILURE <<< ======"
                    )
                    logger.debug(
                        "=============================================="
                    )
                    raise RuntimeError(error)

                case "queued" | "in_progress":
                    # Response is not final yet. Poll again.
                    logger.debug(
                        "Response not final yet (status=%s). Continue ...",
                        response.status,
                    )
                    continue

                case _:
                    error = f"Unknown response status: {response.status}"
                    logger.error(error)
                    logger.debug(
                        "====== >>> END AGENT LOOP W/FAILURE <<< ======"
                    )
                    logger.debug(
                        "=============================================="
                    )
                    raise ValueError(error)

        logger.debug("Returning final response message from LLM.")
        logger.debug("=========== >>> END AGENT LOOP <<< ===========")
        logger.debug("==============================================")
        return response.output_text or ""
