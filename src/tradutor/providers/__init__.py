"""Adapters e descoberta modular de provedores."""

from tradutor.domain import ProviderCapabilities, ProviderFamily
from tradutor.providers.discovery import (
    ConnectionResult,
    ProviderDiscoveryError,
    create_discovered_provider,
    discover_providers,
    get_provider_description,
    provider_factory,
    test_provider_connection,
)
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    ProviderError,
    TransientProviderError,
)
from tradutor.providers.llm.openai_compat import (
    DEFAULT_BASE_URL,
    DEFAULT_KEY_NAME,
    DEFAULT_MODEL,
    OpenAICompatProvider,
)
from tradutor.providers.machine_translation.google_web import (
    GoogleWebProvider,
    GoogleWebResponseError,
)


def provider_capabilities(
    provider_id: str, family: ProviderFamily | str | None = None
) -> ProviderCapabilities | None:
    """Capabilities de um provider selecionado, sem instanciar o adapter.

    Devolve ``None`` quando o provider não é conhecido, para que o
    chamador use o fallback padrão em vez de quebrar.
    """
    try:
        return get_provider_description(provider_id, family=family).capabilities
    except ProviderDiscoveryError:
        return None


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
    "provider_capabilities",
    "provider_factory",
    "test_provider_connection",
]
