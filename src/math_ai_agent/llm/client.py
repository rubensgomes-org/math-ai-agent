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

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.responses import Response

from math_ai_agent.config.config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


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
    ) -> None:
        """Create an ``AsyncOpenAI`` client for the LLM.

        All parameters are validated and must be non-empty.

        Args:
            api_key: API key for the OpenAI-compatible service.
            base_url: Base URL of the inference endpoint.
            model: Model identifier to use for completions.
            tools: Tool definitions in the format matching this client.

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
            "Initializing %s with base_url=%s, model=%s, tool_count=%d",
            type(self).__name__,
            base_url,
            model,
            len(tools),
        )
        logger.debug(
            "Tool definitions:\n%s",
            json.dumps(tools, indent=2),
        )
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.tools = tools
        self.model = model


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
            "Sending %d message(s) to model %s",
            len(history),
            self.model,
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
    item, and ``store`` is always ``False``: the conversation is
    replayed in full on every turn.
    """

    async def create_response(
        self, history: list[Any], instructions: str
    ) -> Response:
        """Send the conversation history and return the response.

        Args:
            history: Conversation history as a list of Responses
                API input Items.
            instructions: System prompt sent as the top-level
                ``instructions`` parameter.

        Returns:
            The ``Response`` from the configured model.
        """
        logger.debug(
            "Sending %d input item(s) to model %s",
            len(history),
            self.model,
        )
        # See the note in ChatCompletionClient.create_response: this
        # call never streams, so narrow it back to ``Response``.
        response = cast(
            Response,
            await self.openai_client.responses.create(
                model=self.model,
                input=history,  # type: ignore[arg-type]
                tools=self.tools,  # type: ignore[arg-type]
                instructions=instructions,
                # ``store`` controls server-side retention of the
                # request and response.  Unlike Chat Completions, the
                # Responses API stores by default, so it must be
                # disabled explicitly.  Two provider notes:
                #
                # * OpenRouter rejects ``store=True`` (and any
                #   non-null ``previous_response_id``) with HTTP 400 --
                #   its Responses API is strictly stateless.  Sending
                #   ``False`` is what keeps this client compatible.
                # * OpenAI honours ``False`` per the API reference, but
                #   accounts also carry a data-retention setting that
                #   governs what appears in the org dashboard.  Treat
                #   this flag as controlling the API's own storage, not
                #   as a guarantee about org-level logging.
                store=False,
            ),
        )
        logger.debug(
            "LLM response:\n%s",
            json.dumps(response.model_dump(), indent=2),
        )
        return response
