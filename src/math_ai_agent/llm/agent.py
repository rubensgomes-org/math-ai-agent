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

"""Agent loops orchestrating the LLM and the calculator MCP server.

Provides the ``agent_loop`` function, which dispatches to the
matching agent loop based on the ``llm.api_style`` setting in
``config.yaml`` and orchestrates a multi-turn conversation between
the LLM and the calculator MCP server.

The LLM transports themselves live in
:mod:`math_ai_agent.llm.client`; this module owns the system
prompt, the control flow, and the tool dispatch.
"""

import json
import logging
from typing import Any

from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.responses import Response, ResponseFunctionToolCall

from math_ai_agent.config.config import (
    configure_logging,
    get_api_key,
    get_api_style,
    get_model,
    get_model_base_url,
)
from math_ai_agent.llm.client import ChatCompletionClient, ResponsesClient
from math_ai_agent.mcp.calc_client import call_tool, get_calc_mcp_tools

configure_logging()
logger = logging.getLogger(__name__)

# Initial text to provide to the LLM context.
_SYSTEM_INSTRUCTIONS = (
    "You are a careful math assistant tutor helping solve math"
    " problems. Always write a short plan first. Do NOT do"
    " arithmetic in your head. For every math operation, request"
    " a tool call to the calculator. After tool results, continue."
    " Provide final answer with explanation."
    " Respond in plain text only. Do NOT use LaTeX, Markdown, or"
    " any other special formatting: no backslashes, no asterisks,"
    " no dollar-sign or parenthesis math delimiters. Write math"
    " inline, like 4 x 3 = 12. Your answer is shown in a plain"
    " text box that cannot render formatting."
)


# -------------------------------------------------
# Agent loops
# -------------------------------------------------
async def _chat_agent_loop(user_prompt: str) -> str:
    """Run the agent loop against the Chat Completions API.

    Discovers MCP tools, sends the user prompt to the LLM, and
    dispatches any tool calls to the calculator MCP server
    until the LLM produces a final text response.

    Args:
        user_prompt: The math question from the user.

    Returns:
        The final text response from the LLM.

    Raises:
        RuntimeError: If the configured API key environment
            variable is not set, the token limit is reached, or
            the content is blocked by a safety filter.
        ValueError: If the LLM returns an unknown finish
            reason.
    """
    logger.debug("Starting AI LLM agent loop (chat completions)")
    history: list[Any] = [{"role": "system", "content": _SYSTEM_INSTRUCTIONS}]
    tools = await get_calc_mcp_tools("chat")
    llm = ChatCompletionClient(
        get_api_key(),
        get_model_base_url(),
        get_model(),
        tools,
    )

    history.append({"role": "user", "content": user_prompt})
    logger.debug("Sending user prompt: %s", user_prompt)
    logger.debug("Starting agent loop.")

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
                    result = await call_tool(tool_name, args)
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


async def _responses_agent_loop(user_prompt: str) -> str:
    """Run the agent loop against the Responses API.

    Discovers MCP tools, sends the user prompt to the LLM, and
    dispatches any ``function_call`` items to the calculator MCP
    server until the LLM produces a final text response.

    The loop is stateless: ``store`` is ``False`` and every output
    Item is echoed back as input on the next turn, so no
    ``previous_response_id`` is used.

    Args:
        user_prompt: The math question from the user.

    Returns:
        The final text response from the LLM.

    Raises:
        RuntimeError: If the configured API key environment
            variable is not set, the token limit is reached, the
            content is blocked by a safety filter, or the request
            fails.
        ValueError: If the LLM returns an unknown response status
            or an unknown incomplete reason.
    """
    logger.debug("Starting AI LLM agent loop (responses)")
    tools = await get_calc_mcp_tools("responses")
    llm = ResponsesClient(
        get_api_key(),
        get_model_base_url(),
        get_model(),
        tools,
    )

    # The system prompt is sent as the top-level `instructions`
    # parameter, so it is not part of the input items.
    history: list[Any] = [{"role": "user", "content": user_prompt}]
    logger.debug("Sending user prompt: %s", user_prompt)
    logger.debug("Starting agent loop.")

    final_text = ""

    # -------------------------
    # Agent Loop
    # -------------------------
    while True:
        response: Response = await llm.create_response(
            history, _SYSTEM_INSTRUCTIONS
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
            logger.debug("No token usage reported in the response.")

        match response.status:
            case "completed":
                tool_calls = [
                    item
                    for item in response.output
                    if isinstance(item, ResponseFunctionToolCall)
                ]
                if not tool_calls:
                    final_text = response.output_text
                    logger.info(
                        "Assistant (LLM) response (status=%s): %s",
                        response.status,
                        final_text,
                    )
                    break

                # Stateless replay: echo every output Item back as
                # input so the model keeps its reasoning context.
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
                    result = await call_tool(tool_call.name, args)
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
                raise ValueError(error)

    logger.debug("Returning final response message from LLM.")
    return final_text or ""


async def agent_loop(user_prompt: str) -> str:
    """Run the agent loop using the configured OpenAI API style.

    Dispatches to the Responses API loop or the Chat Completions
    loop based on the ``llm.api_style`` setting in ``config.yaml``.

    Args:
        user_prompt: The math question from the user.

    Returns:
        The final text response from the LLM.
    """
    api_style = get_api_style()
    if api_style == "responses":
        return await _responses_agent_loop(user_prompt)
    return await _chat_agent_loop(user_prompt)
