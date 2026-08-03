"""Configuracao em TOML validada com pydantic (decisao D9, tarefa 7.4).

A tabela de precos de ``[cost.prices.<provider>]`` alimenta a estimativa
pre-voo da secao 7: o usuario edita os precos por milhao de tokens
(entrada/saida) no arquivo de configuracao e as estimativas subsequentes
passam a usar os novos valores. O schema cobre tambem as secoes de
provider, traducao e execucao, que as tarefas da secao 8 preenchem.

Sem arquivo de configuracao, usa defaults sensatos (precos de exemplo da
DeepSeek/OpenRouter documentados em ``config.example.toml``). Arquivo
invalido (TOML malformado ou campo com valor ilegal) levanta
``ConfigError`` com o campo apontado.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import platformdirs
from pydantic import BaseModel, Field, ValidationError

from tradutor.domain.cost import Prices

APP_DIR = "tradutor-ebook"

# Precos de exemplo quando a tabela do config esta vazia (mesmos valores
# de config.example.toml). O usuario pode sobrescrever por provider.
DEFAULT_PRICES: dict[str, Prices] = {
    "deepseek": Prices(input_per_million=0.27, output_per_million=1.10),
    "openrouter": Prices(input_per_million=0.30, output_per_million=1.20),
}


class ConfigError(Exception):
    """Configuracao invalida; a mensagem aponta o campo do problema."""


class ProviderConfig(BaseModel):
    """Provider OpenAI-compativel: endpoint e modelo."""

    base_url: str
    model: str


class PriceConfig(BaseModel):
    """Precos por milhao de tokens em US$."""

    input_per_million: float = Field(gt=0)
    output_per_million: float = Field(gt=0)

    def to_domain(self) -> Prices:
        return Prices(
            input_per_million=self.input_per_million,
            output_per_million=self.output_per_million,
        )


class CostConfig(BaseModel):
    """Teto de gasto e tabela de precos (secao 7)."""

    spending_limit_usd: float = Field(default=0.0, ge=0)
    prices: dict[str, PriceConfig] = Field(default_factory=dict)


class TranslationConfig(BaseModel):
    """Idiomas e politica de termos."""

    source: str = "auto"
    target: str = "pt-BR"
    policy: str = "hibrido"


class ExecutionConfig(BaseModel):
    """Paralelismo da traducao."""

    parallelism: int = Field(default=4, ge=1)


class AppConfig(BaseModel):
    """Schema completo do config (tarefa 8.1); defaults para config ausente."""

    provider: str = "deepseek"
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    cost: CostConfig = Field(default_factory=CostConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    def prices_for(self, provider: str | None = None) -> Prices | None:
        """Precos do provider: tabela do config primeiro, exemplo como fallback.

        Devolve ``None`` para provider sem precos conhecidos — a
        interface mostra que e preciso configura-los para estimar.
        """
        name = provider if provider is not None else self.provider
        if name in self.cost.prices:
            return self.cost.prices[name].to_domain()
        return DEFAULT_PRICES.get(name)


def default_config_path() -> Path:
    """Caminho padrao do config por plataforma (tarefa 8.2)."""
    return Path(platformdirs.user_config_dir(APP_DIR)) / "config.toml"


def load_config(path: str | Path | None = None) -> AppConfig:
    """Le e valida o config TOML (tarefa 8.2).

    Arquivo ausente devolve defaults (o app roda sem configuracao).
    TOML malformado ou valores invalidos levantam ``ConfigError`` com o
    campo apontado na mensagem.
    """
    source = Path(path) if path is not None else default_config_path()
    if not source.exists():
        return AppConfig()
    try:
        raw = tomllib.loads(source.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"configuracao invalida em {source}: {exc}") from exc
    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(_validation_message(source, exc)) from exc


def _validation_message(source: Path, exc: ValidationError) -> str:
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"]) or "<raiz>"
    return f"configuracao invalida em {source}: campo '{field}' — {first['msg']}"


def write_config(config: AppConfig, path: str | Path | None = None) -> Path:
    """Grava o config em TOML (tela de configuracao da TUI, tarefa 9.2).

    Serializa as secoes do schema: provider, providers, translation,
    cost (teto e precos) e execution. As strings sao escapadas com
    ``json.dumps``, que produz literais TOML basicos validos.
    """
    dest = Path(path) if path is not None else default_config_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# tradutor-ebook — configuracao gerada pela interface",
        "# Este arquivo nunca deve conter chaves de API.",
    ]
    lines.append(f"provider = {json.dumps(config.provider)}")
    for name in sorted(config.providers):
        provider = config.providers[name]
        lines.append(f"[providers.{name}]")
        lines.append(f"base_url = {json.dumps(provider.base_url)}")
        lines.append(f"model = {json.dumps(provider.model)}")
    translation = config.translation
    lines.append("[translation]")
    lines.append(f"source = {json.dumps(translation.source)}")
    lines.append(f"target = {json.dumps(translation.target)}")
    lines.append(f"policy = {json.dumps(translation.policy)}")
    lines.append("[cost]")
    lines.append(f"spending_limit_usd = {config.cost.spending_limit_usd!r}")
    for name in sorted(config.cost.prices):
        price = config.cost.prices[name]
        lines.append(f"[cost.prices.{name}]")
        lines.append(f"input_per_million = {price.input_per_million!r}")
        lines.append(f"output_per_million = {price.output_per_million!r}")
    lines.append("[execution]")
    lines.append(f"parallelism = {config.execution.parallelism!r}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest
