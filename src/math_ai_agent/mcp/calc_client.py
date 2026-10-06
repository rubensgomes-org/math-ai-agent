"""Calculator MCP client.

Provides the ``CalcMCPClient`` class which extends ``fastmcp.Client``
to connect to a remote calculator MCP server.
"""

import logging
import os
from pathlib import Path

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


class CalcMCPClient(Client):
    """Calculator FastMCP client extending ``fastmcp.Client``.

    Usage::

        async with CalcMCPClient() as calc:
            result = await calc.call_tool("add", {"a": 1, "b": 2})
    """

    @staticmethod
    def _create_token_store(token_dir: str) -> FileTreeStore:
        """Create a JSON file store for OAuth tokens under ``token_dir``."""
        directory = Path(token_dir).expanduser()
        logger.debug("creating token store: %s", directory)
        directory.mkdir(parents=True, exist_ok=True)
        return FileTreeStore(
            data_directory=directory,
            key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(
                directory
            ),
            collection_sanitization_strategy=(
                FileTreeV1CollectionSanitizationStrategy(directory)
            ),
        )

    def __init__(self) -> None:
        mcp_config = get_config().server.calculator_mcp
        server_url: str = mcp_config.url
        logger.debug("MCP server URL: %s", server_url)

        if mcp_config.is_oauth:
            token_dir = mcp_config.token_dir
            logger.debug(
                "Creating encrypted file storage for OAuth tokens: %s",
                token_dir,
            )
            encrypted_storage = FernetEncryptionWrapper(
                key_value=self._create_token_store(token_dir),
                fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"]),
            )
            oauth = OAuth(
                token_storage=encrypted_storage,
                callback_port=mcp_config.callback_port,
                additional_client_metadata={
                    "token_endpoint_auth_method": ("client_secret_post"),
                },
            )
            super().__init__(server_url, auth=oauth)
        else:
            super().__init__(server_url)
