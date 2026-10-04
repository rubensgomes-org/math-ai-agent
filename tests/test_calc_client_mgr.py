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

"""Unit tests for :mod:`math_ai_agent.mcp.calc_client_mgr`."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from math_ai_agent.mcp.calc_client_mgr import CalcMCPClientMgr

_ARGS = {"a": 4, "b": 4}


class _FakeClient:
    """Stand-in for ``CalcMCPClient`` that tracks its connection state."""

    def __init__(self, result="8"):
        self.connected = False
        self.exit_count = 0
        self.call_tool = AsyncMock(return_value=result)
        self.tools_definitions = AsyncMock(return_value=[{"name": "add"}])

    async def __aenter__(self):
        self.connected = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.connected = False
        self.exit_count += 1

    def is_connected(self):
        return self.connected

    def drop_on_call(self):
        """Make the next call lose the connection and raise."""

        async def _drop(*_args):
            await asyncio.sleep(0)
            self.connected = False
            raise RuntimeError("Connection closed")

        self.call_tool.side_effect = _drop


def _connection(*clients):
    """Build a connection whose factory returns ``clients`` in order."""
    factory = MagicMock(side_effect=list(clients))
    return CalcMCPClientMgr(client_factory=factory), factory


# ---------------------------------------------------------------------------
# Lifecycle and delegation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connects_on_enter_and_disconnects_on_exit():
    client = _FakeClient()
    conn, factory = _connection(client)
    async with conn as connected:
        assert connected is conn
        assert client.connected
    factory.assert_called_once()
    assert client.exit_count == 1


@pytest.mark.asyncio
async def test_tools_definitions_delegates_to_client():
    conn, _ = _connection(_FakeClient())
    async with conn:
        assert await conn.tools_definitions() == [{"name": "add"}]


@pytest.mark.asyncio
async def test_tool_listing_before_connect_raises():
    conn, _ = _connection(_FakeClient())
    with pytest.raises(RuntimeError, match="not connected"):
        await conn.tools_definitions()


@pytest.mark.asyncio
async def test_call_tool_delegates_to_client():
    client = _FakeClient()
    conn, _ = _connection(client)
    async with conn:
        assert await conn.call_tool("add", _ARGS) == "8"
    client.call_tool.assert_awaited_once_with("add", _ARGS)


# ---------------------------------------------------------------------------
# Reconnect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_error_on_live_connection_is_not_retried():
    client = _FakeClient()
    client.call_tool.side_effect = RuntimeError("division by zero")
    conn, factory = _connection(client)
    async with conn:
        with pytest.raises(RuntimeError, match="division by zero"):
            await conn.call_tool("divide", {"a": 1, "b": 0})
    factory.assert_called_once()


@pytest.mark.asyncio
async def test_lost_connection_reconnects_and_retries(caplog):
    first, second = _FakeClient(), _FakeClient(result="9")
    first.drop_on_call()
    conn, factory = _connection(first, second)
    async with conn:
        with caplog.at_level(logging.WARNING):
            assert await conn.call_tool("add", _ARGS) == "9"
    assert factory.call_count == 2
    assert first.exit_count == 1
    second.call_tool.assert_awaited_once_with("add", _ARGS)
    assert "MCP connection lost" in caplog.text


@pytest.mark.asyncio
async def test_retry_failure_propagates():
    first, second = _FakeClient(), _FakeClient()
    first.drop_on_call()
    second.call_tool.side_effect = RuntimeError("still failing")
    conn, _ = _connection(first, second)
    async with conn:
        with pytest.raises(RuntimeError, match="still failing"):
            await conn.call_tool("add", _ARGS)


@pytest.mark.asyncio
async def test_disconnected_client_reconnects_before_call():
    first, second = _FakeClient(), _FakeClient(result="9")
    conn, factory = _connection(first, second)
    async with conn:
        first.connected = False
        assert await conn.call_tool("add", _ARGS) == "9"
    first.call_tool.assert_not_awaited()
    assert factory.call_count == 2


@pytest.mark.asyncio
async def test_concurrent_failures_reconnect_once():
    first, second = _FakeClient(), _FakeClient(result="9")
    first.drop_on_call()
    conn, factory = _connection(first, second)
    async with conn:
        results = await asyncio.gather(
            conn.call_tool("add", _ARGS), conn.call_tool("add", _ARGS)
        )
    assert results == ["9", "9"]
    assert factory.call_count == 2
    assert second.call_tool.await_count == 2


@pytest.mark.asyncio
async def test_failed_reconnect_is_retried_on_next_call():
    first, third = _FakeClient(), _FakeClient(result="9")
    first.drop_on_call()
    conn, factory = _connection(first, ConnectionError("server down"), third)
    async with conn:
        with pytest.raises(ConnectionError, match="server down"):
            await conn.call_tool("add", _ARGS)
        assert await conn.call_tool("add", _ARGS) == "9"
    assert factory.call_count == 3


class _FailingDisconnectClient(_FakeClient):
    """Fake client whose disconnect raises."""

    async def __aexit__(self, exc_type, exc, tb):
        raise RuntimeError("disconnect failed")


@pytest.mark.asyncio
async def test_disconnect_error_is_logged_not_raised(caplog):
    conn, _ = _connection(_FailingDisconnectClient())
    with caplog.at_level(logging.WARNING):
        async with conn:
            pass
    assert "Error disconnecting the calculator MCP client" in caplog.text
