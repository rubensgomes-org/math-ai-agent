"""Azure Key Vault reader for the LLM API key."""

import logging

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)

SECRET_PREFIX = "ca-mathagent--"

# How does the Azure Container Apps get permission to read the Key Vault secret?
#
# All Azure Container Apps have the shared UAMID "id-rgomesapp-dev" attached to
# their managed identity. This UAMID is used to grant the container apps
# access to the Key Vault based on the role "Key Vault Secrets User" that has
# been added to that UAMID


def secret_name(env_var: str) -> str:
    """Return the Key Vault secret name for an environment variable name."""
    return SECRET_PREFIX + env_var.replace("_", "-")


def read_secret(vault_uri: str, name: str) -> str:
    """Return the non-empty value of secret ``name`` in ``vault_uri``."""
    logger.info("Reading secret %s from Key Vault %s", name, vault_uri)
    with (
        DefaultAzureCredential() as credential,
        SecretClient(vault_url=vault_uri, credential=credential) as client,
    ):
        value = client.get_secret(name).value
    if not value:
        raise ValueError(f"Key Vault secret {name} in {vault_uri} is empty.")
    return value
