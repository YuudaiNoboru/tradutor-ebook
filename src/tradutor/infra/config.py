"""Configuração TOML por família/provider, sem persistir segredos."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import platformdirs
from pydantic import BaseModel, Field, ValidationError

from tradutor.domain.cost import Prices

APP_DIR = "tradutor-ebook"
DEFAULT_PRICES: dict[str, Prices] = {
    "deepseek": Prices(input_per_million=0.27, output_per_million=1.10),
    "openrouter": Prices(input_per_million=0.30, output_per_million=1.20),
}


class ConfigError(Exception):
    """Configuração inválida ou incompatível com a família selecionada."""


class ProviderConfig(BaseModel):
    base_url: str = ""
    model: str = ""
    variant: str = "openai-chat"
    max_batch_chars: int | None = Field(default=None, ge=1)
    max_batch_items: int | None = Field(default=None, ge=1)
    delay_seconds: float = Field(default=0.0, ge=0)
    parallelism: int | None = Field(default=None, ge=1)


class MachineTranslationConfig(BaseModel):
    variant: str = "html-v2/text-v6"
    max_batch_chars: int = Field(default=5000, ge=1)
    max_batch_items: int = Field(default=8, ge=1)
    delay_seconds: float = Field(default=0.25, ge=0)
    parallelism: int = Field(default=1, ge=1)
    timeout_seconds: float = Field(default=30.0, gt=0)


class PriceConfig(BaseModel):
    input_per_million: float = Field(gt=0)
    output_per_million: float = Field(gt=0)

    def to_domain(self) -> Prices:
        return Prices(self.input_per_million, self.output_per_million)


class CostConfig(BaseModel):
    spending_limit_usd: float = Field(default=0.0, ge=0)
    prices: dict[str, PriceConfig] = Field(default_factory=dict)


class TranslationConfig(BaseModel):
    source: str = "auto"
    target: str = "pt-BR"
    policy: str = "hibrido"


class ExecutionConfig(BaseModel):
    parallelism: int = Field(default=4, ge=1)


class UpdateConfig(BaseModel):
    auto_check: bool = True


class AppConfig(BaseModel):
    """Schema atual; campos antigos continuam aceitos por defaults."""

    family: str = "llm"
    provider: str = "deepseek"
    variant: str = "openai-chat"
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    machine_translation: MachineTranslationConfig = Field(default_factory=MachineTranslationConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    cost: CostConfig = Field(default_factory=CostConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    update: UpdateConfig = Field(default_factory=UpdateConfig)

    def provider_family(self):
        from tradutor.domain import ProviderFamily

        try:
            return ProviderFamily(self.family)
        except ValueError as exc:
            raise ConfigError(f"família de provider inválida: {self.family}") from exc

    @property
    def active_model(self) -> str:
        """Nome do modelo do provider ativo (default da DeepSeek)."""
        from tradutor.providers.openai_compat import DEFAULT_MODEL

        provider = self.providers.get(self.provider)
        if self.family == "machine_translation":
            return ""
        return provider.model if provider else DEFAULT_MODEL

    @property
    def term_policy(self):
        """Politica de termos do config com fallback seguro para 'hibrido'."""
        from tradutor.domain import TermPolicy

        try:
            return TermPolicy(self.translation.policy)
        except ValueError:
            return TermPolicy.HIBRIDO

    def provider_variant(self) -> str:
        if self.family == "machine_translation":
            return self.machine_translation.variant
        configured = self.providers.get(self.provider)
        return configured.variant if configured and configured.variant else self.variant

    def provider_limits(self) -> tuple[int | None, int | None, float, int]:
        if self.family == "machine_translation":
            mt = self.machine_translation
            return mt.max_batch_chars, mt.max_batch_items, mt.delay_seconds, mt.parallelism
        configured = self.providers.get(self.provider)
        return (
            configured.max_batch_chars if configured else None,
            configured.max_batch_items if configured else None,
            configured.delay_seconds if configured else 0.0,
            configured.parallelism
            if configured and configured.parallelism
            else self.execution.parallelism,
        )

    def prices_for(self, provider: str | None = None) -> Prices | None:
        name = provider if provider is not None else self.provider
        if self.family == "machine_translation":
            return None
        if name in self.cost.prices:
            return self.cost.prices[name].to_domain()
        return DEFAULT_PRICES.get(name)


def default_config_path() -> Path:
    return Path(platformdirs.user_config_dir(APP_DIR)) / "config.toml"


def load_config(path: str | Path | None = None) -> AppConfig:
    source = Path(path) if path is not None else default_config_path()
    if not source.exists():
        return AppConfig()
    try:
        raw = tomllib.loads(source.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"configuracao invalida em {source}: {exc}") from exc
    family = raw.get("family", "llm")
    if family not in {"llm", "machine_translation"}:
        raise ConfigError(f"configuracao invalida em {source}: família desconhecida {family!r}")
    if family == "machine_translation":
        machine = raw.get("machine_translation", {})
        if isinstance(machine, dict):
            incompatible = {"model", "api_key", "glossary", "priming"}.intersection(machine)
            if incompatible:
                fields = ", ".join(sorted(incompatible))
                raise ConfigError(
                    f"configuracao invalida em {source}: campos incompatíveis para tradução automática: {fields}"
                )
    try:
        config = AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(_validation_message(source, exc)) from exc
    if config.family == "machine_translation" and config.machine_translation.variant in {
        "html-v1/text-v2",
        "html-v1/text-v3",
        "html-v1/text-v4",
        "html-v1/text-v5",
        "html-v1/text-v6",
    }:
        config.machine_translation.variant = "html-v2/text-v6"
    return config


def _validation_message(source: Path, exc: ValidationError) -> str:
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"]) or "<raiz>"
    return f"configuracao invalida em {source}: campo '{field}' — {first['msg']}"


def write_config(config: AppConfig, path: str | Path | None = None) -> Path:
    dest = Path(path) if path is not None else default_config_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# tradutor-ebook — configuracao gerada pela interface",
        "# Este arquivo nunca deve conter chaves de API.",
        f"family = {json.dumps(config.family)}",
        f"provider = {json.dumps(config.provider)}",
        f"variant = {json.dumps(config.variant)}",
    ]
    for name in sorted(config.providers):
        provider = config.providers[name]
        lines.extend(
            [
                f"[providers.{name}]",
                f"base_url = {json.dumps(provider.base_url)}",
                f"model = {json.dumps(provider.model)}",
                f"variant = {json.dumps(provider.variant)}",
            ]
        )
        if provider.max_batch_chars is not None:
            lines.append(f"max_batch_chars = {provider.max_batch_chars}")
        if provider.max_batch_items is not None:
            lines.append(f"max_batch_items = {provider.max_batch_items}")
        if provider.delay_seconds:
            lines.append(f"delay_seconds = {provider.delay_seconds!r}")
    mt = config.machine_translation
    lines.extend(
        [
            "[machine_translation]",
            f"variant = {json.dumps(mt.variant)}",
            f"max_batch_chars = {mt.max_batch_chars}",
            f"max_batch_items = {mt.max_batch_items}",
            f"delay_seconds = {mt.delay_seconds!r}",
            f"parallelism = {mt.parallelism}",
            f"timeout_seconds = {mt.timeout_seconds!r}",
        ]
    )
    translation = config.translation
    lines.extend(
        [
            "[translation]",
            f"source = {json.dumps(translation.source)}",
            f"target = {json.dumps(translation.target)}",
            f"policy = {json.dumps(translation.policy)}",
            "[cost]",
            f"spending_limit_usd = {config.cost.spending_limit_usd!r}",
        ]
    )
    for name in sorted(config.cost.prices):
        price = config.cost.prices[name]
        lines.extend(
            [
                f"[cost.prices.{name}]",
                f"input_per_million = {price.input_per_million!r}",
                f"output_per_million = {price.output_per_million!r}",
            ]
        )
    lines.extend(
        [
            "[execution]",
            f"parallelism = {config.execution.parallelism}",
            "[update]",
            f"auto_check = {json.dumps(config.update.auto_check)}",
        ]
    )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest
