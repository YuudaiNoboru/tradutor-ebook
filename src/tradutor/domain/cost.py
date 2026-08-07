"""Custo da traducao: estimativa pre-voo e relatorio real-vs-previsto (secao 7).

Funcoes puras, sem I/O: a tabela de precos vem do config (camada
``infra``) e a contagem de tokens recebe o contador injetado
(``tiktoken`` na camada ``translate``). O teto de gasto e checado pela
orquestracao apos cada lote.

Para LLMs a estimativa usa tokens e custo em US$; para providers sem
telemetria de tokens (traducao automatica) as metricas sao
caracteres/blocos e o custo permanece "nao mensuravel" (``None``) —
nunca zero, para nao afirmar que nenhum conteudo foi processado.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from tradutor.domain.blocks import Chapter
from tradutor.domain.translate import Usage

MILLION = 1_000_000

# Fatores de expansao por idioma alvo: o quanto o texto traduzido tende a
# crescer em relacao ao original. Idiomas que comprimem (CJK) ficam abaixo
# de 1.0.
EXPANSION_FACTORS: dict[str, float] = {
    "pt": 1.2,
    "en": 1.0,
    "es": 1.05,
    "fr": 1.05,
    "it": 1.05,
    "de": 1.1,
    "nl": 1.0,
    "ja": 0.7,
    "zh": 0.6,
    "ko": 0.7,
}
DEFAULT_EXPANSION_FACTOR = 1.0


@dataclass(frozen=True, slots=True)
class Prices:
    """Precos por milhao de tokens (entrada/saida) em US$."""

    input_per_million: float
    output_per_million: float


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Estimativa pre-voo adequada ao provider.

    LLMs: tokens e custo em US$. Providers sem telemetria: ``None`` nos
    campos de token/custo e contagem de caracteres/blocos no lugar.
    """

    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    batch_count: int
    estimated_seconds: float
    characters: int = 0
    blocks: int = 0


@dataclass(frozen=True, slots=True)
class CostReport:
    """Relatorio final: previsto (estimativa) vs real (uso reportado)."""

    estimated: CostEstimate
    actual: Usage
    actual_cost_usd: float | None
    difference_usd: float | None


def expansion_factor(target_language: str) -> float:
    """Fator de expansao aproximado do idioma alvo.

    Compara pela parte principal do codigo de idioma ("pt-BR" -> "pt");
    idiomas desconhecidos usam o fator neutro 1.0.
    """
    lang = target_language.strip().split("-")[0].lower()
    return EXPANSION_FACTORS.get(lang, DEFAULT_EXPANSION_FACTOR)


def translatable_tokens(
    chapters: Sequence[Chapter],
    token_count: Callable[[str], int],
) -> int:
    """Tokens pre-voo sobre o payload real de texto traduzivel.

    Blocos protegidos ou em branco nunca entram na conta — so o texto
    efetivamente enviado ao modelo importa para o custo.
    """
    total = 0
    for chapter in chapters:
        for block in chapter.blocks:
            if block.protected or not block.text.strip():
                continue
            total += token_count(block.text)
    return total


def estimate(
    *,
    input_tokens: int,
    target_language: str,
    prices: Prices,
    batch_count: int,
    latency_seconds: float,
    parallelism: int,
) -> CostEstimate:
    """Estimativa de tokens de saida, custo US$ e tempo para LLMs.

    - Saida = entrada x fator de expansao do idioma alvo.
    - Custo = entrada/1M x preco de entrada + saida/1M x preco de saida.
    - Tempo = lotes x latencia media / paralelismo.
    """
    if input_tokens < 0:
        raise ValueError("tokens de entrada nao podem ser negativos")
    if batch_count < 0:
        raise ValueError("numero de lotes nao pode ser negativo")
    if latency_seconds < 0:
        raise ValueError("latencia nao pode ser negativa")
    if parallelism < 1:
        raise ValueError("paralelismo deve ser >= 1")
    output_tokens = round(input_tokens * expansion_factor(target_language))
    cost_usd = (
        input_tokens / MILLION * prices.input_per_million
        + output_tokens / MILLION * prices.output_per_million
    )
    estimated_seconds = batch_count * latency_seconds / parallelism
    return CostEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost_usd, 2),
        batch_count=batch_count,
        estimated_seconds=round(estimated_seconds, 1),
    )


def estimate_unmetered(
    *,
    characters: int,
    blocks: int,
    batch_count: int,
    latency_seconds: float,
    parallelism: int,
) -> CostEstimate:
    """Estimativa para providers sem cobranca/token mensuravel.

    Custo e tokens saem ``None`` (nao reportados), nunca zero; o tempo
    estimado usa a latencia e o paralelismo efetivo do provider.
    """
    if characters < 0 or blocks < 0 or batch_count < 0:
        raise ValueError("caracteres, blocos e lotes nao podem ser negativos")
    if latency_seconds < 0:
        raise ValueError("latencia nao pode ser negativa")
    if parallelism < 1:
        raise ValueError("paralelismo deve ser >= 1")
    return CostEstimate(
        input_tokens=None,
        output_tokens=None,
        cost_usd=None,
        batch_count=batch_count,
        estimated_seconds=round(batch_count * latency_seconds / parallelism, 1),
        characters=characters,
        blocks=blocks,
    )


def cost_of(usage: Usage, prices: Prices | None) -> float | None:
    """Custo real em US$ de um uso acumulado.

    Devolve ``None`` quando nao ha tabela de precos ou o provider nao
    reportou tokens (uso nao mensuravel nao e confundido com custo zero).
    """
    if prices is None or not usage.token_usage_reported:
        return None
    return (usage.prompt_tokens or 0) / MILLION * prices.input_per_million + (
        usage.completion_tokens or 0
    ) / MILLION * prices.output_per_million


def make_cost_report(
    *,
    estimate: CostEstimate,
    usage: Usage,
    prices: Prices | None,
) -> CostReport:
    """Relatorio final real-vs-previsto; ``None`` quando nao mensuravel."""
    actual_cost_usd = cost_of(usage, prices)
    difference = (
        None
        if actual_cost_usd is None or estimate.cost_usd is None
        else actual_cost_usd - estimate.cost_usd
    )
    return CostReport(
        estimated=estimate,
        actual=usage,
        actual_cost_usd=None if actual_cost_usd is None else round(actual_cost_usd, 2),
        difference_usd=None if difference is None else round(difference, 2),
    )
