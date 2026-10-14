"""Configuration helpers — loads config.yaml and configures logging."""

import functools
import logging
import logging.config
import os
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from math_ai_agent.config.models import AppConfig
from math_ai_agent.config.ms.app_configuration import load_app_configuration

logger = logging.getLogger(__name__)

# APP_CONFIG_ENDPOINT_ENV is an environment variable set in every Azure
# Container App by the "azure-iac" Terraform "container-apps" module.
APP_CONFIG_ENDPOINT_ENV = "APP_CONFIG_ENDPOINT"

# HTTPX_LOG_LEVEL_ENV overrides the "httpx" logger level from config.yaml.
# httpx itself no longer reads this variable.
HTTPX_LOG_LEVEL_ENV = "HTTPX_LOG_LEVEL"
HTTPX_LOGGER_NAME = "httpx"


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
    logger.debug("Loading config from YAML file: %s", path)
    return AppConfig.model_validate(_read_yaml(path))


def _read_yaml(path: Path) -> dict[str, Any]:
    """Return the YAML mapping in the file at ``path``."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


################################################################################
# The following Public APIs define where and how the config is loaded.         #
################################################################################


@functools.cache
def get_config() -> AppConfig:
    """Return the application config, loaded once on first call.

    With ``APP_CONFIG_ENDPOINT`` set, loads from Azure; else from YAML.
    """
    logger.debug(
        "APP_CONFIG_ENDPOINT: %s", os.environ.get(APP_CONFIG_ENDPOINT_ENV)
    )
    endpoint = os.environ.get(APP_CONFIG_ENDPOINT_ENV)
    if endpoint:
        logger.info(
            "Loading config from Azure App Configuration endpoint: %s", endpoint
        )
        # Only the logging section comes from the YAML file.  The Dockerfile
        # sets MATHAIAGENT_CONFIG=/etc/math-ai-agent/config.yaml and copies
        # config/config_docker.yaml to that path.
        logging_config = _read_yaml(_resolve_config_path())["logging"]
        return load_app_configuration(endpoint, logging_config)
    logger.debug("Loading config from YAML file: %s", _resolve_config_path())
    return _load_config(_resolve_config_path())


def configure_logging() -> None:
    """Apply config.yaml logging, then any ``HTTPX_LOG_LEVEL`` override."""
    logging.config.dictConfig(get_config().logging)
    logger.debug("Loaded config from %s", _resolve_config_path())
    httpx_level = os.environ.get(HTTPX_LOG_LEVEL_ENV)
    if httpx_level:
        logging.getLogger(HTTPX_LOGGER_NAME).setLevel(httpx_level.upper())
        logger.info("httpx log level set to %s", httpx_level.upper())
