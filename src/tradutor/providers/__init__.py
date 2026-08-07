"""Adapters e descoberta modular de provedores."""

from tradutor.providers.discovery import (
    ProviderDiscoveryError,
    create_discovered_provider,
    discover_providers,
    get_provider_description,
    provider_factory,
)
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    ProviderError,
    TransientProviderError,
)
from tradutor.providers.machine_translation.google_web import (
    GoogleWebProvider,
    GoogleWebResponseError,
)
from tradutor.providers.openai_compat import (
    DEFAULT_BASE_URL,
    DEFAULT_KEY_NAME,
    DEFAULT_MODEL,
    ConnectionResult,
    OpenAICompatProvider,
)

__all__ = [
    "AuthenticationError",
    "ConnectionResult",
    "DEFAULT_BASE_URL",
    "DEFAULT_KEY_NAME",
    "DEFAULT_MODEL",
    "DefinitiveProviderError",
    "GoogleWebProvider",
    "GoogleWebResponseError",
    "OpenAICompatProvider",
    "ProviderDiscoveryError",
    "ProviderError",
    "TransientProviderError",
    "create_discovered_provider",
    "discover_providers",
    "get_provider_description",
    "provider_factory",
]
