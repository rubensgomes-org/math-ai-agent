"""Pydantic models for the config.yaml sections.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
"""

import logging
import os
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, ValidationInfo, model_validator

from math_ai_agent.config.ms import key_vault

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT_SECONDS = 120.0

# KEY_VAULT_URI_CONTEXT is the key in the pydantic validation context that
# contains the Key Vault URI.
KEY_VAULT_URI_CONTEXT = "key_vault_uri"


class LLMConfig(BaseModel):
    """The ``llm`` section of config.yaml.

    ``api_key`` is empty when ``is_azure``, since the LLM client then uses
    Entra ID tokens. Otherwise it is read at construction from Key Vault
    when the validation context has a vault URI, else from the
    ``api_key_env`` environment variable. It is excluded from ``repr()``
    and ``model_dump()``.
    """

    is_azure: bool = False
    api_style: Literal["chat", "responses"] = "chat"
    model_base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key_env: str
    system_instructions: str
    timeout_seconds: float = Field(default=DEFAULT_LLM_TIMEOUT_SECONDS, gt=0)
    max_concurrent_prompts: int = Field(default=10, gt=0)
    is_stateful: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    api_key: str = Field(default="", exclude=True, repr=False)

    @model_validator(mode="after")
    def _load_api_key(self, info: ValidationInfo) -> Self:
        """Set ``api_key`` from Key Vault or the environment."""
        logger.debug("info.context: %s", info.context)
        if self.is_azure:
            logger.debug("LLM API key not needed; using Entra ID tokens")
            return self
        # The vault URI is in the context only in Azure mode; see
        # app_configuration.load_app_configuration.
        vault_uri = (info.context or {}).get(KEY_VAULT_URI_CONTEXT)
        if vault_uri:
            logger.debug(
                "Reading LLM API key from Key Vault: %s", self.api_key_env
            )
            name = key_vault.secret_name(self.api_key_env)
            self.api_key = key_vault.read_secret(vault_uri, name)
            return self
        logger.debug("LLM API key environment variable: %s", self.api_key_env)
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            error = f"{self.api_key_env} environment variable is not set."
            logger.error(error)
            raise ValueError(error)
        self.api_key = api_key
        return self


class CalculatorMCPConfig(BaseModel):
    """The ``server.calculator_mcp`` section of config.yaml."""

    url: str
    is_oauth: bool = False
    token_dir: str
    callback_port: int


class ServerConfig(BaseModel):
    """The ``server`` section of config.yaml."""

    calculator_mcp: CalculatorMCPConfig


class WebConfig(BaseModel):
    """The ``web`` section of config.yaml: where the app listens."""

    host: str = "127.0.0.1"
    port: int = 9090


class AppConfig(BaseModel):
    """The full config.yaml; ``logging`` is a ``dictConfig`` mapping."""

    llm: LLMConfig
    server: ServerConfig
    web: WebConfig = WebConfig()
    logging: dict[str, Any]
