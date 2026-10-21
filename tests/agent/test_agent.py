"""Unit tests for ``Agent`` setup and its concurrent prompt limit."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from math_ai_agent.agent.agent import Agent
from math_ai_agent.agent.errors import AgentBusyError
from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from math_ai_agent.llm.responses_client import ResponsesClient

from tests.fakes.common import ADD_TOOL, MCP_TOOLS, llm_config

# ---------------------------------------------------------------------------
# Agent context — api_style selection
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_calc():
    """Fake MCP client exposing the MCP tools definitions."""
    return SimpleNamespace(list_tools=AsyncMock(return_value=MCP_TOOLS))


@pytest.mark.parametrize(
    "client_type", [ChatCompletionsClient, ResponsesClient]
)
async def test_agent_enter_selects_client_for_api_style(
    app_config, update_model, fake_calc, client_type
):
    """Entering the agent builds the LLM client matching model.api_style."""
    model = update_model(
        api_style="responses" if client_type is ResponsesClient else "chat"
    )
    async with Agent(fake_calc, model) as agent:
        llm = agent._llm  # pylint: disable=protected-access
    assert isinstance(llm, client_type)
    # pylint: disable-next=protected-access
    assert llm.tools == client_type._format_tools(MCP_TOOLS)
    assert llm.openai_client.timeout == app_config.model.timeout_seconds
    assert llm.temperature == app_config.model.temperature


async def test_agent_run_requires_entered_context(app_config, fake_calc):
    """Running an agent without an LLM client raises RuntimeError."""
    with pytest.raises(RuntimeError):
        await Agent(fake_calc, app_config.model).run("1+1?")


# ---------------------------------------------------------------------------
# Agent.run — concurrent prompt limit
# ---------------------------------------------------------------------------


def _stop_response(content="done"):
    """Build a Chat Completions response that ends the agent loop."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=None,
    )


@pytest.fixture()
def single_slot_agent(update_model):
    """An agent allowing one prompt at a time, with a gated LLM."""
    model = update_model(max_concurrent_prompts=1)
    gate = asyncio.Event()

    async def _gated_response(history):  # pylint: disable=unused-argument
        await gate.wait()
        return _stop_response()

    agent = Agent(
        SimpleNamespace(call_tool=AsyncMock()),
        model,
        ChatCompletionsClient(llm_config(), [ADD_TOOL]),
    )
    with patch.object(
        ChatCompletionsClient, "prompt", side_effect=_gated_response
    ):
        yield agent, gate


async def test_agent_run_rejects_prompt_when_slots_full(single_slot_agent):
    """A prompt beyond max_concurrent_prompts raises AgentBusyError."""
    agent, gate = single_slot_agent
    first = asyncio.create_task(agent.run("1+1?"))
    await asyncio.sleep(0)
    with pytest.raises(AgentBusyError):
        await agent.run("2+2?")
    gate.set()
    assert (await first).answer == "done"


async def test_agent_run_frees_slot_after_prompt(single_slot_agent):
    """A finished prompt frees its slot for the next one."""
    agent, gate = single_slot_agent
    gate.set()
    assert (await agent.run("1+1?")).answer == "done"
    assert (await agent.run("2+2?")).answer == "done"


async def test_agent_run_frees_slot_after_error(single_slot_agent):
    """A failed prompt frees its slot for the next one."""
    agent, gate = single_slot_agent
    gate.set()
    with patch.object(
        ChatCompletionsClient,
        "prompt",
        side_effect=RuntimeError("LLM down"),
    ):
        with pytest.raises(RuntimeError, match="LLM down"):
            await agent.run("1+1?")
    assert (await agent.run("2+2?")).answer == "done"
