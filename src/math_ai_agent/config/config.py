"""Configuration helpers — loads config.yaml and configures logging."""

import functools
import logging
import logging.config
import os
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, ValidationInfo, model_validator

from math_ai_agent.config import key_vault
from math_ai_agent.config.app_configuration import load_app_configuration

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT_SECONDS = 120.0

# APP_CONFIG_ENDPOINT_ENV is an environment variable set in every Azure
# Container App by the "azure-iac" Terraform "container-apps" module.
APP_CONFIG_ENDPOINT_ENV = "APP_CONFIG_ENDPOINT"

# KEY_VAULT_URI_ENV is an environment variable set in every Azure
# Container App by the "azure-iac" Terraform "container-apps" module.
KEY_VAULT_URI_ENV = "KEY_VAULT_URI"

# CONTAINER_APP_NAME is injected into every container app at runtime. This
# environment variable is used by config.py to choose the App Configuration
# label in azure mode.
CONTAINER_APP_NAME_ENV = "CONTAINER_APP_NAME"

# KEY_VAULT_URI_CONTEXT is the key in the pydantic validation context that
# contains the Key Vault URI.
KEY_VAULT_URI_CONTEXT = "key_vault_uri"


class LLMConfig(BaseModel):
    """The ``llm`` section of config.yaml.

    ``api_key`` is read at construction from Key Vault when the validation
    context has a vault URI, else from the ``api_key_env`` environment
    variable. It is excluded from ``repr()`` and ``model_dump()``.
    """

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


def _resolve_config_path() -> Path:
    """Return the config.yaml path.

    Resolution order:

    1. The ``MATHAIAGENT_CONFIG`` environment variable, when set.
    2. The ``config.yaml`` bundled inside the
       ``math_ai_agent.config`` package.

    Returns:
        The resolved path to config.yaml.
    """
    env_path = os.environ.get("MATHAIAGENT_CONFIG")
    if env_path:
        return Path(env_path)
    return Path(str(files("math_ai_agent.config").joinpath("config.yaml")))


def _load_config(path: Path) -> AppConfig:
    """Parse and validate the config file at ``path``.

    Raises:
        pydantic.ValidationError: If the file does not match the models.
    """
    return AppConfig.model_validate(_read_yaml(path))


def _read_yaml(path: Path) -> dict[str, Any]:
    """Return the YAML mapping in the file at ``path``."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_azure_config(endpoint: str) -> AppConfig:
    """Return the config from App Configuration and Key Vault.

    Only ``logging`` comes from the YAML file.
    """
    mapping = load_app_configuration(endpoint, _environment_label())
    mapping["logging"] = _read_yaml(_resolve_config_path())["logging"]
    context = {KEY_VAULT_URI_CONTEXT: _required_env(KEY_VAULT_URI_ENV)}
    return AppConfig.model_validate(mapping, context=context)


def _environment_label() -> str:
    """Return the environment suffix of the container app name."""
    app_name = _required_env(CONTAINER_APP_NAME_ENV)
    _, separator, label = app_name.rpartition("-")
    if not separator or not label:
        raise ValueError(
            f"{CONTAINER_APP_NAME_ENV} '{app_name}' has no environment suffix."
        )
    return label


def _required_env(name: str) -> str:
    """Return the non-empty value of environment variable ``name``."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} environment variable is not set.")
    return value


################################################################################
# The following Public APIs define where and how the config is loaded.         #
################################################################################


@functools.cache
def get_config() -> AppConfig:
    """Return the application config, loaded once on first call.

    With ``APP_CONFIG_ENDPOINT`` set, loads from Azure; else from YAML.
    """
    endpoint = os.environ.get(APP_CONFIG_ENDPOINT_ENV)
    if endpoint:
        logger.debug(
            "Loading config from Azure App Configuration endpoint: %s", endpoint
        )
        return _load_azure_config(endpoint)
    logger.debug("Loading config from YAML file: %s", _resolve_config_path())
    return _load_config(_resolve_config_path())


def configure_logging() -> None:
    """Apply the logging configuration from config.yaml."""
    logging.config.dictConfig(get_config().logging)
    logger.debug("Loaded config from %s", _resolve_config_path())
