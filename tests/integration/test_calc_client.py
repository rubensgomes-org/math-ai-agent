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

"""Integration test client for the calculator MCP server.

Connects to the remote calculator MCP server, lists available tools,
and calls each one with sample arguments to verify end-to-end
connectivity.  Run standalone with::

    poetry run python tests/integration/test_calc_client.py
"""

import asyncio
import json
import logging

from math_ai_agent.mcp.calc_client import CalcMCPClient

logger = logging.getLogger(__name__)


_SAMPLE_ARGS: dict[str, dict[str, float | int]] = {
    "add": {"a": 2, "b": 3},
    "subtract": {"a": 10, "b": 4},
    "multiply": {"a": 3, "b": 7},
    "divide": {"a": 15, "b": 4},
    "power": {"a": 2, "b": 8},
    "nth_root": {"a": 27, "b": 3},
    "modulo": {"a": 17, "b": 5},
    "floor_divide": {"a": 17, "b": 5},
    "sqrt": {"a": 16},
    "absolute": {"a": -42},
    "floor": {"a": 3.7},
    "ceil": {"a": 3.2},
    "log10": {"a": 1000},
    "ln": {"a": 2.718281828},
    "exp": {"a": 1},
    "round_number": {"a": 3.14159, "decimals": 2},
}


async def run_client() -> None:
    """Connect to the MCP server, list and call each tool."""
    calcmcp_client = CalcMCPClient()

    async with calcmcp_client:
        openai_tools = await calcmcp_client.to_chat_completions_tools()
        print(f"Tools:\n{json.dumps(openai_tools, indent=2)}")
        tools = await calcmcp_client.list_tools()
        print(f"Connected — {len(tools)} tools available:\n")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
            args = _SAMPLE_ARGS.get(tool.name, {})
            result = await calcmcp_client.call_tool(tool.name, args)
            print(f"    call_tool({tool.name}, {args}) => {result}\n")


def main() -> None:
    """Entry point for the MCP client."""
    asyncio.run(run_client())


if __name__ == "__main__":
    main()
