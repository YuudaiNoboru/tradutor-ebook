"""Testes do config TOML + pydantic (tarefa 7.4 e 7.7).

Cobrem: tabela de precos editavel no config refletida na estimativa,
defaults sensatos sem arquivo, TOML invalido e campos invalidos com a
mensagem apontando o campo, e fallback de precos do exemplo.
"""

from __future__ import annotations

import pytest

from tradutor.domain import Prices, estimate
from tradutor.infra.config import (
    DEFAULT_PRICES,
    AppConfig,
    ConfigError,
    PriceConfig,
    ProviderConfig,
    load_config,
    write_config,
)


def test_missing_config_uses_defaults(tmp_path):
    config = load_config(tmp_path / "nao-existe.toml")

    assert config.provider == "deepseek"
    assert config.translation.target == "pt-BR"
    assert config.execution.parallelism == 4
    assert config.cost.spending_limit_usd == 0.0
    assert config.prices_for("deepseek") == DEFAULT_PRICES["deepseek"]


def test_edited_prices_are_used_in_estimate(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        "[cost.prices.deepseek]\ninput_per_million = 0.50\noutput_per_million = 2.00\n",
        encoding="utf-8",
    )
    config = load_config(path)

    prices = config.prices_for("deepseek")
    assert prices == Prices(input_per_million=0.50, output_per_million=2.00)

    result = estimate(
        input_tokens=1_000_000,
        target_language="pt-BR",
        prices=prices,
        batch_count=1,
        latency_seconds=10,
        parallelism=1,
    )
    assert result.cost_usd == pytest.approx(0.50 + 1.2 * 2.00)


def test_full_sections_are_parsed(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'provider = "openrouter"\n'
        "[providers.openrouter]\n"
        'base_url = "https://openrouter.ai/api/v1"\n'
        'model = "deepseek/deepseek-chat"\n'
        "[translation]\n"
        'target = "es"\n'
        "[cost]\n"
        "spending_limit_usd = 5.0\n"
        "[execution]\n"
        "parallelism = 2\n",
        encoding="utf-8",
    )
    config = load_config(path)

    assert config.provider == "openrouter"
    assert config.providers["openrouter"].base_url == "https://openrouter.ai/api/v1"
    assert config.translation.target == "es"
    assert config.cost.spending_limit_usd == 5.0
    assert config.execution.parallelism == 2


def test_unknown_provider_prices_is_none(tmp_path):
    config = load_config(tmp_path / "nao-existe.toml")

    assert config.prices_for("provedor-desconhecido") is None


def test_invalid_toml_raises_config_error(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("isto nao e [toml", encoding="utf-8")

    with pytest.raises(ConfigError, match="configuracao invalida"):
        load_config(path)


def test_invalid_field_error_points_to_field(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[cost]\nspending_limit_usd = -5\n", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        load_config(path)

    assert "cost.spending_limit_usd" in str(excinfo.value)


def test_negative_price_is_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        "[cost.prices.deepseek]\ninput_per_million = -1.0\noutput_per_million = 1.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(path)

    assert "cost.prices.deepseek" in str(excinfo.value)


def test_defaults_constructed_directly():
    config = AppConfig()
    assert config.cost.prices == {}
    assert config.prices_for("deepseek") == DEFAULT_PRICES["deepseek"]


def test_write_config_roundtrip(tmp_path):
    config = AppConfig()
    config.provider = "openrouter"
    config.providers["openrouter"] = ProviderConfig(
        base_url="https://openrouter.ai/api/v1", model="deepseek/deepseek-chat"
    )
    config.translation.target = "es"
    config.translation.policy = "traduzir"
    config.cost.spending_limit_usd = 5.0
    config.cost.prices["openrouter"] = PriceConfig(input_per_million=0.50, output_per_million=2.00)
    config.execution.parallelism = 2

    path = write_config(config, tmp_path / "config.toml")
    reloaded = load_config(path)

    assert reloaded.provider == "openrouter"
    assert reloaded.providers["openrouter"].model == "deepseek/deepseek-chat"
    assert reloaded.translation.target == "es"
    assert reloaded.translation.policy == "traduzir"
    assert reloaded.cost.spending_limit_usd == 5.0
    assert reloaded.cost.prices["openrouter"].input_per_million == 0.50
    assert reloaded.execution.parallelism == 2


def test_write_config_escapes_strings(tmp_path):
    config = AppConfig()
    config.translation.target = 'pt-"BR"'

    path = write_config(config, tmp_path / "config.toml")

    reloaded = load_config(path)
    assert reloaded.translation.target == 'pt-"BR"'
