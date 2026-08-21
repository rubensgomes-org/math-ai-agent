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

"""Calculator MCP client and helper functions.

Provides the ``CalcMCPClient`` class which extends ``fastmcp.Client``
to connect to a remote calculator MCP server, cache its tool list,
and expose inherited ``call_tool()`` / ``list_tools()`` methods.
Also provides the helper functions ``get_calc_mcp_tools()`` to discover
available tools and ``call_tool()`` to invoke a tool over a new
connection.
"""

import asyncio
import json
import logging
import os

import mcp.types
from cryptography.fernet import Fernet
from fastmcp import Client
from fastmcp.client.auth import OAuth
from key_value.aio.stores.disk import DiskStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from math_ai_agent.config.config import (
    get_callback_port,
    get_token_dir,
    get_url,
    is_oauth,
)

logger = logging.getLogger(__name__)


class CalcMCPClient(Client):
    """Calculator MCP client extending ``fastmcp.Client``.

    Builds the correct transport and auth from ``config.yaml``,
    pings on connect, and maintains a class-level tool cache.

    Usage::

        async with CalcMCPClient() as calc:
            result = await calc.call_tool("add", {"a": 1, "b": 2})
    """

    _tools: list[mcp.types.Tool] = []
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize the calculator MCP client."""
        logger.debug("Instantiating CalcMCPClient")
        url = get_url()
        logger.info("Creating HTTP MCP client: %s", url)

        if is_oauth():
            logger.info("OAuth enabled, using OAuthClient")
            token_dir = get_token_dir()
            logger.debug(
                "Creating encrypted disk storage for OAuth tokens: %s",
                token_dir,
            )
            encrypted_storage = FernetEncryptionWrapper(
                key_value=DiskStore(directory=token_dir),
                fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"]),
            )
            oauth = OAuth(
                token_storage=encrypted_storage,
                callback_port=get_callback_port(),
                additional_client_metadata={
                    "token_endpoint_auth_method": ("client_secret_post"),
                },
            )
            super().__init__(url, auth=oauth)
        else:
            super().__init__(url)

    async def __aenter__(self) -> "CalcMCPClient":
        """Connect to the MCP server and populate the tool cache."""
        logger.debug("Connecting to Calculator MCP server")
        await super().__aenter__()
        logger.debug("Pinging MCP server")
        await self.ping()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Disconnect from the MCP server."""
        logger.debug("Closing CalcMCPClient")
        await super().__aexit__(exc_type, exc, tb)

    async def list_tools(self, max_pages: int = 0) -> list[mcp.types.Tool]:
        """Return cached tools, fetching from the server on first call.

        Thread-safe via an ``asyncio.Lock``.  Subsequent calls return
        the cached list without contacting the server.

        Returns:
            The list of tools available on the MCP server.
        """
        async with CalcMCPClient._lock:
            if not CalcMCPClient._tools:
                logger.debug(
                    "CalcMCPClient._tools is empty:" " fetching from MCP server"
                )
                CalcMCPClient._tools = await super().list_tools()
            return CalcMCPClient._tools

    async def to_openai_tools(self) -> list[dict]:
        """Convert cached MCP tools to OpenAI function-calling schema.

        Calls ``list_tools()`` to retrieve the (cached) tool list and
        converts each tool to the OpenAI function-calling format.

        Returns:
            A list of dicts in the OpenAI tool format::

                [
                    {
                        "type": "function",
                        "function": {
                            "name": "add",
                            "description": "Add two numbers",
                            "parameters": { ... }
                        }
                    },
                    ...
                ]
        """
        logger.debug("Converting MCP tools to OpenAI format")
        mcp_tools: list[mcp.types.Tool] = await self.list_tools()
        openai_tools: list[dict] = []
        for tool in mcp_tools:
            func: dict = {"name": tool.name}
            if tool.description:
                func["description"] = tool.description
            func["parameters"] = tool.inputSchema
            openai_tools.append({"type": "function", "function": func})
        logger.debug(
            "Converted %d MCP tools to OpenAI format",
            len(openai_tools),
        )
        return openai_tools

    async def to_responses_tools(self) -> list[dict]:
        """Convert cached MCP tools to Responses API function schema.

        Calls ``list_tools()`` to retrieve the (cached) tool list and
        converts each tool to the Responses API function-calling
        format.  Unlike the Chat Completions format produced by
        ``to_openai_tools()``, the Responses API uses a flat,
        internally-tagged shape with no nested ``function`` object.

        Returns:
            A list of dicts in the Responses tool format::

                [
                    {
                        "type": "function",
                        "name": "add",
                        "description": "Add two numbers",
                        "parameters": { ... }
                    },
                    ...
                ]
        """
        logger.debug("Converting MCP tools to Responses format")
        mcp_tools: list[mcp.types.Tool] = await self.list_tools()
        responses_tools: list[dict] = []
        for tool in mcp_tools:
            func: dict = {"type": "function", "name": tool.name}
            if tool.description:
                func["description"] = tool.description
            func["parameters"] = tool.inputSchema
            responses_tools.append(func)
        logger.debug(
            "Converted %d MCP tools to Responses format",
            len(responses_tools),
        )
        return responses_tools


# -------------------------------------------------
# Helper functions
# -------------------------------------------------
async def get_calc_mcp_tools(
    api_style: str = "chat",
) -> list[dict[str, object]]:
    """Discover available tools from the Calculator MCP server.

    Args:
        api_style: ``"responses"`` for the Responses API tool
            format, anything else for the Chat Completions format.

    Returns:
        Tool definitions discovered from the MCP server, in the
        format matching ``api_style``.
    """
    logger.debug("Discovering Calculator MCP tools (api_style=%s)", api_style)
    async with CalcMCPClient() as calcmcp_client:
        if api_style == "responses":
            tools = await calcmcp_client.to_responses_tools()
        else:
            tools = await calcmcp_client.to_openai_tools()
    logger.debug("Discovered %d MCP tool(s)", len(tools))
    return tools


async def call_tool(tool_name: str, args: dict) -> str:
    """Call a calculator MCP tool over a new connection.

    Args:
        tool_name: The name of the MCP tool to invoke.
        args: The arguments to pass to the tool.

    Returns:
        The string representation of the tool result.

    Raises:
        Exception: If the MCP tool call fails.
    """
    async with CalcMCPClient() as calcmcp_client:
        logger.debug(
            "Calling calculator MCP tool %s with %s",
            tool_name,
            args,
        )
        result = await calcmcp_client.call_tool(tool_name, args)
        logger.debug(
            "Tool %s result:\n%s",
            tool_name,
            json.dumps(result.structured_content, indent=2),
        )
        return str(result.data)
