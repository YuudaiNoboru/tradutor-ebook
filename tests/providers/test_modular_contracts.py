"""Contratos da descoberta e isolamento entre famílias de providers."""

from __future__ import annotations

from types import ModuleType

import pytest

from tradutor.domain import (
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
    ProviderStability,
    Usage,
)
from tradutor.providers.discovery import (
    ProviderDiscoveryError,
    create_discovered_provider,
    discover_providers,
    get_provider_description,
    provider_factory,
)


def _module(name: str, provider_id: str = "fake") -> ModuleType:
    module = ModuleType(name)
    module.DESCRIPTION = ProviderDescription(
        identity=ProviderIdentity(ProviderFamily.MACHINE_TRANSLATION, provider_id, "1", "test"),
        capabilities=ProviderCapabilities(
            family=ProviderFamily.MACHINE_TRANSLATION,
            requires_credentials=False,
            stability=ProviderStability.EXPERIMENTAL,
            reports_token_usage=False,
            reports_character_usage=True,
            supports_model_listing=False,
        ),
        display_name="Fake",
    )
    module.create_provider = lambda **_: object()
    return module


def test_usage_accepts_unreported_tokens_and_counts_blocks():
    usage = Usage(None, None, characters=120, blocks=3)

    assert usage.total_tokens is None
    assert usage.character_count == 120
    assert usage.block_count == 3


def test_discovery_rejects_duplicate_ids():
    with pytest.raises(ProviderDiscoveryError, match="duplicado"):
        discover_providers(modules=[_module("one"), _module("two")])


def test_discovery_rejects_module_without_factory():
    module = _module("invalid")
    del module.create_provider

    with pytest.raises(ProviderDiscoveryError, match="create_provider"):
        discover_providers(modules=[module])


def test_discovery_filters_family_without_central_registry():
    llm = _module("llm", "llm-fake")
    llm.DESCRIPTION = ProviderDescription(
        identity=ProviderIdentity(ProviderFamily.LLM, "llm-fake", "1", "test"),
        capabilities=ProviderCapabilities(family=ProviderFamily.LLM),
        display_name="LLM fake",
    )
    found = discover_providers(ProviderFamily.LLM, modules=[llm, _module("machine")])

    assert [item.provider_id for item in found] == ["llm-fake"]


class _Secrets:
    def get(self, name: str) -> str | None:
        return "test-key" if name == "DEEPSEEK_API_KEY" else None


def test_deepseek_module_preserves_defaults_and_secret_alias():
    from tradutor.providers.llm.deepseek import create_provider

    provider = create_provider(_Secrets())

    assert provider.base_url == "https://api.deepseek.com"
    assert provider.model == "deepseek-chat"
    assert provider._key_name == "DEEPSEEK_API_KEY"
    assert provider.identity.family is ProviderFamily.LLM
    assert provider.identity.provider_id == "deepseek"
    assert provider.capabilities.supports_glossary


def test_discovery_rejects_invalid_family():
    with pytest.raises(ProviderDiscoveryError, match="família"):
        discover_providers("pombo")


def test_discovery_unknown_package_yields_no_providers():
    assert discover_providers(package="tradutor.nao_existe") == ()


def test_discovery_rejects_module_without_description():
    module = ModuleType("sem-descricao")
    module.create_provider = lambda **_: object()

    with pytest.raises(ProviderDiscoveryError, match="DESCRIPTION"):
        discover_providers(modules=[module])


def test_discovery_rejects_inconsistent_family_metadata():
    module = _module("inconsistente")
    module.DESCRIPTION = ProviderDescription(
        identity=ProviderIdentity(ProviderFamily.LLM, "inconsistente", "1", "test"),
        capabilities=ProviderCapabilities(family=ProviderFamily.MACHINE_TRANSLATION),
        display_name="Inconsistente",
    )

    with pytest.raises(ProviderDiscoveryError, match="inconsistentes"):
        discover_providers(modules=[module])


def test_discovery_rejects_empty_display_name():
    module = _module("sem-nome")
    module.DESCRIPTION = ProviderDescription(
        identity=module.DESCRIPTION.identity,
        capabilities=module.DESCRIPTION.capabilities,
        display_name="   ",
    )

    with pytest.raises(ProviderDiscoveryError, match="display_name"):
        discover_providers(modules=[module])


def test_provider_factory_returns_matching_factory():
    module = _module("fake")
    factory = provider_factory(module.DESCRIPTION, modules=[module])

    assert factory is module.create_provider


def test_provider_factory_missing_raises_actionable_error():
    module = _module("fake")
    other = _module("outro", "outro")

    with pytest.raises(ProviderDiscoveryError, match="não encontrada"):
        provider_factory(module.DESCRIPTION, modules=[other])


def test_get_provider_description_rejects_unknown():
    with pytest.raises(ProviderDiscoveryError, match="desconhecido"):
        get_provider_description("nao-existe", "machine_translation")


def test_discovery_allows_same_id_in_different_families():
    llm = _module("gemeo", "gemeo")
    llm.DESCRIPTION = ProviderDescription(
        identity=ProviderIdentity(ProviderFamily.LLM, "gemeo", "1", "test"),
        capabilities=ProviderCapabilities(family=ProviderFamily.LLM),
        display_name="Gêmeo LLM",
    )
    machine = _module("gemeo-mt", "gemeo")

    found = discover_providers(modules=[llm, machine])
    assert len(found) == 2


def test_get_provider_description_rejects_ambiguous(monkeypatch):
    import tradutor.providers.discovery as discovery_mod

    llm_desc = ProviderDescription(
        identity=ProviderIdentity(ProviderFamily.LLM, "gemeo", "1", "test"),
        capabilities=ProviderCapabilities(family=ProviderFamily.LLM),
        display_name="Gêmeo LLM",
    )
    mt_desc = ProviderDescription(
        identity=ProviderIdentity(ProviderFamily.MACHINE_TRANSLATION, "gemeo", "1", "test"),
        capabilities=ProviderCapabilities(
            family=ProviderFamily.MACHINE_TRANSLATION,
            requires_credentials=False,
            reports_token_usage=False,
        ),
        display_name="Gêmeo MT",
    )
    monkeypatch.setattr(
        discovery_mod, "discover_providers", lambda family=None, package=None: (llm_desc, mt_desc)
    )

    with pytest.raises(ProviderDiscoveryError, match="ambíguo"):
        get_provider_description("gemeo")


def test_create_discovered_provider_builds_google_web():
    from tradutor.providers.machine_translation.google_web import GoogleWebProvider

    provider = create_discovered_provider(
        "google-web", family="machine_translation", delay_seconds=0.0, max_retries=0
    )

    assert isinstance(provider, GoogleWebProvider)
    assert provider.identity.provider_id == "google-web"


def test_create_discovered_provider_unknown_id_raises():
    with pytest.raises(ProviderDiscoveryError, match="desconhecido"):
        create_discovered_provider("nao-existe", family="machine_translation")
