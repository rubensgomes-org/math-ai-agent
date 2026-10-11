"""Azure App Configuration loader for the config.yaml sections.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
"""

import logging
from collections.abc import Mapping
from typing import Any

from azure.appconfiguration.provider import SettingSelector, load
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

KEY_PREFIX = "ca-mathagent/"
KEY_SEPARATOR = "/"


def load_app_configuration(endpoint: str, label: str) -> dict[str, Any]:
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
