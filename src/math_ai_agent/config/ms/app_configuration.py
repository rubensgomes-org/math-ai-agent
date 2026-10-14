"""Azure App Configuration loader for the config.yaml sections.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
"""

import logging
import os
from collections.abc import Mapping
from typing import Any

from azure.appconfiguration.provider import SettingSelector, load
from azure.identity import DefaultAzureCredential

from math_ai_agent.config.models import KEY_VAULT_URI_CONTEXT, AppConfig

logger = logging.getLogger(__name__)

KEY_PREFIX = "ca-mathagent/"
KEY_SEPARATOR = "/"

# KEY_VAULT_URI_ENV is an environment variable set in every Azure
# Container App by the "azure-iac" Terraform "container-apps" module.
KEY_VAULT_URI_ENV = "KEY_VAULT_URI"

# CONTAINER_APP_NAME is injected into every container app at runtime. Its
# environment suffix is the App Configuration label.
CONTAINER_APP_NAME_ENV = "CONTAINER_APP_NAME"


def load_app_configuration(
    endpoint: str, logging_config: dict[str, Any]
) -> AppConfig:
    """Return the Azure config; ``logging`` comes from ``logging_config``."""
    logger.debug(
        "Loading config from Azure App Configuration endpoint: %s", endpoint
    )
    mapping = _read_store(endpoint, _environment_label())
    mapping["logging"] = logging_config
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


def _read_store(endpoint: str, label: str) -> dict[str, Any]:
    """Return the store's ``KEY_PREFIX`` key-values as a nested mapping."""
    logger.info(
        "Loading App Configuration from %s with label %s", endpoint, label
    )
    selector = SettingSelector(key_filter=f"{KEY_PREFIX}*", label_filter=label)
    with (
        DefaultAzureCredential() as credential,
        load(
            endpoint=endpoint,
            credential=credential,
            selects=[selector],
            trim_prefixes=[KEY_PREFIX],
        ) as provider,
    ):
        settings = dict(provider)
    logger.info("Loaded %d App Configuration settings", len(settings))
    return _nest(settings)


def _nest(settings: Mapping[str, Any]) -> dict[str, Any]:
    """Split ``a/b/c`` keys into nested dicts."""
    nested: dict[str, Any] = {}
    for key, value in settings.items():
        *parents, leaf = key.split(KEY_SEPARATOR)
        node = nested
        for parent in parents:
            node = node.setdefault(parent, {})
        node[leaf] = value
    return nested
