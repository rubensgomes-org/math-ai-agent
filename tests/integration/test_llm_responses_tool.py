"""Integration test for LLM tool calling via the Responses API.

Drives the real ``Agent`` from ``math_ai_agent.agent.agent`` against
the configured LLM endpoint and the calculator MCP server, so the loop
under test is the same code the FastAPI app runs.  Reads the math
prompt from the command line, or interactively when no argument is
given.  Run standalone with::

    poetry run python tests/integration/test_llm_responses_tool.py
    poetry run python tests/integration/test_llm_responses_tool.py "4+4*3?"

The agent always uses ``ResponsesClient``, so the configured
endpoint must support the Responses API (``POST /v1/responses``).
"""

import asyncio
import logging
import sys

from ai_utils_lib.config.config import load_config
from ai_utils_lib.config.file_load_config import configure_logging

from math_ai_agent.agent.agent import Agent
from math_ai_agent.llm.responses_client import ResponsesClient
from math_ai_agent.mcp.calc_client import CalcMCPClient

_PACKAGE = "math_ai_agent"

logger = logging.getLogger(__name__)


async def show_tools(calc: CalcMCPClient) -> None:
    """Log the tool definitions from the MCP server."""
    tools = await calc.list_tools()
    logger.info("Discovered %d MCP tool(s)", len(tools))
    for tool in tools:
        logger.info("  - %s: %s", tool.name, tool.description)


async def main() -> None:
    """Entry point for the Responses API integration test."""
    logger.info("Running integration test for ResponsesClient")
    async with CalcMCPClient(load_config(_PACKAGE).mcp["calculator"]) as calc:
        await show_tools(calc)
        user_input = (
            " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("User: ")
        )
        logger.debug("Sending user prompt: %s", user_input)
        model = load_config(_PACKAGE).model
        llm = ResponsesClient(model, await calc.list_tools())
        async with Agent(calc, model, llm) as agent:
            logger.info("Assistant: %s", await agent.run(user_input))
    logger.info("Integration test completed")


if __name__ == "__main__":
    configure_logging(load_config(_PACKAGE))
    asyncio.run(main())
