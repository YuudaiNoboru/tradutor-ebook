"""Custo da traducao: estimativa pre-voo e relatorio real-vs-previsto (secao 7).

Funcoes puras, sem I/O: a tabela de precos vem do config (camada
``infra``, tarefa 7.4) e a contagem de tokens recebe o contador
injetado (``tiktoken`` na camada ``translate``, tarefa 7.1). O teto de
gasto e checado pela orquestracao apos cada lote (tarefa 7.5).

- ``translatable_tokens``: tokens do payload real (protegidos/brancos fora).
- ``expansion_factor``: fator de expansao do idioma alvo (7.2).
- ``estimate``: tokens in/out, custo US$ e tempo (7.3).
- ``cost_of``: custo real em US$ a partir do usage exato da API.
- ``make_cost_report``: relatorio final real-vs-previsto (7.6).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from tradutor.domain.blocks import Chapter
from tradutor.domain.translate import Usage

MILLION = 1_000_000

# Fatores de expansao por idioma alvo (tarefa 7.2): o quanto o texto
# traduzido tende a crescer em relacao ao original. Idiomas que
# comprimem (CJK) ficam abaixo de 1.0.
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
    """Estimativa pre-voo: tokens, custo em US$ e tempo estimado."""

    input_tokens: int
    output_tokens: int
    cost_usd: float
    batch_count: int
    estimated_seconds: float


@dataclass(frozen=True, slots=True)
class CostReport:
    """Relatorio final: previsto (estimativa) vs real (usage exato da API)."""

    estimated: CostEstimate
    actual: Usage
    actual_cost_usd: float
    difference_usd: float


def expansion_factor(target_language: str) -> float:
    """Fator de expansao aproximado do idioma alvo (tarefa 7.2).

    Compara pela parte principal do codigo de idioma ("pt-BR" -> "pt");
    idiomas desconhecidos usam o fator neutro 1.0.
    """
    lang = target_language.strip().split("-")[0].lower()
    return EXPANSION_FACTORS.get(lang, DEFAULT_EXPANSION_FACTOR)


def translatable_tokens(
    chapters: Sequence[Chapter],
    token_count: Callable[[str], int],
) -> int:
    """Tokens pre-voo sobre o payload real de texto traduzivel (tarefa 7.1).

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
    """Estimativa de tokens de saida, custo US$ e tempo (tarefa 7.3).

    - Saida = entrada x fator de expansao do idioma alvo.
    - Custo = entrada/1M x preco de entrada + saida/1M x preco de saida.
    - Tempo = lotes x latencia media / paralelismo (loteria: ETA medido
      vem da vazao real na tela de progresso, secao 9).
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


def cost_of(usage: Usage, prices: Prices) -> float:
    """Custo real em US$ de um uso acumulado (tarefas 7.5 e 7.6).

    A mesma formula da estimativa, agora com o usage exato reportado
    pela API.
    """
    return (
        usage.prompt_tokens / MILLION * prices.input_per_million
        + usage.completion_tokens / MILLION * prices.output_per_million
    )


def make_cost_report(
    *,
    estimate: CostEstimate,
    usage: Usage,
    prices: Prices,
) -> CostReport:
    """Relatorio final real-vs-previsto (tarefa 7.6).

    Compara a estimativa pre-voo com o uso exato da API; a diferenca
    pode ser negativa (gastou menos que o previsto).
    """
    actual_cost_usd = cost_of(usage, prices)
    return CostReport(
        estimated=estimate,
        actual=usage,
        actual_cost_usd=round(actual_cost_usd, 2),
        difference_usd=round(actual_cost_usd - estimate.cost_usd, 2),
    )
