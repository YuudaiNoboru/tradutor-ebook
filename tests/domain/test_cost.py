"""Testes de custo do dominio (secao 7: tarefas 7.1, 7.2, 7.3, 7.6 e 7.7).

Cobrem: contagem pre-voo ignorando blocos protegidos/brancos (7.1),
fatores de expansao por idioma alvo (7.2), matematica da estimativa de
tokens/custo/tempo (7.3), custo real a partir do usage exato e relatorio
real-vs-previsto (7.6).
"""

from __future__ import annotations

import pytest

from tradutor.domain import (
    Block,
    Chapter,
    Prices,
    Usage,
    cost_of,
    estimate,
    estimate_unmetered,
    expansion_factor,
    make_cost_report,
    translatable_tokens,
)

DEEPSEEK = Prices(input_per_million=0.27, output_per_million=1.10)


def book() -> list[Chapter]:
    return [
        Chapter(
            blocks=[
                Block(id=0, kind="texto", text="alpha"),
                Block(id=1, kind="codigo", text="long code sample", protected=True),
                Block(id=2, kind="texto", text="   "),
                Block(id=3, kind="texto", text="omega"),
            ],
            path="c.xhtml",
        )
    ]


def test_expansion_factor_by_target_language():
    assert expansion_factor("pt-BR") == pytest.approx(1.2)
    assert expansion_factor("en") == pytest.approx(1.0)
    assert expansion_factor("es") == pytest.approx(1.05)
    assert expansion_factor("ja") == pytest.approx(0.7)


def test_expansion_factor_case_insensitive_and_unknown_defaults():
    assert expansion_factor("PT-br") == pytest.approx(1.2)
    assert expansion_factor("xy") == pytest.approx(1.0)
    assert expansion_factor("") == pytest.approx(1.0)


def test_translatable_tokens_ignores_protected_and_blank_blocks():
    assert translatable_tokens(book(), token_count=len) == 10


def test_translatable_tokens_empty_book():
    assert translatable_tokens([], token_count=len) == 0


def test_estimate_math_tokens_cost_and_time():
    result = estimate(
        input_tokens=1_000_000,
        target_language="pt-BR",
        prices=DEEPSEEK,
        batch_count=10,
        latency_seconds=30,
        parallelism=4,
    )
    assert result.input_tokens == 1_000_000
    assert result.output_tokens == 1_200_000
    assert result.cost_usd == pytest.approx(0.27 + 1.2 * 1.10)
    assert result.batch_count == 10
    assert result.estimated_seconds == pytest.approx(10 * 30 / 4)


def test_estimate_cjk_language_compresses_output():
    result = estimate(
        input_tokens=1_000_000,
        target_language="zh",
        prices=DEEPSEEK,
        batch_count=1,
        latency_seconds=10,
        parallelism=1,
    )
    assert result.output_tokens == 600_000


def test_estimate_validates_inputs():
    with pytest.raises(ValueError, match="tokens"):
        estimate(
            input_tokens=-1,
            target_language="pt-BR",
            prices=DEEPSEEK,
            batch_count=1,
            latency_seconds=10,
            parallelism=1,
        )
    with pytest.raises(ValueError, match="lotes"):
        estimate(
            input_tokens=10,
            target_language="pt-BR",
            prices=DEEPSEEK,
            batch_count=-1,
            latency_seconds=10,
            parallelism=1,
        )
    with pytest.raises(ValueError, match="paralelismo"):
        estimate(
            input_tokens=10,
            target_language="pt-BR",
            prices=DEEPSEEK,
            batch_count=1,
            latency_seconds=10,
            parallelism=0,
        )
    with pytest.raises(ValueError, match="latencia"):
        estimate(
            input_tokens=10,
            target_language="pt-BR",
            prices=DEEPSEEK,
            batch_count=1,
            latency_seconds=-1,
            parallelism=1,
        )


def test_cost_of_uses_exact_usage_from_api():
    cost = cost_of(Usage(prompt_tokens=1_000_000, completion_tokens=2_000_000), DEEPSEEK)
    assert cost == pytest.approx(0.27 + 2 * 1.10)


def test_cost_of_zero_usage_is_zero():
    assert cost_of(Usage(0, 0), DEEPSEEK) == 0.0


def test_cost_report_compares_actual_vs_estimated():
    est = estimate(
        input_tokens=1_000_000,
        target_language="pt-BR",
        prices=DEEPSEEK,
        batch_count=1,
        latency_seconds=10,
        parallelism=1,
    )
    report = make_cost_report(
        estimate=est,
        usage=Usage(prompt_tokens=1_000_000, completion_tokens=1_000_000),
        prices=DEEPSEEK,
    )
    assert report.estimated is est
    assert report.actual == Usage(1_000_000, 1_000_000)
    assert report.actual_cost_usd == pytest.approx(0.27 + 1.0 * 1.10)
    assert report.difference_usd == pytest.approx((0.27 + 1.10) - est.cost_usd)


def test_cost_report_difference_can_be_negative():
    est = estimate(
        input_tokens=1_000_000,
        target_language="pt-BR",
        prices=DEEPSEEK,
        batch_count=1,
        latency_seconds=10,
        parallelism=1,
    )
    report = make_cost_report(
        estimate=est,
        usage=Usage(0, 0),
        prices=DEEPSEEK,
    )
    assert report.actual_cost_usd == 0.0
    assert report.difference_usd == pytest.approx(-est.cost_usd)


def test_cost_of_unmetered_usage_is_none():
    assert cost_of(Usage(None, None, characters=100, blocks=2), DEEPSEEK) is None


def test_cost_of_without_prices_is_none():
    assert cost_of(Usage(10, 5), None) is None


def test_estimate_unmetered_reports_characters_and_blocks():
    est = estimate_unmetered(
        characters=100, blocks=2, batch_count=3, latency_seconds=2.0, parallelism=1
    )

    assert est.input_tokens is None
    assert est.output_tokens is None
    assert est.cost_usd is None
    assert est.characters == 100
    assert est.blocks == 2
    assert est.batch_count == 3
    assert est.estimated_seconds == pytest.approx(6.0)


def test_estimate_unmetered_validates_inputs():
    with pytest.raises(ValueError, match="caracteres"):
        estimate_unmetered(characters=-1, blocks=0, batch_count=1, latency_seconds=1, parallelism=1)
    with pytest.raises(ValueError, match="paralelismo"):
        estimate_unmetered(characters=0, blocks=0, batch_count=1, latency_seconds=1, parallelism=0)
    with pytest.raises(ValueError, match="latencia"):
        estimate_unmetered(characters=0, blocks=0, batch_count=1, latency_seconds=-1, parallelism=1)


def test_cost_report_unmetered_keeps_none():
    est = estimate_unmetered(
        characters=10, blocks=1, batch_count=1, latency_seconds=1, parallelism=1
    )
    report = make_cost_report(
        estimate=est,
        usage=Usage(None, None, characters=10, blocks=1),
        prices=None,
    )

    assert report.actual_cost_usd is None
    assert report.difference_usd is None
    assert report.actual.blocks == 1
