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

"""Shared calculator MCP session that reconnects when it drops.

Provides the ``CalcFastMCPConnection`` class, which owns one connected
``CalcFastMCPClient`` for the app's lifetime and replaces it with a new one
when the session with the MCP server is lost.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AsyncExitStack
from types import TracebackType

from fastmcp.client.client import CallToolResult

from math_ai_agent.mcp.calc_client import CalcFastMCPClient

logger = logging.getLogger(__name__)


class CalcFastMCPConnection:
    """One calculator FastMCP session shared by every request.

    A failed call whose client is no longer connected is retried once on
    a new session.  Failures that leave the client connected, such as
    tool errors, are raised without a retry.

    Usage::

        async with CalcFastMCPConnection() as calc:
            result = await calc.call_tool("add", {"a": 1, "b": 2})
    """

    def __init__(
        self,
        client_factory: Callable[[], CalcFastMCPClient] = CalcFastMCPClient,
    ) -> None:
        """Create the connection without connecting a session.

        Args:
            client_factory: Builds each new, unconnected MCP client.
        """
        logger.debug("Initializing CalcFastMCPConnection")
        self._client_factory = client_factory
        self._reconnect_lock = asyncio.Lock()
        self._exit_stack = AsyncExitStack()
        self._client: CalcFastMCPClient | None = None

    async def __aenter__(self) -> "CalcFastMCPConnection":
        """Connect to the MCP server."""
        logger.debug("Connecting to the MCP server")
        await self._connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Disconnect the current MCP session."""
        logger.debug("Disconnecting the MCP session")
        await self._disconnect()

    async def to_chat_completions_tools(self) -> list[dict]:
        """Return the MCP tools in the Chat Completions format."""
        logger.debug("Return the MCP tools in the Chat Completions API format")
        return await self._connected_client().to_chat_completions_tools()

    async def to_responses_tools(self) -> list[dict]:
        """Return the MCP tools in the Responses API format."""
        logger.debug("Return the MCP tools in the Responses API format")
        return await self._connected_client().to_responses_tools()

    async def call_tool(self, tool_name: str, args: dict) -> CallToolResult:
        """Call an MCP tool, retrying once if the session is lost.

        Args:
            tool_name: The name of the MCP tool to invoke.
            args: The arguments to pass to the tool.

        Returns:
            The tool result.

        Raises:
            Exception: If the tool call fails for a reason other than a
                lost session, or fails again after reconnecting.
        """
        client = self._client
        if client is None or not client.is_connected():
            client = await self._reconnect(client)
        try:
            return await client.call_tool(tool_name, args)
        # A lost connection surfaces as several exception types, so the
        # connection state, not the type, decides whether to retry.
        except Exception as error:  # pylint: disable=broad-exception-caught
            if client.is_connected():
                raise
            logger.warning(
                "MCP connection lost while calling tool %s; reconnecting: %r",
                tool_name,
                error,
            )
        client = await self._reconnect(client)
        return await client.call_tool(tool_name, args)

    def _connected_client(self) -> CalcFastMCPClient:
        """Return the current client, or fail if none is connected."""
        if self._client is None:
            raise RuntimeError("CalcFastMCPConnection is not connected")
        return self._client

    async def _reconnect(
        self, failed: CalcFastMCPClient | None
    ) -> CalcFastMCPClient:
        """Replace the failed client with a new, connected one.

        Tasks that fail on the same client at once reconnect only once;
        the others reuse the client connected by the first.
        """
        async with self._reconnect_lock:
            if self._client is not failed and self._client is not None:
                return self._client
            await self._disconnect()
            logger.info("Reconnecting to the calculator MCP server")
            return await self._connect()

    async def _connect(self) -> CalcFastMCPClient:
        """Connect a new MCP client and make it the current one."""
        exit_stack = AsyncExitStack()
        logger.debug("Creating the FastMCP client")
        client = await exit_stack.enter_async_context(self._client_factory())
        self._exit_stack, self._client = exit_stack, client
        return client

    async def _disconnect(self) -> None:
        """Disconnect the current MCP client, logging any error."""
        self._client = None
        try:
            await self._exit_stack.aclose()
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Error disconnecting the calculator MCP client: %r", error
            )
