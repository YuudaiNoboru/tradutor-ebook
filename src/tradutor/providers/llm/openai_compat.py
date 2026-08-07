"""Módulo LLM de referência para o adapter OpenAI-compatível.

O adapter continua disponível em ``tradutor.providers.openai_compat`` para
compatibilidade com integrações existentes; este módulo é a unidade que a
descoberta modular apresenta à aplicação.
"""

from __future__ import annotations

from tradutor.domain import (
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
)
from tradutor.providers.openai_compat import (
    DEFAULT_BASE_URL,
    DEFAULT_KEY_NAME,
    DEFAULT_MODEL,
    OpenAICompatProvider,
)

DESCRIPTION = ProviderDescription(
    identity=ProviderIdentity(ProviderFamily.LLM, "openai-compatible", "1", "openai-chat"),
    capabilities=ProviderCapabilities(
        family=ProviderFamily.LLM,
        supports_glossary=True,
        supports_priming=True,
        supports_term_policy=True,
        supports_html=True,
        requires_credentials=True,
        max_batch_items=32,
        max_concurrency=4,
        reports_token_usage=True,
        supports_model_listing=True,
        has_pricing=False,
    ),
    display_name="OpenAI compatível",
    description="Provider de referência para APIs compatíveis com o protocolo OpenAI.",
)


def create_provider(secret_store, **kwargs):
    """Cria o adapter compartilhado sem colocar segredos na configuração."""

    return OpenAICompatProvider(secret_store, **kwargs)


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_KEY_NAME",
    "DEFAULT_MODEL",
    "DESCRIPTION",
    "OpenAICompatProvider",
    "create_provider",
]
