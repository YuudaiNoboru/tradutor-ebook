"""Adapters de provedores de LLM (camada externa da arquitetura hexagonal)."""

from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    ProviderError,
    TransientProviderError,
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
    "OpenAICompatProvider",
    "ProviderError",
    "TransientProviderError",
]
