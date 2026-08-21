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

"""Integration test for LLM tool calling via the ChatCompletionClient.

Connects to the calculator MCP server, discovers tools, then runs
an agent loop that sends a math prompt to the LLM and dispatches
tool calls back to the MCP server.  Run standalone with::

    poetry run python tests/integration/test_llm_chat_completion_tool.py
"""

import asyncio
import json
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


async def call_tool(tool_name: str, args: dict) -> str:
    """Call a calculator MCP tool over a new connection.

    Args:
        tool_name: The name of the MCP tool to invoke.
        args: The arguments dict to pass to the tool.

    Returns:
        The string representation of the tool result.
    """
    async with CalcMCPClient() as calcmcp_client:
        logger.info(
            "Calling calculator MCP tool %s with %s",
            tool_name,
            args,
        )
        result = await calcmcp_client.call_tool(tool_name, args)
        logger.debug(
            "Tool %s result:\n%s",
            tool_name,
            json.dumps(result.structured_content, indent=2),
        )
        return str(result.data)


async def prompt_llm() -> None:
    """Run the interactive agent loop with LLM tool calling.

    Discovers MCP tools, reads a math prompt from the user,
    then enters an agent loop that sends it to the LLM and
    dispatches any tool calls to the calculator MCP server
    until the LLM produces a final text response.
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

    user_input = input("User: ")
    messages.append({"role": "user", "content": user_input})
    logger.debug("Sending user prompt: %s", user_input)

    # -------------------------
    # Agent Loop
    # -------------------------
    while True:
        response = await llm.create_response(messages)
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        match finish_reason:
            case "stop":
                logger.info("Assistant: %s", message.content)
                break

            case "length":
                logger.error("Token limit reached.")
                break

            case "tool_calls":
                messages.append(message)
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_call_id = tool_call.id
                    args = json.loads(tool_call.function.arguments)
                    result = await call_tool(tool_name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result,
                        }
                    )
                continue

            case "content_filter":
                logger.error("Blocked by safety reasons.")
                break

            case None:
                # Happens during streaming before final chunk
                pass

            case _:
                raise ValueError(f"Unknown finish_reason: {finish_reason}")


async def main() -> None:
    """Entry point for the LLM tool-calling integration test."""
    logger.info("Running integration test for ChatCompletionClient")
    await prompt_llm()
    logger.info("Integration test completed")


if __name__ == "__main__":
    asyncio.run(main())
