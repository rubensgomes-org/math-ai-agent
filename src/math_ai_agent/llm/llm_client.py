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

"""Abstract LLM client around the OpenAI SDK.

``LLMClient`` validates parameters, builds the underlying
``AsyncOpenAI`` client, and declares the methods each API client
implements.  Its concrete clients live in
:mod:`math_ai_agent.llm.chat_completions_client` and
:mod:`math_ai_agent.llm.responses_client`.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import mcp_types
from openai import AsyncOpenAI

from math_ai_agent.config.config import (
    DEFAULT_LLM_TIMEOUT_SECONDS,
    get_config,
)

logger = logging.getLogger(__name__)


class LLMClient[ResponseT](ABC):
    """Shared validation and ``AsyncOpenAI`` construction.

    Each instance holds its own ``AsyncOpenAI`` client, model name,
    tool definitions, and the ``llm.system_instructions`` from
    ``config.yaml``.  ``ResponseT`` is the SDK response type returned
    by the concrete client's API.
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

        ``api_key``, ``base_url``, ``model`` and ``tools`` must be
        non-empty.

        Args:
            api_key: API key for the OpenAI-compatible service.
            base_url: Base URL of the inference endpoint.
            model: Model identifier to use for completions.
            tools: Tool definitions in the format matching this client.
            timeout_seconds: Seconds to wait for each LLM response.
            temperature: Sampling temperature, or ``None`` to use the
                provider default.

        Raises:
            ValueError: If a required parameter is empty or ``None``.
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
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )
        self.tools = tools
        self.model = model
        self.temperature = temperature
        self.system_instructions = get_config().llm.system_instructions

    async def close(self) -> None:
        """Close the underlying ``AsyncOpenAI`` HTTP connections."""
        logger.debug("Closing LLM %s", type(self).__name__)
        await self.openai_client.close()

    @staticmethod
    @abstractmethod
    def format_tools(tools: list[mcp_types.Tool]) -> list[dict]:
        """Format MCP tools definitions for this client's API.

        Args:
            tools: The MCP server's tools.

        Returns:
            A list of tool dicts in this client's API format.
        """

    @abstractmethod
    async def create_response(self, history: list[Any]) -> ResponseT:
        """Send the conversation history and return the response.

        Args:
            history: Conversation history in this client's API format.

        Returns:
            The response from the configured model.
        """

    @staticmethod
    @abstractmethod
    def report_usage(response: ResponseT) -> None:
        """Log the token usage reported in ``response``.

        Args:
            response: The response returned by the model.
        """
