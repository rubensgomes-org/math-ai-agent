# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review
# and refinement have occurred, users should be aware that the output may
# contain inaccuracies, errors, or security vulnerabilities
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
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.


"""LLM client for the OpenAI Responses API (``POST /v1/responses``).

The system prompt, the multi-turn control flow, and the calculator MCP
tool dispatch all live in :mod:`math_ai_agent.agent.agent`.
"""

import logging
from typing import Any, cast

import mcp_types
from openai import omit
from openai.types.responses import Response

from math_ai_agent.config.config import (
    DEFAULT_LLM_TIMEOUT_SECONDS,
    ReasoningSummary,
)
from math_ai_agent.llm.llm_client import LLMClient
from math_ai_agent.llm.utils import (
    function_definition,
    omit_if_none,
    to_json,
)

logger = logging.getLogger(__name__)


class ResponsesClient(LLMClient):
    """Async OpenAI client for the Responses API.

    The system prompt is supplied by the caller and sent as the
    top-level ``instructions`` parameter rather than as a message
    item.  When ``stateful`` is ``False``, ``store`` is ``False`` and
    the caller replays the whole conversation on every turn.  When it
    is ``True``, responses are stored and continued with
    ``previous_response_id``, which not every provider supports.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        tools: list[dict],
        timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS,
        temperature: float | None = None,
        stateful: bool = False,
        reasoning_summary: ReasoningSummary | None = None,
    ) -> None:
        """Create the client; see ``LLMClient`` for the other args.

        Args:
            stateful: Store responses on the server so turns can be
                continued with ``previous_response_id``.
            reasoning_summary: Reasoning summary detail to request, or
                ``None`` to not request one.
        """
        super().__init__(
            api_key, base_url, model, tools, timeout_seconds, temperature
        )
        self.stateful = stateful
        self.reasoning_summary = reasoning_summary

    @staticmethod
    def format_tools(tools: list[mcp_types.Tool]) -> list[dict]:
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

    async def create_response(
        self,
        history: list[Any],
        instructions: str,
        previous_response_id: str | None = None,
    ) -> Response:
        """Send input items and return the response.

        Args:
            history: Responses API input Items: the whole
                conversation when stateless, or only the new items when
                continuing ``previous_response_id``.
            instructions: System prompt sent as the top-level
                ``instructions`` parameter.  The API does not carry it
                over from a previous response.
            previous_response_id: ID of the stored response to
                continue, or ``None`` to start a new conversation.

        Returns:
            The ``Response`` from the configured model.
        """
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
            instructions,
            previous_response_id,
            to_json(history),
            to_json(self.tools),
        )
        # See the note in ChatCompletionsClient.create_response: this
        # call never streams, so narrow it back to ``Response``.
        response = cast(
            Response,
            await self.openai_client.responses.create(
                model=self.model,
                input=history,  # type: ignore[arg-type]
                # Models without reasoning may reject this field.
                reasoning=(
                    {"summary": self.reasoning_summary}
                    if self.reasoning_summary
                    else omit
                ),
                tools=self.tools,  # type: ignore[arg-type]
                instructions=instructions,
                # ``store`` controls server-side retention of the
                # request and response.  Unlike Chat Completions, the
                # Responses API is stateful by default (depending on
                # support by the LLM model), so it must be disabled
                # explicitly when stateless.  Provider notes:
                #
                # * OpenRouter rejects ``store=True`` (and any
                #   non-null ``previous_response_id``) with HTTP 400,
                #   and NVIDIA rejects ``previous_response_id`` with
                #   HTTP 501.  Both work only when stateless.
                store=self.stateful,
                # ``omit`` leaves the field out of the request.
                previous_response_id=previous_response_id or omit,
                temperature=omit_if_none(self.temperature),
            ),
        )
        logger.debug(
            "LLM response:\n%s",
            to_json(response),
        )
        return response

    @staticmethod
    def report_usage(response: Response) -> None:
        """Log the token usage reported in ``response``.

        Args:
            response: The ``Response`` returned by the model.
        """
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
