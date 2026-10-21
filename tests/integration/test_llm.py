"""Integration test for the ChatCompletionsClient LLM wrapper.

Connects to the calculator MCP server, discovers tools, then sends
a math prompt to the LLM via ``ChatCompletionsClient``.  Run standalone with::

    poetry run python tests/integration/test_llm.py
"""

import asyncio
import logging

import mcp_types
from ai_utils_lib.config.config import load_config
from ai_utils_lib.config.file_load_config import configure_logging

from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from math_ai_agent.mcp.calc_client import CalcMCPClient

_PACKAGE = "math_ai_agent"

logger = logging.getLogger(__name__)

# LLM endpoint, model, API key env var and instructions come from
# config.yaml.


async def get_mcp_tools() -> list[mcp_types.Tool]:
    """Return the tools discovered from the Calculator MCP server."""
    logger.info("Connecting to Calculator MCP server")
    async with CalcMCPClient(
        load_config(_PACKAGE).mcp["calculator"]
    ) as calcmcp_client:
        tools = await calcmcp_client.list_tools()
        logger.info("Discovered %d MCP tool(s)", len(tools))
        return tools


async def prompt_llm() -> None:
    """Discover MCP tools and send a single math prompt.

    Connects to the calculator MCP server to discover tools,
    then sends a user prompt to the LLM.
    """
    logger.info("Starting LLM prompt test")
    tools = await get_mcp_tools()
    messages = [{"role": "user", "content": "4+4?"}]
    logger.debug("Sending prompt: %s", messages[-1]["content"])
    async with ChatCompletionsClient(load_config(_PACKAGE).model, tools) as llm:
        response = await llm.prompt(messages)
    logger.info("Assistant: %s", response.choices[0].message.content)


async def main() -> None:
    """Entry point for the LLM integration test."""
    logger.info("Running integration test for ChatCompletionsClient")
    await prompt_llm()
    logger.info("Integration test completed")


if __name__ == "__main__":
    configure_logging(load_config(_PACKAGE))
    asyncio.run(main())
