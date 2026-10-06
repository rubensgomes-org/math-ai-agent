"""Integration test client for the calculator MCP server.

Connects to the remote calculator MCP server, lists available tools,
and calls each one with sample arguments to verify end-to-end
connectivity.  Run standalone with::

    poetry run python tests/integration/test_calc_client.py
"""

import asyncio
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
