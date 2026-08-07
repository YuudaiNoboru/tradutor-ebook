"""Portas e resultados de tradução compartilhados pelo domínio."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from tradutor.domain.blocks import Block


class TermPolicy(StrEnum):
    TRADUZIR = "traduzir"
    MANTER = "manter"
    HIBRIDO = "hibrido"


class PassadaTask(StrEnum):
    TRADUCAO = "traducao"
    GLOSSARIO = "glossario"
    PRIMING = "priming"


@dataclass(frozen=True, slots=True)
class Usage:
    """Uso reportado: tokens são opcionais; caracteres/blocos são universais."""

    prompt_tokens: int | None = 0
    completion_tokens: int | None = 0
    characters: int = 0
    blocks: int = 0

    def __post_init__(self) -> None:
        for name in ("prompt_tokens", "completion_tokens", "characters", "blocks"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} não pode ser negativo")

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None or self.completion_tokens is None:
            return None
        return self.prompt_tokens + self.completion_tokens

    @property
    def character_count(self) -> int:
        return self.characters

    @property
    def block_count(self) -> int:
        return self.blocks

    @property
    def token_usage_reported(self) -> bool:
        return self.prompt_tokens is not None and self.completion_tokens is not None

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            prompt_tokens=_add_optional(self.prompt_tokens, other.prompt_tokens),
            completion_tokens=_add_optional(self.completion_tokens, other.completion_tokens),
            characters=self.characters + other.characters,
            blocks=self.blocks + other.blocks,
        )


def _add_optional(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    return left + right


@dataclass(frozen=True, slots=True)
class PromptContext:
    source_language: str = "auto"
    target_language: str = "pt-BR"
    policy: TermPolicy = TermPolicy.HIBRIDO
    glossary: tuple[tuple[str, str], ...] = ()
    priming: str = ""
    task: PassadaTask = PassadaTask.TRADUCAO


@dataclass(frozen=True, slots=True)
class TranslationBatch:
    texts: tuple[str, ...]
    usage: Usage


TranslationResult = TranslationBatch


class Translator(Protocol):
    """Compatibilidade histórica para a porta de tradução do motor."""

    def translate(self, batch: Sequence[Block], context: PromptContext) -> TranslationBatch: ...
