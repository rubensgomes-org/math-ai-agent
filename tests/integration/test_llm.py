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

"""Integration test for the ChatCompletionClient LLM wrapper.

Connects to the calculator MCP server, discovers tools, then sends
a math prompt to the LLM via ``ChatCompletionClient``.  Run standalone with::

    poetry run python tests/integration/test_llm.py
"""

import asyncio
import logging

from math_ai_agent.config.config import (
    configure_logging,
    get_api_key,
    get_model,
    get_model_base_url,
)
from math_ai_agent.llm.client import ChatCompletionClient
from math_ai_agent.mcp.calc_client import CalcMCPClient

configure_logging()
logger = logging.getLogger(__name__)

# LLM endpoint, model, and API key env var come from config.yaml.

_SYSTEM_INSTRUCTIONS = """
You are a careful math assistant tutor helping solve math problems. Always
write a short plan first. Do NOT do arithmetic in your head. For every
math operation, request a tool call to the calculator. After tool results,
continue. Provide final answer with explanation.
"""


async def get_mcp_tools() -> list[dict]:
    """Connect to the Calculator MCP server and list the tools.

    Returns:
        OpenAI-format tool definitions discovered from the
        MCP server.
    """
    logger.info("Connecting to Calculator MCP server")
    async with CalcMCPClient() as calcmcp_client:
        tools = await calcmcp_client.to_openai_tools()
        logger.info("Discovered %d MCP tool(s)", len(tools))
        return tools


async def prompt_llm() -> None:
    """Discover MCP tools and send a single math prompt.

    Connects to the calculator MCP server to discover tools,
    builds a message history with system instructions and a
    user prompt, then sends it to the LLM.
    """
    logger.info("Starting LLM prompt test")
    messages = [{"role": "system", "content": _SYSTEM_INSTRUCTIONS}]
    tools = await get_mcp_tools()
    llm = ChatCompletionClient(
        get_api_key(),
        get_model_base_url(),
        get_model(),
        tools,
    )
    messages.append({"role": "user", "content": "4+4?"})
    logger.debug("Sending prompt: %s", messages[-1]["content"])
    response = await llm.create_response(messages)
    logger.info("Assistant: %s", response.choices[0].message.content)


async def main() -> None:
    """Entry point for the LLM integration test."""
    logger.info("Running integration test for ChatCompletionClient")
    await prompt_llm()
    logger.info("Integration test completed")


if __name__ == "__main__":
    asyncio.run(main())
