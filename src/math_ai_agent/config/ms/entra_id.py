"""Microsoft Entra ID token provider for models hosted on Microsoft Foundry.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
"""

from collections.abc import Awaitable, Callable

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


def token_provider(
    credential: DefaultAzureCredential,
) -> Callable[[], Awaitable[str]]:
    """Return an async callable yielding a cached, auto-renewed token."""
    return get_bearer_token_provider(credential, COGNITIVE_SERVICES_SCOPE)
