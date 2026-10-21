"""Unit tests for ``Agent`` tool calls against an in-memory MCP server."""

from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP

from math_ai_agent.agent.agent import Agent
from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from tests.fakes.chat import make_chat_completion, make_client, make_tool_call


def _calculator() -> FastMCP:
    server = FastMCP("calculator")

    @server.tool
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    @server.tool
    def divide(a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    return server


@pytest.fixture()
async def calc():
    async with Client(_calculator()) as client:
        yield client


async def _run_one_tool_call(calc, app_config, name, arguments):
    """Run a prompt whose first turn calls one tool; return its output."""
    histories = []
    responses = [
        make_chat_completion(
            content=None,
            tool_calls=[make_tool_call(name=name, arguments=arguments)],
            finish_reason="tool_calls",
        ),
        make_chat_completion(content="done"),
    ]

    async def _next_response(history):
        histories.append(list(history))
        return responses.pop(0)

    agent = Agent(calc, app_config.model, make_client())
    with patch.object(
        ChatCompletionsClient, "prompt", side_effect=_next_response
    ):
        assert (await agent.run("compute")).answer == "done"
    return histories[1][-1]["content"]


async def test_agent_sends_mcp_tool_result_to_llm(calc, app_config):
    output = await _run_one_tool_call(
        calc, app_config, "add", '{"a": 4, "b": 4}'
    )
    assert output == "8.0"


async def test_agent_sends_mcp_tool_error_to_llm(calc, app_config):
    output = await _run_one_tool_call(
        calc, app_config, "divide", '{"a": 1, "b": 0}'
    )
    assert "Cannot divide by zero" in output
