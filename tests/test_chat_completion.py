# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review
# and refinement have occurred, users should be aware that the output may
# contain inaccuracies, errors, or security vulnerabilities
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
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

"""Unit tests for the Chat Completions path in
:mod:`math_ai_agent.llm`.
"""

import asyncio
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import mcp_types
import pytest
from fastmcp.exceptions import ToolError
from openai import omit
from openai.types.chat import ChatCompletionMessage

from math_ai_agent.agent import agent as llm_module
from math_ai_agent.agent.agent import Agent
from math_ai_agent.config.config import DEFAULT_LLM_TIMEOUT_SECONDS, LLMConfig
from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from math_ai_agent.llm.llm_errors import (
    AgentBusyError,
    ContentFilterError,
    TokenLimitError,
)
from math_ai_agent.llm.responses_client import ResponsesClient
from math_ai_agent.llm.utils import to_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY_ENV = "TEST_LLM_KEY"
_BASE_URL = "http://localhost:11434/v1"
_MODEL = "test-model"
_INSTRUCTIONS = "Test instructions."
_USAGE = SimpleNamespace(
    prompt_tokens=10,
    completion_tokens=5,
    total_tokens=15,
)
_TOOL_RESULT = SimpleNamespace(data=8, structured_content={"result": 8})
_ADD_TOOL = mcp_types.Tool(
    name="add",
    description="Add two numbers",
    input_schema={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    },
)
# The Chat Completions tool definitions the client sends for _ADD_TOOL.
_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    }
]


def _make_chat_completion(
    content="42", tool_calls=None, finish_reason="stop", usage=_USAGE
):
    """Build a fake ChatCompletion-like response object."""
    message = SimpleNamespace(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        function_call=None,
        refusal=None,
    )
    choice = SimpleNamespace(
        message=message,
        finish_reason=finish_reason,
    )
    response = SimpleNamespace(choices=[choice], usage=usage)

    def _dump_tool_calls(tc_list):
        if tc_list is None:
            return None
        return [
            {
                "id": tc.id,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tc_list
        ]

    response.model_dump = lambda **_: {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": _dump_tool_calls(tool_calls),
                    "function_call": None,
                    "refusal": None,
                },
            }
        ]
    }
    return response


def _llm_config(**updates) -> LLMConfig:
    """Build an ``LLMConfig`` with test values and ``updates`` applied."""
    return LLMConfig(
        model_base_url=_BASE_URL,
        model=_MODEL,
        api_key_env=_API_KEY_ENV,
        system_instructions=_INSTRUCTIONS,
        **updates,
    )


def _make_client():
    """Create an ChatCompletionsClient instance with test parameters."""
    return ChatCompletionsClient(_llm_config(), [_ADD_TOOL])


# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ChatCompletionsClient(_llm_config(), [_ADD_TOOL])
    assert client.openai_client is not None
    assert client.tools == _TOOLS
    assert client.model == _MODEL
    assert isinstance(client, ChatCompletionsClient)


def test_to_json_dumps_sdk_objects_and_falls_back_to_str():
    """SDK objects use model_dump; other unencodable values use str."""
    message = ChatCompletionMessage(role="assistant", content="4 + 4 = 8")
    history = [{"role": "user", "content": "4+4?"}, message, date(2026, 9, 26)]
    assert json.loads(to_json(history)) == [
        {"role": "user", "content": "4+4?"},
        {"role": "assistant", "content": "4 + 4 = 8"},
        "2026-09-26",
    ]


@pytest.mark.asyncio
async def test_async_with_closes_openai_client():
    """Leaving an ``async with`` block closes the client."""
    client = _make_client()
    with patch.object(
        client.openai_client, "close", new_callable=AsyncMock
    ) as mock_close:
        async with client as entered:
            assert entered is client
    mock_close.assert_awaited_once()


def test_init_uses_default_timeout():
    client = ChatCompletionsClient(_llm_config(), [_ADD_TOOL])
    assert client.openai_client.timeout == DEFAULT_LLM_TIMEOUT_SECONDS


def test_init_uses_given_timeout():
    client = ChatCompletionsClient(_llm_config(timeout_seconds=30), [_ADD_TOOL])
    assert client.openai_client.timeout == 30


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [0.0, 0.2])
async def test_prompt_sends_temperature(temperature):
    """A set temperature is sent, including 0."""
    client = ChatCompletionsClient(
        _llm_config(temperature=temperature), [_ADD_TOOL]
    )
    mock_create = AsyncMock(return_value=_make_chat_completion())
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    await client.prompt([{"role": "user", "content": "4+4?"}])

    assert mock_create.await_args.kwargs["temperature"] == temperature


