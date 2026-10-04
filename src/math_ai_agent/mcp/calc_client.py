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

"""Calculator MCP client.

Provides the ``CalcMCPClient`` class which extends ``fastmcp.Client``
to connect to a remote calculator MCP server.
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
    """Create a JSON file store for OAuth tokens under ``token_dir``."""
    directory = Path(token_dir).expanduser()
    logger.debug("creating token store: %s", directory)
    directory.mkdir(parents=True, exist_ok=True)
    return FileTreeStore(
        data_directory=directory,
        key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(directory),
        collection_sanitization_strategy=(
            FileTreeV1CollectionSanitizationStrategy(directory)
        ),
    )


class CalcMCPClient(Client):
    """Calculator FastMCP client extending ``fastmcp.Client``.

    Usage::

        async with CalcMCPClient() as calc:
            result = await calc.call_tool("add", {"a": 1, "b": 2})
    """

    def __init__(self) -> None:
        mcp_config = get_config().server.calculator_mcp
        url = mcp_config.url
        logger.debug("MCP server URL: %s", url)

        if mcp_config.is_oauth:
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

    async def tools_definitions(self) -> list[dict]:
        """Return each MCP tool's name, description, and parameters."""
        logger.info("Calling Calculator MCP Server to list tools")
        mcp_tools: list[mcp.types.Tool] = await self.list_tools()
        logger.debug("mcp_tools: %s", mcp_tools)
        functions: list[dict] = []
        for tool in mcp_tools:
            function: dict = {"name": tool.name}
            if tool.description:
                function["description"] = tool.description
            function["parameters"] = tool.input_schema
            functions.append(function)
        return functions
