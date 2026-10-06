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

"""Abstract client for OpenAI-compatible LLM APIs."""

import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Self

from openai import AsyncOpenAI

from math_ai_agent.config.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient[ResponseT](ABC):
    """Abstract type w/common interface to models using OpenAI APIs"""

    def __init__(self, llm_config: LLMConfig, tools: list[dict]) -> None:
        if not tools:
            raise ValueError("tools must not be empty")
        logger.info(
            "Initializing LLM=%s with base_url=%s, model=%s, tool_count=%d",
            type(self).__name__,
            llm_config.model_base_url,
            llm_config.model,
            len(tools),
        )
        self.openai_client = AsyncOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.model_base_url,
            timeout=llm_config.timeout_seconds,
        )
        self.tools = tools
        self.model = llm_config.model
        self.temperature = llm_config.temperature
        self.system_instructions = llm_config.system_instructions

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the underlying ``AsyncOpenAI`` HTTP connections."""
        logger.debug("Closing LLM %s", type(self).__name__)
        await self.openai_client.close()

    @abstractmethod
    async def prompt(self, history: list[Any]) -> ResponseT: ...

    @staticmethod
    @abstractmethod
    def log_token_usage(response: ResponseT) -> None: ...
