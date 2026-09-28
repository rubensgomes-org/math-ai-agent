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

"""LLM client wrappers around the OpenAI SDK.

Provides two thin transports over ``AsyncOpenAI``, sharing the
``_BaseLLMClient`` base that validates parameters and builds the
underlying client:

* ``ResponsesClient`` -- uses the Responses API
  (``POST /v1/responses``), the primary OpenAI API.
* ``ChatCompletionClient`` -- uses the legacy Chat Completions API
  (``POST /v1/chat/completions``).

These classes know only how to talk to the inference endpoint.  The
system prompt, the multi-turn control flow, and the calculator MCP
tool dispatch all live in :mod:`math_ai_agent.llm.agent`.
"""

import json
import logging
from typing import Any, cast

from openai import AsyncOpenAI, omit
from openai.types.chat import ChatCompletion
from openai.types.responses import Response

from math_ai_agent.config.config import (
    DEFAULT_LLM_TIMEOUT_SECONDS,
    ReasoningSummary,
)

logger = logging.getLogger(__name__)

TOOLS_REMOVED_FROM_LOGS = "!!!TOOLS TOO LONG AND REMOVED FROM LOGS!!!"


def _omit_if_none(value: Any) -> Any:
    """Return ``omit``, which leaves the field out of the request, for
    ``None``; otherwise return ``value``."""
    return omit if value is None else value


def _to_json(value: Any) -> str:
    """Format a request payload as indented JSON for logging.

    SDK objects, such as ``ChatCompletionMessage``, are converted with
    ``model_dump``; anything else that JSON cannot encode uses ``str``.
    """

    def _encode(item: Any) -> Any:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return str(item)

    return json.dumps(value, indent=2, default=_encode)


class _BaseLLMClient:
    """Shared validation and ``AsyncOpenAI`` construction.

    Each instance holds its own ``AsyncOpenAI`` client,
    model name, and tool definitions.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        tools: list[dict],
        timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS,
        temperature: float | None = None,
    ) -> None:
        """Create an ``AsyncOpenAI`` client for the LLM.

        All parameters are validated and must be non-empty.

        Args:
            api_key: API key for the OpenAI-compatible service.
            base_url: Base URL of the inference endpoint.
            model: Model identifier to use for completions.
            tools: Tool definitions in the format matching this client.
            timeout_seconds: Seconds to wait for each LLM response.
            temperature: Sampling temperature, or ``None`` to use the
                provider default.

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
        if not tools:
            logger.error("tools is empty or None")
            raise ValueError("tools must not be empty")
        logger.info(
            "Initializing LLM %s with base_url=%s, model=%s, tool_count=%d",
            type(self).__name__,
            base_url,
            model,
            len(tools),
        )
        # logger.debug(
        #     "Tool definitions being set on the LLM client:\n%s",
        #     json.dumps(tools, indent=2),
        # )
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )
        self.tools = tools
        self.model = model
        self.temperature = temperature


class ChatCompletionClient(_BaseLLMClient):
    """Async OpenAI client for the legacy Chat Completions API."""

    async def create_response(
        self, history: list[dict[str, Any]]
    ) -> ChatCompletion:
        """Send the conversation history and return the response.

        Args:
            history: Conversation history as a list of
                role/content dicts.

        Returns:
            The ``ChatCompletion`` from the configured model.
        """
        logger.debug(
            "LLM client sending %d message(s) to model %s\n"
            "Messages:\n%s\n"
            "Tools:\n%s",
            len(history),
            self.model,
            _to_json(history),
            _to_json(self.tools),
        )
        # ``create()`` is overloaded on ``stream``; because the
        # arguments below are loosely typed, some type checkers widen
        # the result to include the streaming variant.  This call never
        # streams, so narrow it back to ``ChatCompletion``.
        response = cast(
            ChatCompletion,
            await self.openai_client.chat.completions.create(
                model=self.model,
                messages=history,  # type: ignore[arg-type]
                tools=self.tools,  # type: ignore[arg-type]
                # See the note on ``store`` in ResponsesClient.  The
                # Chat Completions default is already ``false``, but
                # omitting the field is not reliably the same as
                # sending it: OpenAI accounts carry a separate
                # data-retention setting that can enable storage when
                # the parameter is absent.  Sending it makes the
                # intent explicit rather than dependent on how the
                # account happens to be configured.
                store=False,
                temperature=_omit_if_none(self.temperature),
            ),
        )
        logger.debug(
            "LLM response:\n%s",
            json.dumps(response.model_dump(), indent=2),
        )
        return response


class ResponsesClient(_BaseLLMClient):
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
        """Create the client; see ``_BaseLLMClient`` for the other args.

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

    async def create_response(
        self,
        input_items: list[Any],
        instructions: str,
        previous_response_id: str | None = None,
    ) -> Response:
        """Send input items and return the response.

        Args:
            input_items: Responses API input Items: the whole
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
        logger.info(
            "LLM client sending %d input item(s) to model %s"
            " (previous_response_id=%s)\n"
            "System instructions:\n%s\n"
            "Input items:\n%s\n"
            "Tools:\n%s",
            len(input_items),
            self.model,
            previous_response_id,
            instructions,
            _to_json(input_items),
            TOOLS_REMOVED_FROM_LOGS,
            # _to_json(self.tools),
        )
        # See the note in ChatCompletionClient.create_response: this
        # call never streams, so narrow it back to ``Response``.
        response = cast(
            Response,
            await self.openai_client.responses.create(
                model=self.model,
                input=input_items,  # type: ignore[arg-type]
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
                temperature=_omit_if_none(self.temperature),
            ),
        )
        logger.debug(
            "LLM response:\n%s",
            json.dumps(
                {**response.model_dump(), "tools": TOOLS_REMOVED_FROM_LOGS},
                indent=2,
            ),
        )
        return response
