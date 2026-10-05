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

"""Unit tests for :mod:`math_ai_agent.mcp.calc_client`."""

# Tests call the private token store helper.
# pylint: disable=protected-access

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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


def _make_calc(call_result="42", tools=None):
    """Create a ``CalcMCPClient`` with mocked tool methods."""
    with patch.object(Client, "__init__", return_value=None):
        calc = CalcMCPClient()

    calc.call_tool = AsyncMock(return_value=call_result)
    calc.list_tools = AsyncMock(return_value=tools or [])
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
    # pylint: disable-next=protected-access
    CalcMCPClient._create_token_store("~/tokens")
    assert (tmp_path / "tokens").is_dir()


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
