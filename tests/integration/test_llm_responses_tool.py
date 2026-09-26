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

"""Integration test for LLM tool calling via the Responses API.

Drives the real ``Agent`` from ``math_ai_agent.llm.agent`` against
the configured LLM endpoint and the calculator MCP server, so the loop
under test is the same code the FastAPI app runs.  Reads the math
prompt from the command line, or interactively when no argument is
given.  Run standalone with::

    poetry run python tests/integration/test_llm_responses_tool.py
    poetry run python tests/integration/test_llm_responses_tool.py "4+4*3?"

``llm.api_style`` is forced to ``responses``, so the configured
endpoint must support the Responses API (``POST /v1/responses``).
"""

import asyncio
import logging
import sys

from math_ai_agent.config.config import configure_logging, get_config
from math_ai_agent.llm.agent import Agent
from math_ai_agent.mcp.calc_connection import CalcMCPConnection

logger = logging.getLogger(__name__)


async def show_tools(calc: CalcMCPConnection) -> None:
    """Log the Responses-format tool definitions from the MCP server."""
    tools = await calc.to_responses_tools()
    logger.info("Discovered %d MCP tool(s) in Responses format", len(tools))
    for tool in tools:
        logger.info("  - %s: %s", tool["name"], tool.get("description"))


async def main() -> None:
    """Entry point for the Responses API integration test."""
    logger.info("Running integration test for ResponsesClient")
    get_config().llm.api_style = "responses"
    async with CalcMCPConnection() as calc:
        await show_tools(calc)
        agent = await Agent.create(calc)
        user_input = (
            " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("User: ")
        )
        logger.debug("Sending user prompt: %s", user_input)
        logger.info("Assistant: %s", await agent.run(user_input))
    logger.info("Integration test completed")


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
