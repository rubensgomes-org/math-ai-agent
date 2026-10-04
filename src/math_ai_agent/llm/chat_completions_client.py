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

"""LLM client for the legacy OpenAI Chat Completions API
(``POST /v1/chat/completions``).

The system prompt, the multi-turn control flow, and the calculator MCP
tool dispatch all live in :mod:`math_ai_agent.llm.agent`.
"""

import logging
from typing import Any, cast

from openai.types.chat import ChatCompletion

from math_ai_agent.llm.llm_client import LLMClient
from math_ai_agent.llm.request_utils import omit_if_none, to_json

logger = logging.getLogger(__name__)


class ChatCompletionsClient(LLMClient):
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
            to_json(history),
            to_json(self.tools),
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
                temperature=omit_if_none(self.temperature),
            ),
        )
        logger.debug(
            "LLM response:\n%s",
            to_json(response),
        )
        return response

    @staticmethod
    def report_usage(response: ChatCompletion) -> None:
        """Log the token usage reported in ``response``.

        Args:
            response: The ``ChatCompletion`` returned by the model.
        """
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
