"""Descoberta de providers por módulos, sem registro central."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from tradutor.domain import ProviderDescription, ProviderFamily


class ProviderDiscoveryError(ValueError):
    """Um módulo de provider não cumpre o contrato de descoberta."""


def discover_providers(
    family: ProviderFamily | str | None = None,
    *,
    package: str = "tradutor.providers",
    modules: Iterable[ModuleType] | None = None,
) -> tuple[ProviderDescription, ...]:
    """Carrega módulos de uma família e valida IDs, metadados e fábricas.

    ``modules`` existe para testes e extensões embutidas; em produção os
    subpacotes ``llm`` e ``machine_translation`` são enumerados por
    ``pkgutil``. A função não contém uma lista de providers.
    """

    expected = _coerce_family(family) if family is not None else None
    loaded = tuple(modules) if modules is not None else _load_modules(package, expected)
    found: list[ProviderDescription] = []
    ids: set[tuple[ProviderFamily, str]] = set()
    for module in loaded:
        description = _description_from(module)
        if expected is not None and description.family is not expected:
            continue
        key = (description.family, description.provider_id)
        if key in ids:
            raise ProviderDiscoveryError(
                f"ID de provider duplicado: {description.family.value}/{description.provider_id}"
            )
        ids.add(key)
        factory = getattr(module, "create_provider", None)
        if not callable(factory):
            raise ProviderDiscoveryError(f"módulo {module.__name__} não expõe create_provider")
        found.append(description)
    return tuple(sorted(found, key=lambda item: (item.family.value, item.provider_id)))


def provider_factory(
    description: ProviderDescription, *, modules: Iterable[ModuleType]
) -> Callable[..., Any]:
    """Obtém a fábrica correspondente a uma descrição já validada."""

    for module in modules:
        candidate = _description_from(module)
        if candidate.identity == description.identity:
            factory = getattr(module, "create_provider", None)
            if callable(factory):
                return factory
    raise ProviderDiscoveryError(f"fábrica não encontrada para {description.provider_id}")


def _load_modules(package: str, family: ProviderFamily | None) -> tuple[ModuleType, ...]:
    root_name = {
        ProviderFamily.LLM: f"{package}.llm",
        ProviderFamily.MACHINE_TRANSLATION: f"{package}.machine_translation",
    }
    packages = (root_name[family],) if family is not None else tuple(root_name.values())
    modules: list[ModuleType] = []
    for package_name in packages:
        try:
            root = importlib.import_module(package_name)
        except ModuleNotFoundError:
            continue
        for item in pkgutil.iter_modules(root.__path__, f"{package_name}."):
            if item.name.rsplit(".", 1)[-1].startswith("_"):
                continue
            modules.append(importlib.import_module(item.name))
    return tuple(modules)


def _coerce_family(value: ProviderFamily | str) -> ProviderFamily:
    try:
        return value if isinstance(value, ProviderFamily) else ProviderFamily(value)
    except ValueError as exc:
        raise ProviderDiscoveryError(f"família de provider inválida: {value}") from exc


def _description_from(module: ModuleType) -> ProviderDescription:
    value = getattr(module, "DESCRIPTION", None)
    if value is None:
        value = getattr(module, "PROVIDER_DESCRIPTION", None)
    if not isinstance(value, ProviderDescription):
        raise ProviderDiscoveryError(
            f"módulo {module.__name__} deve expor DESCRIPTION como ProviderDescription"
        )
    if value.identity.family is not value.capabilities.family:
        raise ProviderDiscoveryError(f"metadados inconsistentes em {module.__name__}")
    if not value.display_name.strip():
        raise ProviderDiscoveryError(f"display_name vazio em {module.__name__}")
    return value


def get_provider_description(
    provider_id: str,
    family: ProviderFamily | str | None = None,
    *,
    package: str = "tradutor.providers",
) -> ProviderDescription:
    """Retorna um provider descoberto ou falha com mensagem acionável."""

    matches = [
        item
        for item in discover_providers(family, package=package)
        if item.provider_id == provider_id
    ]
    if not matches:
        family_text = f" na família {family}" if family else ""
        raise ProviderDiscoveryError(f"provider desconhecido{family_text}: {provider_id}")
    if len(matches) > 1:
        raise ProviderDiscoveryError(f"provider ambíguo: {provider_id}")
    return matches[0]


def create_discovered_provider(
    provider_id: str,
    *,
    family: ProviderFamily | str | None = None,
    package: str = "tradutor.providers",
    **kwargs: Any,
) -> Any:
    """Cria um adapter pela família/ID, sem registro manual no núcleo."""

    description = get_provider_description(provider_id, family, package=package)
    modules = _load_modules(package, description.family)
    for module in modules:
        if _description_from(module).identity == description.identity:
            return module.create_provider(**kwargs)
    raise ProviderDiscoveryError(f"fábrica não encontrada para {provider_id}")


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    """Resultado do teste de conexão, com mensagem pronta para a interface."""

    ok: bool
    message: str
    models: tuple[str, ...] = ()


def test_provider_connection(
    provider_id: str,
    family: str,
    *,
    key_override: str | None = None,
    secret_store: Any = None,
    base_url: str | None = None,
    model: str | None = None,
    key_name: str | None = None,
    timeout: float | None = None,
    delay_seconds: float | None = None,
) -> ConnectionResult:
    """Instancia e executa o teste de conexão de um provedor de forma centralizada."""
    from tradutor.providers.openai_compat import (
        DEFAULT_BASE_URL,
        DEFAULT_MODEL,
        OpenAICompatProvider,
    )

    if family == "machine_translation":
        try:
            provider = create_discovered_provider(
                provider_id,
                family="machine_translation",
                delay_seconds=delay_seconds if delay_seconds is not None else 0.25,
                timeout=timeout if timeout is not None else 30.0,
                max_retries=3,
            )
        except Exception as exc:
            return ConnectionResult(False, f"Erro ao criar provedor de tradução automática: {exc}")
    else:
        store = secret_store
        if key_override:
            from tradutor.domain.secrets import ChainedSecretStore, PromptSecretStore

            store = ChainedSecretStore(
                [PromptSecretStore(lambda _name: key_override), secret_store]
            )

        try:
            provider = create_discovered_provider(
                provider_id,
                family="llm",
                secret_store=store,
                base_url=base_url or DEFAULT_BASE_URL,
                model=model or DEFAULT_MODEL,
                key_name=key_name,
            )
        except Exception:
            provider = OpenAICompatProvider(
                secret_store=store,
                base_url=base_url or DEFAULT_BASE_URL,
                model=model or DEFAULT_MODEL,
                key_name=key_name,
            )

    result = provider.test_connection()
    return ConnectionResult(
        ok=result.ok, message=result.message, models=getattr(result, "models", ())
    )
