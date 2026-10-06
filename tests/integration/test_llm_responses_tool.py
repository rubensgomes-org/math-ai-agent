"""Integration test for LLM tool calling via the Responses API.

Drives the real ``Agent`` from ``math_ai_agent.agent.agent`` against
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

from math_ai_agent.agent.agent import Agent
from math_ai_agent.config.config import configure_logging, get_config
from math_ai_agent.llm.responses_client import ResponsesClient
from math_ai_agent.mcp.calc_client import CalcMCPClient

logger = logging.getLogger(__name__)


async def show_tools(calc: CalcMCPClient) -> None:
    """Log the Responses-format tool definitions from the MCP server."""
    tools = ResponsesClient.format_tools(await calc.list_tools())
    logger.info("Discovered %d MCP tool(s) in Responses format", len(tools))
    for tool in tools:
        logger.info("  - %s: %s", tool["name"], tool.get("description"))


async def main() -> None:
    """Entry point for the Responses API integration test."""
    logger.info("Running integration test for ResponsesClient")
    get_config().llm.api_style = "responses"
    async with CalcMCPClient() as calc:
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
