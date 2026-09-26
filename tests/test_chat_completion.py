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

"""Unit tests for the Chat Completions path in
:mod:`math_ai_agent.llm`.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from math_ai_agent.config.config import DEFAULT_LLM_TIMEOUT_SECONDS
from math_ai_agent.llm import agent as llm_module
from math_ai_agent.llm.agent import Agent, AgentBusyError
from math_ai_agent.llm.client import ChatCompletionClient, ResponsesClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY = "test-api-key"
_BASE_URL = "http://localhost:11434/v1"
_MODEL = "test-model"
_USAGE = SimpleNamespace(
    prompt_tokens=10,
    completion_tokens=5,
    total_tokens=15,
)
_TOOL_RESULT = SimpleNamespace(data=8, structured_content={"result": 8})
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

    response.model_dump = lambda: {
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


def _make_client():
    """Create an ChatCompletionClient instance with test parameters."""
    return ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)


# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)
    assert client.openai_client is not None
    assert client.tools is _TOOLS
    assert client.model == _MODEL
    assert isinstance(client, ChatCompletionClient)


def test_init_uses_default_timeout():
    client = ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)
    assert client.openai_client.timeout == DEFAULT_LLM_TIMEOUT_SECONDS


def test_init_uses_given_timeout():
    client = ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS, 30)
    assert client.openai_client.timeout == 30


def test_init_empty_api_key_raises():
    """Empty api_key raises ValueError."""
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ChatCompletionClient("", _BASE_URL, _MODEL, _TOOLS)


def test_init_empty_base_url_raises():
    """Empty base_url raises ValueError."""
    with pytest.raises(ValueError, match="base_url must not be empty"):
        ChatCompletionClient(_API_KEY, "", _MODEL, _TOOLS)


def test_init_empty_model_raises():
    """Empty model raises ValueError."""
    with pytest.raises(ValueError, match="model must not be empty"):
        ChatCompletionClient(_API_KEY, _BASE_URL, "", _TOOLS)


def test_init_empty_tools_raises():
    """Empty tools list raises ValueError."""
    with pytest.raises(ValueError, match="tools must not be empty"):
        ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, [])


def test_init_none_api_key_raises():
    """None api_key raises ValueError."""
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ChatCompletionClient(None, _BASE_URL, _MODEL, _TOOLS)


# ---------------------------------------------------------------------------
# create_response — text response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_response_returns_completion():
    """create_response returns the ChatCompletion from the API."""
    fake_response = _make_chat_completion(content="The answer is 8")
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.create_response(history)

    assert result is fake_response
    assert result.choices[0].message.content == "The answer is 8"
    mock_create.assert_awaited_once_with(
        model=_MODEL,
        messages=history,
        tools=_TOOLS,
        store=False,
    )


@pytest.mark.asyncio
async def test_create_response_with_tool_calls():
    """create_response handles a response with tool_calls."""
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
    result = await client.create_response(history)

    assert result is fake_response
    assert result.choices[0].message.content is None
    assert len(result.choices[0].message.tool_calls) == 1
    assert result.choices[0].message.tool_calls[0].function.name == "add"


@pytest.mark.asyncio
async def test_create_response_with_none_content_no_tool_calls():
    """create_response handles None content without tool_calls."""
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
    result = await client.create_response(history)

    assert result.choices[0].message.content is None
    assert result.choices[0].message.tool_calls is None


@pytest.mark.asyncio
async def test_create_response_passes_all_messages():
    """create_response forwards the full message history."""
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
    await client.create_response(history)

    mock_create.assert_awaited_once_with(
        model=_MODEL,
        messages=history,
        tools=_TOOLS,
        store=False,
    )


@pytest.mark.asyncio
async def test_create_response_multiple_tool_calls():
    """create_response handles multiple tool calls in one response."""
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
    result = await client.create_response(history)

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
def agent_env(app_config):
    """Build an ``Agent`` with a fake MCP client and a patched LLM.

    Yields a ``SimpleNamespace`` whose ``responses`` list is consumed
    one entry per ``create_response`` call, and whose ``call_tool``
    mock records every dispatched calculator tool call.
    """
    env = SimpleNamespace(
        responses=[], call_tool=AsyncMock(return_value=_TOOL_RESULT)
    )

    async def _next_response(history):  # pylint: disable=unused-argument
        return env.responses.pop(0)

    env.agent = Agent(
        SimpleNamespace(call_tool=env.call_tool),
        ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS),
        app_config.llm.system_instructions,
        app_config.llm.max_concurrent_prompts,
    )
    with patch.object(
        ChatCompletionClient, "create_response", side_effect=_next_response
    ):
        yield env


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
async def test_agent_run_length_raises_runtime_error(agent_env):
    """A "length" finish_reason raises RuntimeError."""
    agent_env.responses = [_make_chat_completion(finish_reason="length")]
    with pytest.raises(RuntimeError, match="Token limit reached"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_content_filter_raises_runtime_error(agent_env):
    """A "content_filter" finish_reason raises RuntimeError."""
    agent_env.responses = [
        _make_chat_completion(finish_reason="content_filter")
    ]
    with pytest.raises(RuntimeError, match="blocked"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_unknown_reason_raises_value_error(agent_env):
    """An unrecognised finish_reason raises ValueError."""
    agent_env.responses = [_make_chat_completion(finish_reason="wat")]
    with pytest.raises(ValueError, match="Unknown finish_reason: wat"):
        await agent_env.agent.run("4+4?")


# ---------------------------------------------------------------------------
# Agent.run — continue branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_none_reason_continues(agent_env):
    """A None finish_reason loops again instead of terminating."""
    agent_env.responses = [
        _make_chat_completion(finish_reason=None),
        _make_chat_completion(content="done"),
    ]
    assert await agent_env.agent.run("4+4?") == "done"
    assert agent_env.responses == []


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
    """Fake MCP client exposing tools in both OpenAI formats."""
    return SimpleNamespace(
        to_openai_tools=AsyncMock(return_value=_TOOLS),
        to_responses_tools=AsyncMock(
            return_value=[{"type": "function", "name": "add"}]
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("api_style", "client_type", "tools_attr"),
    [
        ("chat", ChatCompletionClient, "to_openai_tools"),
        ("responses", ResponsesClient, "to_responses_tools"),
    ],
)
async def test_agent_create_selects_client_for_api_style(
    app_config, fake_calc, api_style, client_type, tools_attr
):
    """Agent.create builds the LLM client matching llm.api_style."""
    app_config.llm.api_style = api_style
    with (
        patch.object(llm_module, "get_config", return_value=app_config),
        patch.object(llm_module, "get_api_key", return_value=_API_KEY),
    ):
        agent = await Agent.create(fake_calc)
    llm = agent._llm  # pylint: disable=protected-access
    assert isinstance(llm, client_type)
    assert llm.tools == await getattr(fake_calc, tools_attr)()
    assert llm.openai_client.timeout == app_config.llm.timeout_seconds


@pytest.mark.asyncio
async def test_agent_create_propagates_missing_api_key(app_config, fake_calc):
    """A missing API key aborts agent creation."""
    with (
        patch.object(llm_module, "get_config", return_value=app_config),
        patch.object(
            llm_module, "get_api_key", side_effect=RuntimeError("no key")
        ),
    ):
        with pytest.raises(RuntimeError, match="no key"):
            await Agent.create(fake_calc)


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
    gate = asyncio.Event()

    async def _gated_response(history):  # pylint: disable=unused-argument
        await gate.wait()
        return _stop_response()

    agent = Agent(
        SimpleNamespace(call_tool=AsyncMock()),
        ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS),
        app_config.llm.system_instructions,
        1,
    )
    with patch.object(
        ChatCompletionClient, "create_response", side_effect=_gated_response
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
        ChatCompletionClient,
        "create_response",
        side_effect=RuntimeError("LLM down"),
    ):
        with pytest.raises(RuntimeError, match="LLM down"):
            await agent.run("1+1?")
    assert await agent.run("2+2?") == "done"
