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

"""Unit tests for :mod:`math_ai_agent.mcp.calc_client`."""

# Tests inspect and reset the client's private tool cache.
# pylint: disable=protected-access

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import mcp.types
import pytest
from cryptography.fernet import Fernet
from fastmcp import Client

from math_ai_agent.mcp import calc_client
from math_ai_agent.mcp.calc_client import CalcMCPClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_URL = "http://localhost:9000/mcp"


@pytest.fixture(autouse=True)
def _clear_tools_cache():
    """Reset the class-level tool cache before each test."""
    CalcMCPClient._tools = []
    yield
    CalcMCPClient._tools = []


@pytest.fixture(autouse=True)
def _patch_config(app_config):
    """Serve the shared test ``AppConfig`` to the client."""
    with patch.object(calc_client, "get_config", return_value=app_config):
        yield


@pytest.fixture()
def patch_no_oauth():
    """Stub Client.__init__; the test config has OAuth disabled."""
    with patch.object(Client, "__init__", return_value=None) as mock_init:
        yield mock_init


@pytest.fixture()
def patch_oauth(monkeypatch, app_config, tmp_path):
    """Enable OAuth in the test config and stub Client.__init__ and OAuth."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("OAUTH_STORAGE_ENCRYPTION_KEY", key)
    app_config.server.calculator_mcp.token_dir = str(tmp_path)
    app_config.server.calculator_mcp.is_oauth = True
    with (
        patch.object(Client, "__init__", return_value=None) as mock_init,
        patch.object(calc_client, "OAuth") as mock_oauth,
    ):
        yield mock_init, mock_oauth


def _make_calc(call_result="42"):
    """Create a ``CalcMCPClient`` with a mocked ``call_tool``."""
    with patch.object(Client, "__init__", return_value=None):
        calc = CalcMCPClient()

    calc.call_tool = AsyncMock(return_value=call_result)
    return calc


# ---------------------------------------------------------------------------
# __init__ — no OAuth
# ---------------------------------------------------------------------------


def test_init_no_oauth(patch_no_oauth):
    mock_init = patch_no_oauth
    calc = CalcMCPClient()
    assert isinstance(calc, Client)
    mock_init.assert_called_once_with(_URL)


# ---------------------------------------------------------------------------
# __init__ — with OAuth
# ---------------------------------------------------------------------------


def test_init_with_oauth(patch_oauth):
    mock_init, mock_oauth = patch_oauth
    calc = CalcMCPClient()
    assert isinstance(calc, Client)
    mock_init.assert_called_once()
    assert mock_oauth.call_args.kwargs["callback_port"] == 10000
    # Verify OAuth auth was passed
    _, kwargs = mock_init.call_args
    assert "auth" in kwargs


def test_init_oauth_missing_env_raises(monkeypatch, app_config, tmp_path):
    monkeypatch.delenv("OAUTH_STORAGE_ENCRYPTION_KEY", raising=False)
    app_config.server.calculator_mcp.is_oauth = True
    app_config.server.calculator_mcp.token_dir = str(tmp_path)
    with patch.object(Client, "__init__", return_value=None):
        with pytest.raises(KeyError):
            CalcMCPClient()


def test_create_token_store_expands_home_and_creates_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    calc_client._create_token_store("~/tokens")
    assert (tmp_path / "tokens").is_dir()


# ---------------------------------------------------------------------------
# async context manager (__aenter__ / __aexit__)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aenter_does_not_ping():
    calc = _make_calc()
    calc.ping = AsyncMock()

    with (
        patch.object(
            Client,
            "__aenter__",
            new_callable=AsyncMock,
            return_value=calc,
        ),
        patch.object(
            Client,
            "__aexit__",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        async with calc:
            calc.ping.assert_not_awaited()


@pytest.mark.asyncio
async def test_aenter_returns_self():
    calc = _make_calc()

    with (
        patch.object(
            Client,
            "__aenter__",
            new_callable=AsyncMock,
            return_value=calc,
        ),
        patch.object(
            Client,
            "list_tools",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            Client,
            "__aexit__",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        async with calc as returned:
            assert returned is calc


@pytest.mark.asyncio
async def test_aexit_delegates_to_super():
    calc = _make_calc()

    with (
        patch.object(
            Client,
            "__aenter__",
            new_callable=AsyncMock,
            return_value=calc,
        ),
        patch.object(
            Client,
            "list_tools",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            Client,
            "__aexit__",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_exit,
    ):
        async with calc:
            pass

    mock_exit.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_tools — caching behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tools_fetches_when_empty():
    tools = [SimpleNamespace(name="sqrt", description="Square root")]
    calc = _make_calc()

    with patch.object(
        Client,
        "list_tools",
        new_callable=AsyncMock,
        return_value=tools,
    ) as mock_parent_lt:
        result = await calc.list_tools()

    assert result == tools
    assert CalcMCPClient._tools == tools
    mock_parent_lt.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_tools_returns_cache_on_second_call():
    tools = [SimpleNamespace(name="add", description="Add")]
    calc = _make_calc()

    with patch.object(
        Client,
        "list_tools",
        new_callable=AsyncMock,
        return_value=tools,
    ) as mock_parent_lt:
        first = await calc.list_tools()
        second = await calc.list_tools()

    assert first is second
    # list_tools should only have been called once (cache hit)
    mock_parent_lt.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_tools_skips_fetch_when_pre_populated():
    existing = [SimpleNamespace(name="divide", description="Divide")]
    CalcMCPClient._tools = existing
    calc = _make_calc()

    with patch.object(
        Client,
        "list_tools",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_parent_lt:
        result = await calc.list_tools()

    assert result is existing
    mock_parent_lt.assert_not_awaited()


# ---------------------------------------------------------------------------
# call_tool (inherited)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_tool_delegates_to_parent():
    calc = _make_calc(call_result="5")
    result = await calc.call_tool("add", {"a": 2, "b": 3})

    assert result == "5"
    calc.call_tool.assert_awaited_once_with("add", {"a": 2, "b": 3})


@pytest.mark.asyncio
async def test_call_tool_with_empty_arguments():
    calc = _make_calc(call_result="ok")
    result = await calc.call_tool("noop", {})

    assert result == "ok"
    calc.call_tool.assert_awaited_once_with("noop", {})


# ---------------------------------------------------------------------------
# to_openai_tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_to_openai_tools_converts_single_tool():
    tools = [
        mcp.types.Tool(
            name="add",
            description="Add two numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_openai_tools()
    assert len(result) == 1
    assert result[0]["type"] == "function"
    func = result[0]["function"]
    assert func["name"] == "add"
    assert func["description"] == "Add two numbers"
    assert func["parameters"]["type"] == "object"
    assert "a" in func["parameters"]["properties"]
    assert "b" in func["parameters"]["properties"]


@pytest.mark.asyncio
async def test_to_openai_tools_multiple_tools():
    tools = [
        mcp.types.Tool(
            name="add",
            description="Add",
            inputSchema={"type": "object", "properties": {}},
        ),
        mcp.types.Tool(
            name="sqrt",
            description="Square root",
            inputSchema={
                "type": "object",
                "properties": {"a": {"type": "number"}},
            },
        ),
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_openai_tools()
    assert len(result) == 2
    assert result[0]["function"]["name"] == "add"
    assert result[1]["function"]["name"] == "sqrt"


@pytest.mark.asyncio
async def test_to_openai_tools_empty_list():
    calc = _make_calc()
    with patch.object(
        Client,
        "list_tools",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await calc.to_openai_tools()
    assert result == []


@pytest.mark.asyncio
async def test_to_openai_tools_no_description():
    tools = [
        mcp.types.Tool(
            name="noop",
            inputSchema={"type": "object", "properties": {}},
        )
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_openai_tools()
    assert "description" not in result[0]["function"]


@pytest.mark.asyncio
async def test_to_openai_tools_preserves_input_schema():
    schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "First operand",
            },
            "b": {
                "type": "number",
                "description": "Second operand",
            },
        },
        "required": ["a", "b"],
    }
    tools = [
        mcp.types.Tool(
            name="add",
            description="Add",
            inputSchema=schema,
        )
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_openai_tools()
    assert result[0]["function"]["parameters"] == schema


# ---------------------------------------------------------------------------
# to_responses_tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_to_responses_tools_converts_single_tool():
    """A single MCP tool converts to the flat Responses schema."""
    tools = [
        mcp.types.Tool(
            name="add",
            description="Add two numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_responses_tools()
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["name"] == "add"
    assert result[0]["description"] == "Add two numbers"
    assert result[0]["parameters"]["type"] == "object"
    assert "function" not in result[0]


@pytest.mark.asyncio
async def test_to_responses_tools_multiple_tools():
    """Every MCP tool is converted, in order."""
    tools = [
        mcp.types.Tool(
            name="add",
            description="Add",
            inputSchema={"type": "object", "properties": {}},
        ),
        mcp.types.Tool(
            name="sqrt",
            description="Square root",
            inputSchema={
                "type": "object",
                "properties": {"a": {"type": "number"}},
            },
        ),
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_responses_tools()
    assert len(result) == 2
    assert result[0]["name"] == "add"
    assert result[1]["name"] == "sqrt"


@pytest.mark.asyncio
async def test_to_responses_tools_empty_list():
    """An MCP server exposing no tools yields an empty list."""
    calc = _make_calc()
    with patch.object(
        Client,
        "list_tools",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await calc.to_responses_tools()
    assert result == []


@pytest.mark.asyncio
async def test_to_responses_tools_no_description():
    """A tool without a description omits the description key."""
    tools = [
        mcp.types.Tool(
            name="noop",
            inputSchema={"type": "object", "properties": {}},
        )
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_responses_tools()
    assert "description" not in result[0]


@pytest.mark.asyncio
async def test_to_responses_tools_preserves_input_schema():
    """The MCP inputSchema is passed through verbatim as parameters."""
    schema = {
        "type": "object",
        "properties": {"a": {"type": "number", "description": "operand"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    tools = [
        mcp.types.Tool(name="sqrt", description="root", inputSchema=schema)
    ]
    CalcMCPClient._tools = tools
    calc = _make_calc()
    result = await calc.to_responses_tools()
    assert result[0]["parameters"] == schema


# ---------------------------------------------------------------------------
# Full round-trip (context manager + call_tool)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_round_trip():
    tools = [
        SimpleNamespace(name="multiply", description="Multiply"),
    ]
    calc = _make_calc(call_result="21")

    with (
        patch.object(
            Client,
            "__aenter__",
            new_callable=AsyncMock,
            return_value=calc,
        ),
        patch.object(
            Client,
            "list_tools",
            new_callable=AsyncMock,
            return_value=tools,
        ),
        patch.object(
            Client,
            "__aexit__",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        async with calc:
            result = await calc.call_tool("multiply", {"a": 3, "b": 7})
            assert result == "21"


# ---------------------------------------------------------------------------
# Module-level helpers — get_calc_mcp_tools / call_tool
# ---------------------------------------------------------------------------


class _FakeCalcClient:
    """Stand-in for CalcMCPClient as an async context manager."""

    def __init__(self, tools=None, result=None, responses_tools=None):
        self._tools = tools or []
        self._responses_tools = responses_tools or []
        self._result = result
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def to_openai_tools(self):
        return self._tools

    async def to_responses_tools(self):
        return self._responses_tools

    async def call_tool(self, tool_name, args):
        self.calls.append((tool_name, args))
        return self._result


@pytest.mark.asyncio
async def test_get_calc_mcp_tools_returns_openai_tools():
    """get_calc_mcp_tools opens a client and returns its OpenAI tool list."""
    tools = [{"type": "function", "function": {"name": "add"}}]
    fake = _FakeCalcClient(tools=tools)
    with patch.object(calc_client, "CalcMCPClient", return_value=fake):
        assert await calc_client.get_calc_mcp_tools() == tools


@pytest.mark.asyncio
async def test_get_calc_mcp_tools_empty():
    """An MCP server exposing no tools yields an empty list."""
    with patch.object(
        calc_client, "CalcMCPClient", return_value=_FakeCalcClient(tools=[])
    ):
        assert await calc_client.get_calc_mcp_tools() == []


@pytest.mark.asyncio
async def test_get_calc_mcp_tools_responses_style():
    """api_style="responses" returns the flat Responses tool list."""
    chat_tools = [{"type": "function", "function": {"name": "add"}}]
    responses_tools = [{"type": "function", "name": "add"}]
    fake = _FakeCalcClient(tools=chat_tools, responses_tools=responses_tools)
    with patch.object(calc_client, "CalcMCPClient", return_value=fake):
        assert (
            await calc_client.get_calc_mcp_tools("responses") == responses_tools
        )


@pytest.mark.asyncio
async def test_get_calc_mcp_tools_chat_style_is_the_default():
    """An explicit or omitted "chat" style returns the nested tool list."""
    chat_tools = [{"type": "function", "function": {"name": "add"}}]
    responses_tools = [{"type": "function", "name": "add"}]
    fake = _FakeCalcClient(tools=chat_tools, responses_tools=responses_tools)
    with patch.object(calc_client, "CalcMCPClient", return_value=fake):
        assert await calc_client.get_calc_mcp_tools("chat") == chat_tools
        assert await calc_client.get_calc_mcp_tools() == chat_tools


@pytest.mark.asyncio
async def test_call_tool_returns_string_result():
    """call_tool returns the string form of the tool result data."""
    result = SimpleNamespace(structured_content={"result": 8}, data=8)
    fake = _FakeCalcClient(result=result)
    with patch.object(calc_client, "CalcMCPClient", return_value=fake):
        assert await calc_client.call_tool("add", {"a": 4, "b": 4}) == "8"
    assert fake.calls == [("add", {"a": 4, "b": 4})]


@pytest.mark.asyncio
async def test_call_tool_propagates_errors():
    """A failing MCP tool call propagates to the caller."""
    fake = _FakeCalcClient()

    async def _boom(tool_name, args):
        raise RuntimeError("tool exploded")

    fake.call_tool = _boom
    with patch.object(calc_client, "CalcMCPClient", return_value=fake):
        with pytest.raises(RuntimeError, match="tool exploded"):
            await calc_client.call_tool("divide", {"a": 1, "b": 0})
