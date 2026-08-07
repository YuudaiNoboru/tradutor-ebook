"""Módulo descobrível do provider DeepSeek, compatível com OpenAI."""

from tradutor.domain import (
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
)
from tradutor.providers.openai_compat import OpenAICompatProvider

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
        max_concurrency=4,
        reports_token_usage=True,
        supports_model_listing=True,
        has_pricing=True,
    ),
    display_name="DeepSeek",
    description="API de chat compatível com OpenAI.",
)


def create_provider(secret_store, **kwargs):
    kwargs.setdefault("base_url", "https://api.deepseek.com")
    kwargs.setdefault("model", "deepseek-chat")
    kwargs.setdefault("key_name", "DEEPSEEK_API_KEY")
    return OpenAICompatProvider(secret_store, **kwargs)
