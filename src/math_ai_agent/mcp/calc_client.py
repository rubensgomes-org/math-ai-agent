"""Calculator MCP client."""

import logging
import os
from pathlib import Path
from types import TracebackType

from ai_utils_lib.config.models import MCP
from cryptography.fernet import Fernet
from fastmcp import Client
from fastmcp.client.auth import OAuth
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30
_INIT_TIMEOUT_SECONDS = 10
_ENCRYPTION_KEY_ENV = "OAUTH_STORAGE_ENCRYPTION_KEY"
_TOKEN_DIR_MODE = 0o700
# Send the client secret in the token request body (RFC 7591).
_OAUTH_CLIENT_METADATA = {"token_endpoint_auth_method": "client_secret_post"}


class CalcMCPClient(Client):
    """Calculator MCP client with optional encrypted OAuth token storage."""

    def __init__(self, config: MCP) -> None:
        """Create the client for the ``mcp.calculator`` config."""
        self._server_url = str(config.url)
        logger.info(
            "Calculator MCP client for %s (OAuth=%s)",
            self._server_url,
            config.is_oauth,
        )
        super().__init__(
            self._server_url,
            auth=self._create_oauth(config) if config.is_oauth else None,
            timeout=_TIMEOUT_SECONDS,
            init_timeout=_INIT_TIMEOUT_SECONDS,
        )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the Calculator MCP client."""
        logger.debug("Closing Calculator MCP client: %s", self._server_url)
        await super().__aexit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def _create_oauth(config: MCP) -> OAuth:
        """Create OAuth with tokens encrypted under ``config.token_dir``."""
        encrypted_storage = FernetEncryptionWrapper(
            key_value=CalcMCPClient._create_token_store(config.token_dir),
            fernet=_fernet_from_env(),
        )
        return OAuth(
            token_storage=encrypted_storage,
            callback_port=config.callback_port,
            additional_client_metadata=_OAUTH_CLIENT_METADATA,
        )

    @staticmethod
    def _create_token_store(token_dir: str) -> FileTreeStore:
        """Create an owner-only JSON file store for OAuth tokens."""
        directory = Path(token_dir).expanduser()
        logger.debug("Creating token store: %s", directory)
        directory.mkdir(mode=_TOKEN_DIR_MODE, parents=True, exist_ok=True)
        directory.chmod(_TOKEN_DIR_MODE)
        return FileTreeStore(
            data_directory=directory,
            key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(
                directory
            ),
            collection_sanitization_strategy=(
                FileTreeV1CollectionSanitizationStrategy(directory)
            ),
        )


def _fernet_from_env() -> Fernet:
    """Return the token encryption key from the environment."""
    key = os.environ.get(_ENCRYPTION_KEY_ENV)
    if not key:
        raise ValueError(
            f"{_ENCRYPTION_KEY_ENV} must be set when mcp.calculator.is_oauth"
            " is true; generate one with Fernet.generate_key()"
        )
    try:
        return Fernet(key)
    except ValueError as error:
        raise ValueError(
            f"{_ENCRYPTION_KEY_ENV} is not a valid Fernet key"
        ) from error
