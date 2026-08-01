"""Porta ``Translator`` e tipos de dados de traducao.

O nucleo do dominio define a porta; os adapters de provedor (camada
``providers``) a implementam. ``PromptContext`` e montado pelo nucleo
(secao 5: glossario, priming e politica) e a porta nunca recebe chaves.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from tradutor.domain.blocks import Block


class TermPolicy(StrEnum):
    """Politica de termos tecnicos aplicada na traducao (default hibrido)."""

    TRADUZIR = "traduzir"
    MANTER = "manter"
    HIBRIDO = "hibrido"


@dataclass(frozen=True, slots=True)
class Usage:
    """Tokens consumidos: entrada e saida (somaveis entre lotes)."""

    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
        )


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Contexto de um lote: idiomas, politica, glossario e priming."""

    source_language: str = "auto"
    target_language: str = "pt-BR"
    policy: TermPolicy = TermPolicy.HIBRIDO
    glossary: tuple[tuple[str, str], ...] = ()
    priming: str = ""


@dataclass(frozen=True, slots=True)
class TranslationBatch:
    """Resultado de um lote: traducoes alinhadas aos blocos + uso de tokens."""

    texts: tuple[str, ...]
    usage: Usage


class Translator(Protocol):
    """Porta de traducao: o nucleo nao conhece o provedor concreto."""

    def translate(self, batch: Sequence[Block], context: PromptContext) -> TranslationBatch: ...