def test_init_empty_tools_raises():
    """Empty tools list raises ValueError."""
    with pytest.raises(ValueError, match="tools must not be empty"):
        ChatCompletionsClient(_llm_config(), [])


# ---------------------------------------------------------------------------
# _format_tools
# ---------------------------------------------------------------------------


_MCP_TOOLS = [
    mcp_types.Tool(
        name="add",
        description="Add two numbers",
        input_schema={"type": "object", "properties": {}},
    ),
    mcp_types.Tool(
        name="noop", input_schema={"type": "object", "properties": {}}
    ),
]

_TOOLS_DEFINITIONS = [
    {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {"type": "object", "properties": {}},
    },
    {"name": "noop", "parameters": {"type": "object", "properties": {}}},
]


def test_format_tools_nests_each_definition_under_function():
    """Each definition becomes a nested Chat Completions function tool."""
    # pylint: disable-next=protected-access
    assert ChatCompletionsClient._format_tools(_MCP_TOOLS) == [
        {"type": "function", "function": definition}
        for definition in _TOOLS_DEFINITIONS
    ]


def test_format_tools_empty_list():
    # pylint: disable-next=protected-access
    assert ChatCompletionsClient._format_tools([]) == []


# ---------------------------------------------------------------------------
# prompt — text response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prompt_returns_completion():
    """prompt returns the ChatCompletion from the API."""
    fake_response = _make_chat_completion(content="The answer is 8")
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.prompt(history)

    assert result is fake_response
    assert result.choices[0].message.content == "The answer is 8"
    mock_create.assert_awaited_once_with(
        model=_MODEL,
        messages=history,
        tools=_TOOLS,
        temperature=omit,
    )


@pytest.mark.asyncio
async def test_prompt_with_tool_calls():
    """prompt handles a response with tool_calls."""
    tool_call = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(
            name="add",
            arguments='{"a": 2, "b": 3}',
        ),
    )
    fake_response = _make_chat_completion(
        content=None,
        tool_calls=[tool_call],
        finish_reason="tool_calls",
    )
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "2+3?"}]
    result = await client.prompt(history)

    assert result is fake_response
    assert result.choices[0].message.content is None
    assert len(result.choices[0].message.tool_calls) == 1
    assert result.choices[0].message.tool_calls[0].function.name == "add"


@pytest.mark.asyncio
async def test_prompt_with_none_content_no_tool_calls():
    """prompt handles None content without tool_calls."""
    fake_response = _make_chat_completion(
        content=None,
        tool_calls=None,
        finish_reason="stop",
    )
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "hello"}]
    result = await client.prompt(history)

    assert result.choices[0].message.content is None
    assert result.choices[0].message.tool_calls is None


@pytest.mark.asyncio
async def test_prompt_passes_all_messages():
    """prompt forwards the full message history."""
    fake_response = _make_chat_completion(content="done")
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [
        {"role": "system", "content": "You are a math tutor."},
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "And 3+3?"},
    ]
    await client.prompt(history)

    mock_create.assert_awaited_once_with(
        model=_MODEL,
        messages=history,
        tools=_TOOLS,
        temperature=omit,
    )


@pytest.mark.asyncio
async def test_prompt_multiple_tool_calls():
    """prompt handles multiple tool calls in one response."""
    tool_calls = [
        SimpleNamespace(
            id="call_1",
            function=SimpleNamespace(name="add", arguments='{"a": 1, "b": 2}'),
        ),
        SimpleNamespace(
            id="call_2",
            function=SimpleNamespace(name="add", arguments='{"a": 3, "b": 4}'),
        ),
    ]
    fake_response = _make_chat_completion(
        content=None,
        tool_calls=tool_calls,
        finish_reason="tool_calls",
    )
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "(1+2) + (3+4)?"}]
    result = await client.prompt(history)

    assert len(result.choices[0].message.tool_calls) == 2


# ---------------------------------------------------------------------------
# Agent.run — helpers
# ---------------------------------------------------------------------------


def _make_tool_call(call_id="call-1", name="add", arguments='{"a": 4, "b": 4}'):
    """Build a fake tool_call object as returned by the OpenAI SDK."""
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


