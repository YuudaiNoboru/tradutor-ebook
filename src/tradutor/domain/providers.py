"""Contratos neutros para familias de provedores."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from tradutor.domain.blocks import Block
from tradutor.domain.translate import PassadaTask, TermPolicy, TranslationBatch


class ProviderFamily(StrEnum):
    LLM = "llm"
    MACHINE_TRANSLATION = "machine_translation"
    TRADUCAO_AUTOMATICA = "machine_translation"


class ProviderStability(StrEnum):
    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    UNOFFICIAL = "unofficial"


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    family: ProviderFamily
    provider_id: str
    version: str = "1"
    transport_variant: str = "default"

    def __post_init__(self) -> None:
        if not self.provider_id or self.provider_id != self.provider_id.strip():
            raise ValueError("provider_id deve ser um identificador não vazio")
        if not self.version or not self.transport_variant:
            raise ValueError("versão e variante do provider são obrigatórias")

    @property
    def id(self) -> str:
        return self.provider_id

    @property
    def cache_key(self) -> str:
        return ":".join((self.family.value, self.provider_id, self.version, self.transport_variant))


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    family: ProviderFamily
    supports_glossary: bool = False
    supports_priming: bool = False
    supports_term_policy: bool = False
    supports_html: bool = False
    requires_credentials: bool = True
    stability: ProviderStability = ProviderStability.STABLE
    max_batch_chars: int | None = None
    max_batch_items: int | None = None
    max_concurrency: int = 1
    delay_seconds: float = 0.0
    reports_token_usage: bool | None = None
    reports_character_usage: bool = False
    supports_model_listing: bool = True
    supports_connection_test: bool = True
    experimental: bool = False
    has_pricing: bool = True

    def __post_init__(self) -> None:
        if self.reports_token_usage is None:
            object.__setattr__(self, "reports_token_usage", self.family is ProviderFamily.LLM)
        for name in ("max_batch_chars", "max_batch_items"):
            value = getattr(self, name)
            if value is not None and value < 1:
                raise ValueError(f"{name} deve ser positivo")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency deve ser >= 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds não pode ser negativo")
        if self.family is ProviderFamily.LLM and not self.reports_token_usage:
            raise ValueError("LLM deve declarar medição de tokens")

    @property
    def supports_quality_context(self) -> bool:
        return self.supports_glossary or self.supports_priming or self.supports_term_policy

    @property
    def usage_metered(self) -> bool:
        return self.reports_token_usage or self.reports_character_usage


@dataclass(frozen=True, slots=True)
class ProviderDescription:
    identity: ProviderIdentity
    capabilities: ProviderCapabilities
    display_name: str
    description: str = ""
    experimental_warning: str = ""

    @property
    def family(self) -> ProviderFamily:
        return self.identity.family

    @property
    def provider_id(self) -> str:
        return self.identity.provider_id

    @property
    def id(self) -> str:
        return self.provider_id

    @property
    def version(self) -> str:
        return self.identity.version

    @property
    def transport_variant(self) -> str:
        return self.identity.transport_variant


@dataclass(frozen=True, slots=True)
class LLMContext:
    source_language: str = "auto"
    target_language: str = "pt-BR"
    policy: TermPolicy = TermPolicy.HIBRIDO
    glossary: tuple[tuple[str, str], ...] = ()
    priming: str = ""
    task: PassadaTask = PassadaTask.TRADUCAO


@dataclass(frozen=True, slots=True)
class MachineTranslationContext:
    source_language: str = "auto"
    target_language: str = "pt-BR"


class LLMTranslator(Protocol):
    identity: ProviderIdentity
    capabilities: ProviderCapabilities

    def translate(self, batch: Sequence[Block], context: LLMContext) -> TranslationBatch: ...


class MachineTranslationProvider(Protocol):
    identity: ProviderIdentity
    capabilities: ProviderCapabilities

    def translate(
        self, batch: Sequence[Block], context: MachineTranslationContext
    ) -> TranslationBatch: ...


class ProviderFactory(Protocol):
    """Fábrica de adapter mantida fora do núcleo da tradução."""

    def __call__(self, **kwargs: object) -> object: ...
