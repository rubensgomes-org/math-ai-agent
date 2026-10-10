"""Calculator MCP client."""

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
    """Calculator MCP client with optional encrypted OAuth token storage."""

    def __init__(self) -> None:
        """Initializes the client from the ``calculator_mcp`` config."""
        mcp_config = get_config().server.calculator_mcp
        self._server_url: str = mcp_config.url
        logger.debug("MCP server URL: %s", self._server_url)
        if not mcp_config.is_oauth:
            logger.info("Connecting to local MCP server: %s", self._server_url)
            super().__init__(self._server_url)
            return

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
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
        logger.info(
            "Using OAuth to authenticate to remote MCP server: %s",
            self._server_url,
        )
        super().__init__(self._server_url, auth=oauth)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the Calculator MCP client."""
        logger.debug("Closing Calculator MCP client: %s", self._server_url)
        await super().__aexit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def _create_token_store(token_dir: str) -> FileTreeStore:
        """Creates a JSON file store for OAuth tokens under ``token_dir``."""
        directory = Path(token_dir).expanduser()
        logger.debug("Creating token store: %s", directory)
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
