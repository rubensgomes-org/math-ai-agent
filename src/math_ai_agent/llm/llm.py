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

"""LLM client and agent loop for math tool-calling.

Provides the ``OpenAIClient`` class that wraps an
``AsyncOpenAI`` instance and sends chat completion requests
to the configured LLM model with tool definitions, and the
``agent_loop`` function that orchestrates a multi-turn
conversation between the LLM and the calculator MCP server.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage

from math_ai_agent.config.config import (
    configure_logging,
    get_api_key,
    get_model,
    get_model_base_url,
)
from math_ai_agent.mcp.calc_client import call_tool, get_mcp_tools

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


class OpenAIClient:
    """Async OpenAI client for LLM chat completions.

    Each instance holds its own ``AsyncOpenAI`` client,
    model name, and tool definitions.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        calcmcp_tools: list[dict],
    ) -> None:
        """Create an ``AsyncOpenAI`` client for chat completions.

        All parameters are validated and must be non-empty.

        Args:
            api_key: API key for the OpenAI-compatible service.
            base_url: Base URL of the inference endpoint.
            model: Model identifier to use for completions.
            calcmcp_tools: OpenAI-format tool definitions from
                the calculator MCP server.

        Raises:
            ValueError: If any parameter is empty or ``None``.
        """
        if not api_key:
            logger.error("api_key is empty or None")
            raise ValueError("api_key must not be empty")
        if not base_url:
            logger.error("base_url is empty or None")
            raise ValueError("base_url must not be empty")
        if not model:
            logger.error("model is empty or None")
            raise ValueError("model must not be empty")
        if not calcmcp_tools:
            logger.error("calcmcp_tools is empty or None")
            raise ValueError("calcmcp_tools must not be empty")
        logger.info(
            "Initializing OpenAIClient with "
            "base_url=%s, model=%s, tool_count=%d",
            base_url,
            model,
            len(calcmcp_tools),
        )
        logger.debug(
            "Tool definitions:\n%s",
            json.dumps(calcmcp_tools, indent=2),
        )
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.calcmcp_tools = calcmcp_tools
        self.model = model

    async def create_response(
        self, messages: list[dict[str, Any]]
    ) -> ChatCompletion:
        """Send messages to the LLM and return the response.

        Args:
            messages: Conversation history as a list of
                role/content dicts.

        Returns:
            The ``ChatCompletion`` from the configured model.
        """
        logger.debug(
            "Sending %d message(s) to model %s",
            len(messages),
            self.model,
        )
        response: ChatCompletion = (
            await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                tools=self.calcmcp_tools,  # type: ignore[arg-type]
            )
        )
        logger.debug(
            "LLM response:\n%s",
            json.dumps(response.model_dump(), indent=2),
        )
        return response


# -------------------------------------------------
# Agent loop
# -------------------------------------------------
async def agent_loop(user_prompt: str) -> str:
    """Run the interactive agent loop with LLM tool calling.

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
    logger.debug("Starting AI LLM agent loop")
    context: list[Any] = [{"role": "system", "content": _SYSTEM_INSTRUCTIONS}]
    tools = await get_mcp_tools()
    llm = OpenAIClient(
        get_api_key(),
        get_model_base_url(),
        get_model(),
        tools,
    )

    context.append({"role": "user", "content": user_prompt})
    logger.debug("Sending user prompt: %s", user_prompt)
    logger.debug("Starting agent loop.")

    # -------------------------
    # Agent Loop
    # -------------------------
    while True:
        response: ChatCompletion = await llm.create_response(context)
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
                context.append(llm_msg)
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
                    context.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result,
                        }
                    )
                continue

            case "content_filter":
                error = (
                    f"The content [{context}] was blocked"
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
