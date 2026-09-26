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

"""Calculator MCP client.

Provides the ``CalcMCPClient`` class which extends ``fastmcp.Client``
to connect to a remote calculator MCP server and convert its tools to
the OpenAI function-calling formats.
"""

import logging
import os
from pathlib import Path

import mcp.types
from cryptography.fernet import Fernet
from fastmcp import Client
from fastmcp.client.auth import OAuth
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from math_ai_agent.config.config import get_config

logger = logging.getLogger(__name__)


def _create_token_store(token_dir: str) -> FileTreeStore:
    """Create a JSON file store for OAuth tokens under ``token_dir``.

    The sanitization strategies keep OAuth keys, which contain URL
    characters, valid as file and directory names.
    """
    directory = Path(token_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return FileTreeStore(
        data_directory=directory,
        key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(directory),
        collection_sanitization_strategy=(
            FileTreeV1CollectionSanitizationStrategy(directory)
        ),
    )


class CalcMCPClient(Client):
    """Calculator MCP client extending ``fastmcp.Client``.

    Builds the correct transport and auth from ``config.yaml``.

    Usage::

        async with CalcMCPClient() as calc:
            result = await calc.call_tool("add", {"a": 1, "b": 2})
    """

    def __init__(self) -> None:
        """Initialize the calculator MCP client."""
        logger.debug("Instantiating CalcMCPClient")
        mcp_config = get_config().server.calculator_mcp
        url = mcp_config.url
        logger.info("Creating HTTP MCP client: %s", url)

        if mcp_config.is_oauth:
            logger.info("OAuth enabled, using OAuthClient")
            token_dir = mcp_config.token_dir
            logger.debug(
                "Creating encrypted file storage for OAuth tokens: %s",
                token_dir,
            )
            encrypted_storage = FernetEncryptionWrapper(
                key_value=_create_token_store(token_dir),
                fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"]),
            )
            oauth = OAuth(
                token_storage=encrypted_storage,
                callback_port=mcp_config.callback_port,
                additional_client_metadata={
                    "token_endpoint_auth_method": ("client_secret_post"),
                },
            )
            super().__init__(url, auth=oauth)
        else:
            super().__init__(url)

    async def __aenter__(self) -> "CalcMCPClient":
        """Connect to the MCP server."""
        logger.debug("Connecting to Calculator MCP server")
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Disconnect from the MCP server."""
        logger.debug("Closing CalcMCPClient")
        await super().__aexit__(exc_type, exc, tb)

    async def to_openai_tools(self) -> list[dict]:
        """Convert MCP tools to OpenAI function-calling schema.

        Calls ``list_tools()`` to retrieve the tool list and
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
        logger.debug("Calling Calculator MCP Server to list tools")
        mcp_tools: list[mcp.types.Tool] = await self.list_tools()
        logger.debug("mcp_tools: %s", mcp_tools)
        logger.debug("Converting %d MCP tools to OpenAI format", len(mcp_tools))
        openai_tools: list[dict] = []
        for tool in mcp_tools:
            func: dict = {"name": tool.name}
            if tool.description:
                func["description"] = tool.description
            func["parameters"] = tool.input_schema
            openai_tools.append({"type": "function", "function": func})
        logger.debug(
            "Converted %d MCP tools to OpenAI format",
            len(openai_tools),
        )
        return openai_tools

    async def to_responses_tools(self) -> list[dict]:
        """Convert MCP tools to Responses API function schema.

        Calls ``list_tools()`` to retrieve the tool list and
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
        logger.debug("Calling Calculator MCP Server to list tools")
        mcp_tools: list[mcp.types.Tool] = await self.list_tools()
        logger.debug("mcp_tools: %s", mcp_tools)
        logger.debug(
            "Converting %d MCP tools to Responses format", len(mcp_tools)
        )
        responses_tools: list[dict] = []
        for tool in mcp_tools:
            func: dict = {"type": "function", "name": tool.name}
            if tool.description:
                func["description"] = tool.description
            func["parameters"] = tool.input_schema
            responses_tools.append(func)
        logger.debug(
            "Converted %d MCP tools to Responses format",
            len(responses_tools),
        )
        return responses_tools