@pytest.fixture()
def agent_env():
    """Build an ``Agent`` with a fake MCP client and a patched LLM.

    Yields a ``SimpleNamespace`` whose ``responses`` list is consumed
    one entry per ``prompt`` call, whose ``histories`` list
    records a snapshot of the history sent on each call, and whose
    ``call_tool`` mock records every dispatched calculator tool call.
    """
    env = SimpleNamespace(
        responses=[],
        histories=[],
        call_tool=AsyncMock(return_value=_TOOL_RESULT),
    )

    async def _next_response(history):
        env.histories.append(list(history))
        return env.responses.pop(0)

    env.agent = Agent(
        SimpleNamespace(call_tool=env.call_tool),
        ChatCompletionsClient(_llm_config(), [_ADD_TOOL]),
    )
    with patch.object(
        ChatCompletionsClient, "prompt", side_effect=_next_response
    ):
        yield env


@pytest.mark.asyncio
async def test_agent_context_manager_closes_llm_client(agent_env):
    with patch.object(
        ChatCompletionsClient,
        "__aexit__",
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_close:
        async with agent_env.agent as agent:
            assert agent is agent_env.agent
            mock_close.assert_not_awaited()
    mock_close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Agent.run — terminal responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_returns_content_on_stop(agent_env):
    """A "stop" finish_reason returns the assistant message content."""
    agent_env.responses = [_make_chat_completion(content="The answer is 8")]
    assert await agent_env.agent.run("4+4?") == "The answer is 8"


@pytest.mark.asyncio
async def test_agent_run_returns_empty_string_for_none_content(agent_env):
    """A "stop" with no content returns an empty string, not None."""
    agent_env.responses = [_make_chat_completion(content=None)]
    assert await agent_env.agent.run("4+4?") == ""


@pytest.mark.asyncio
async def test_agent_run_handles_missing_usage(agent_env):
    """A response without usage data is logged and does not raise."""
    agent_env.responses = [_make_chat_completion(content="8", usage=None)]
    assert await agent_env.agent.run("4+4?") == "8"


# ---------------------------------------------------------------------------
# Agent.run — error finish reasons
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_length_raises_token_limit_error(agent_env):
    """A "length" finish_reason raises TokenLimitError."""
    agent_env.responses = [_make_chat_completion(finish_reason="length")]
    with pytest.raises(TokenLimitError, match="Token limit reached"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_content_filter_raises_content_filter_error(
    agent_env,
):
    """A "content_filter" finish_reason raises ContentFilterError."""
    agent_env.responses = [
        _make_chat_completion(finish_reason="content_filter")
    ]
    with pytest.raises(ContentFilterError, match="blocked for safety"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_unknown_reason_raises_value_error(agent_env):
    """An unrecognised finish_reason raises ValueError."""
    agent_env.responses = [_make_chat_completion(finish_reason="wat")]
    with pytest.raises(ValueError, match="Non-supported finish_reason: wat"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_none_reason_raises_value_error(agent_env):
    """A missing finish_reason raises ValueError."""
    agent_env.responses = [_make_chat_completion(finish_reason=None)]
    with pytest.raises(ValueError, match="Non-supported finish_reason: None"):
        await agent_env.agent.run("4+4?")


# ---------------------------------------------------------------------------
# Agent.run — continue branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_dispatches_tool_call(agent_env):
    """A tool_calls response dispatches to the MCP calculator."""
    agent_env.responses = [
        _make_chat_completion(
            content=None,
            tool_calls=[_make_tool_call()],
            finish_reason="tool_calls",
        ),
        _make_chat_completion(content="4 + 4 = 8"),
    ]
    assert await agent_env.agent.run("4+4?") == "4 + 4 = 8"
    agent_env.call_tool.assert_awaited_once_with("add", {"a": 4, "b": 4})


@pytest.mark.asyncio
async def test_agent_run_sends_configured_system_instructions(
    agent_env, app_config
):
    """The first message is the system prompt from config.yaml."""
    agent_env.responses = [_make_chat_completion(content="8")]
    await agent_env.agent.run("4+4?")
    assert agent_env.histories[0][0] == {
        "role": "system",
        "content": app_config.llm.system_instructions,
    }


@pytest.mark.asyncio
async def test_agent_run_returns_tool_error_to_llm(agent_env):
    """A tool error is sent to the LLM as the tool message content."""
    agent_env.call_tool.side_effect = ToolError(
        "Error calling tool 'divide': Cannot divide by zero"
    )
    agent_env.responses = [
        _make_chat_completion(
            content=None,
            tool_calls=[_make_tool_call(name="divide")],
            finish_reason="tool_calls",
        ),
        _make_chat_completion(content="undefined"),
    ]
    assert await agent_env.agent.run("10/0?") == "undefined"
    assert agent_env.histories[1][-1] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "Error calling tool 'divide': Cannot divide by zero",
    }


@pytest.mark.asyncio
async def test_agent_run_returns_invalid_json_arguments_to_llm(agent_env):
    """Invalid JSON arguments are sent to the LLM without a tool call."""
    agent_env.responses = [
        _make_chat_completion(
            content=None,
            tool_calls=[_make_tool_call(arguments="{bad")],
            finish_reason="tool_calls",
        ),
        _make_chat_completion(content="done"),
    ]
    assert await agent_env.agent.run("4+4?") == "done"
    agent_env.call_tool.assert_not_awaited()
    assert "invalid JSON arguments" in agent_env.histories[1][-1]["content"]


@pytest.mark.asyncio
async def test_agent_run_dispatches_multiple_tool_calls(agent_env):
    """Every tool call in one response is dispatched in order."""
    agent_env.responses = [
        _make_chat_completion(
            content=None,
            tool_calls=[
                _make_tool_call(call_id="c1", name="add"),
                _make_tool_call(
                    call_id="c2", name="multiply", arguments='{"a": 2, "b": 3}'
                ),
            ],
            finish_reason="tool_calls",
        ),
        _make_chat_completion(content="done"),
    ]
    assert await agent_env.agent.run("compute") == "done"
    assert agent_env.call_tool.await_count == 2
    assert [c.args[0] for c in agent_env.call_tool.await_args_list] == [
        "add",
        "multiply",
    ]


# ---------------------------------------------------------------------------
# Agent.create — api_style selection
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_calc():
    """Fake MCP client exposing the MCP tools definitions."""
    return SimpleNamespace(list_tools=AsyncMock(return_value=_MCP_TOOLS))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client_type", [ChatCompletionsClient, ResponsesClient]
)
async def test_agent_create_selects_client_for_api_style(
    app_config, fake_calc, client_type
):
    """Agent.create builds the LLM client matching llm.api_style."""
    app_config.llm.api_style = (
        "responses" if client_type is ResponsesClient else "chat"
    )
    with patch.object(llm_module, "get_config", return_value=app_config):
        agent = await Agent.create(fake_calc)
    llm = agent._llm  # pylint: disable=protected-access
    assert isinstance(llm, client_type)
    # pylint: disable-next=protected-access
    assert llm.tools == client_type._format_tools(_MCP_TOOLS)
    assert llm.openai_client.timeout == app_config.llm.timeout_seconds
    assert llm.temperature == app_config.llm.temperature


@pytest.mark.asyncio
async def test_agent_create_closes_llm_when_construction_fails(fake_calc):
    """A failure building the agent closes the new LLM client."""
    with (
        patch.object(Agent, "__init__", side_effect=RuntimeError("boom")),
        patch.object(
            ChatCompletionsClient,
            "__aexit__",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_close,
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await Agent.create(fake_calc)
    mock_close.assert_awaited_once()


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
def single_slot_agent(app_config):
    """An agent allowing one prompt at a time, with a gated LLM."""
    app_config.llm.max_concurrent_prompts = 1
    gate = asyncio.Event()

    async def _gated_response(history):  # pylint: disable=unused-argument
        await gate.wait()
        return _stop_response()

    agent = Agent(
        SimpleNamespace(call_tool=AsyncMock()),
        ChatCompletionsClient(_llm_config(), [_ADD_TOOL]),
    )
    with patch.object(
        ChatCompletionsClient, "prompt", side_effect=_gated_response
    ):
        yield agent, gate


@pytest.mark.asyncio
async def test_agent_run_rejects_prompt_when_slots_full(single_slot_agent):
    """A prompt beyond max_concurrent_prompts raises AgentBusyError."""
    agent, gate = single_slot_agent
    first = asyncio.create_task(agent.run("1+1?"))
    await asyncio.sleep(0)
    with pytest.raises(AgentBusyError):
        await agent.run("2+2?")
    gate.set()
    assert await first == "done"


@pytest.mark.asyncio
async def test_agent_run_frees_slot_after_prompt(single_slot_agent):
    """A finished prompt frees its slot for the next one."""
    agent, gate = single_slot_agent
    gate.set()
    assert await agent.run("1+1?") == "done"
    assert await agent.run("2+2?") == "done"


@pytest.mark.asyncio
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
    assert await agent.run("2+2?") == "done"
