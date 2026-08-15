from __future__ import annotations

from typing import Any

from tradutor.domain import (
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
    SecretStore,
)
from tradutor.providers.llm.openai_compat import DEFAULT_MODEL, OpenAICompatProvider

DESCRIPTION = ProviderDescription(
    identity=ProviderIdentity(ProviderFamily.LLM, "deepseek", "1", "openai-chat"),
    capabilities=ProviderCapabilities(
        family=ProviderFamily.LLM,
        supports_glossary=True,
        supports_priming=True,
        supports_term_policy=True,
        supports_html=True,
        requires_credentials=True,
        max_batch_items=32,
        max_concurrency=20,
        latency_seconds=90.0,
        max_output_tokens=8192,
        reports_token_usage=True,
        supports_model_listing=True,
        has_pricing=True,
    ),
    display_name="DeepSeek",
    description="API de chat compatível com OpenAI.",
)


def create_provider(secret_store: SecretStore, **kwargs: Any) -> OpenAICompatProvider:
    kwargs.setdefault("base_url", "https://api.deepseek.com")
    kwargs.setdefault("model", DEFAULT_MODEL)
    kwargs.setdefault("key_name", "DEEPSEEK_API_KEY")
    kwargs.setdefault("thinking", False)
    return OpenAICompatProvider(secret_store, **kwargs)
