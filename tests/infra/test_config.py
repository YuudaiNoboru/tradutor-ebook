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
    default_config_path,
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


def test_old_config_without_family_loads_as_llm(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'provider = "deepseek"\n'
        "[providers.deepseek]\n"
        'base_url = "https://api.deepseek.com"\n'
        'model = "deepseek-chat"\n',
        encoding="utf-8",
    )
    config = load_config(path)

    assert config.family == "llm"
    assert config.provider == "deepseek"
    assert config.providers["deepseek"].model == "deepseek-chat"
    assert config.prices_for() == DEFAULT_PRICES["deepseek"]


def test_machine_translation_config_loads_with_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'family = "machine_translation"\n'
        'provider = "google-web"\n'
        "[machine_translation]\n"
        "max_batch_chars = 3000\n",
        encoding="utf-8",
    )
    config = load_config(path)

    assert config.family == "machine_translation"
    assert config.machine_translation.max_batch_chars == 3000
    assert config.machine_translation.max_batch_items == 8
    assert config.machine_translation.parallelism == 1
    assert config.machine_translation.variant == "html-v2/text-v6"
    assert config.prices_for() is None


@pytest.mark.parametrize(
    "old",
    [
        "html-v1/text-v2",
        "html-v1/text-v3",
        "html-v1/text-v4",
        "html-v1/text-v5",
        "html-v1/text-v6",
    ],
)
def test_machine_translation_migrates_retired_text_variant(tmp_path, old):
    path = tmp_path / "config.toml"
    path.write_text(
        'family = "machine_translation"\n'
        'provider = "google-web"\n'
        "[machine_translation]\n"
        f'variant = "{old}"\n',
        encoding="utf-8",
    )
    config = load_config(path)

    assert config.machine_translation.variant == "html-v2/text-v6"


def test_machine_translation_rejects_llm_fields(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'family = "machine_translation"\n'
        'provider = "google-web"\n'
        "[machine_translation]\n"
        'model = "deepseek-chat"\n'
        'api_key = "sk-123"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="incompat"):
        load_config(path)


def test_machine_translation_rejects_invalid_limits(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'family = "machine_translation"\n'
        'provider = "google-web"\n'
        "[machine_translation]\n"
        "max_batch_chars = 0\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="machine_translation.max_batch_chars"):
        load_config(path)


def test_unknown_family_is_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('family = "pombo"\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="fam"):
        load_config(path)


def test_write_config_roundtrip_machine_translation(tmp_path):
    config = AppConfig()
    config.family = "machine_translation"
    config.provider = "google-web"
    config.machine_translation.max_batch_chars = 2500
    config.machine_translation.delay_seconds = 0.5

    path = write_config(config, tmp_path / "config.toml")
    reloaded = load_config(path)

    assert reloaded.family == "machine_translation"
    assert reloaded.provider == "google-web"
    assert reloaded.machine_translation.max_batch_chars == 2500
    assert reloaded.machine_translation.delay_seconds == 0.5
    assert "api_key" not in path.read_text(encoding="utf-8")


def test_provider_variant_and_limits_by_family():
    config = AppConfig()
    config.family = "machine_translation"
    config.provider = "google-web"

    assert config.provider_variant() == "html-v2/text-v6"
    chars, items, delay, parallelism = config.provider_limits()
    assert chars == 5000
    assert items == 8
    assert delay == 0.25
    assert parallelism == 1

    llm = AppConfig()
    assert llm.provider_variant() == "openai-chat"
    assert llm.provider_limits() == (None, None, 0.0, 4)


def test_example_config_is_loadable():
    from pathlib import Path

    example = Path(__file__).resolve().parents[2] / "config.example.toml"
    config = load_config(example)

    assert config.family == "llm"
    assert config.provider == "deepseek"
    assert config.machine_translation.max_batch_chars == 5000


def test_provider_family_invalid_raises():
    config = AppConfig()
    config.family = "pombo"

    with pytest.raises(ConfigError, match="família"):
        config.provider_family()


def test_default_config_path_uses_platform_dir():
    path = default_config_path()

    assert path.name == "config.toml"
    assert "tradutor-ebook" in str(path)


def test_write_config_persists_provider_limits(tmp_path):
    config = AppConfig()
    config.providers["openrouter"] = ProviderConfig(
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat",
        max_batch_chars=3000,
        max_batch_items=16,
        delay_seconds=0.5,
    )

    path = write_config(config, tmp_path / "config.toml")
    text = path.read_text(encoding="utf-8")

    assert "max_batch_chars = 3000" in text
    assert "max_batch_items = 16" in text
    assert "delay_seconds = 0.5" in text
    reloaded = load_config(path)
    assert reloaded.providers["openrouter"].max_batch_chars == 3000


def test_machine_translation_section_must_be_table(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'family = "machine_translation"\nmachine_translation = "html"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="machine_translation"):
        load_config(path)


def test_update_config_default_and_roundtrip(tmp_path):
    config = AppConfig()
    assert config.update.auto_check is True

    path = tmp_path / "config_without_update.toml"
    path.write_text('family = "llm"\n', encoding="utf-8")
    loaded = load_config(path)
    assert loaded.update.auto_check is True

    path_false = tmp_path / "config_false.toml"
    path_false.write_text('family = "llm"\n[update]\nauto_check = false\n', encoding="utf-8")
    loaded_false = load_config(path_false)
    assert loaded_false.update.auto_check is False

    loaded_false.update.auto_check = True
    written_path = write_config(loaded_false, tmp_path / "config_written.toml")
    assert "auto_check = true" in written_path.read_text(encoding="utf-8")
    reloaded = load_config(written_path)
    assert reloaded.update.auto_check is True
