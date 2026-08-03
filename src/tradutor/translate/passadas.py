"""Passadas de qualidade (secao 5): glossario e priming.

Cada passada envia uma amostra do livro pela porta ``Translator`` com o
``PromptContext.task`` correspondente; o adapter produz a resposta no
formato JSON esperado e a passada a interpreta em objetos do dominio.
O nucleo nao conhece o provedor: apenas monta o contexto, envia os
blocos e interpreta as respostas.

- ``extract_glossary``: lista ``termo original -> traducao`` (tarefa 5.1).
- ``build_priming``: resumo de estilo/tom do livro (tarefa 5.2).
"""

from __future__ import annotations

from collections.abc import Sequence

from tradutor.domain import Block, Chapter, PassadaTask, PromptContext, Translator

SAMPLE_CHAPTERS = 10
GLOSSARY_SAMPLE_CHARS = 20_000
PRIMING_SAMPLE_CHARS = 12_000


def extract_glossary(
    translator: Translator,
    chapters: Sequence[Chapter],
    *,
    source_language: str = "auto",
    target_language: str = "pt-BR",
    max_chapters: int = SAMPLE_CHAPTERS,
    max_chars: int = GLOSSARY_SAMPLE_CHARS,
) -> list[tuple[str, str]]:
    """Extrai termos tecnicos e nomes proprios de uma amostra do livro.

    Devolve entradas ``(termo original, traducao)`` para persistencia no
    ``glossario.json``; a politica de termos fica a cargo da traducao.
    """
    sample = _sample_text(chapters, max_chapters=max_chapters, max_chars=max_chars)
    if not sample:
        return []
    context = PromptContext(
        source_language=source_language,
        target_language=target_language,
        task=PassadaTask.GLOSSARIO,
    )
    batch = translator.translate([_sample_block(sample)], context)
    entries: list[tuple[str, str]] = []
    for text in batch.texts:
        entries.extend(_parse_glossary_entries(text))
    return entries


def build_priming(
    translator: Translator,
    chapters: Sequence[Chapter],
    *,
    source_language: str = "auto",
    target_language: str = "pt-BR",
    max_chapters: int = SAMPLE_CHAPTERS,
    max_chars: int = PRIMING_SAMPLE_CHARS,
) -> str:
    """Produz um resumo do estilo e tom do livro a partir da amostra."""
    sample = _sample_text(chapters, max_chapters=max_chapters, max_chars=max_chars)
    if not sample:
        return ""
    context = PromptContext(
        source_language=source_language,
        target_language=target_language,
        task=PassadaTask.PRIMING,
    )
    batch = translator.translate([_sample_block(sample)], context)
    return "\n".join(text.strip() for text in batch.texts if text.strip())


def _sample_block(text: str) -> Block:
    return Block(id=0, kind="amostra", text=text)


def _sample_text(
    chapters: Sequence[Chapter],
    *,
    max_chapters: int,
    max_chars: int,
) -> str:
    """Junta o texto traduzivel dos primeiros capitulos, com teto de tamanho."""
    parts: list[str] = []
    budget = max_chars
    for chapter in chapters[:max_chapters]:
        for block in chapter.blocks:
            if block.protected or not block.text.strip():
                continue
            if budget <= 0:
                return "\n\n".join(parts)
            take = min(len(block.text), budget)
            parts.append(block.text[:take])
            budget -= take
    return "\n\n".join(parts)


def _parse_glossary_entries(text: str) -> list[tuple[str, str]]:
    """Interpreta linhas ``termo original -> traducao`` (aceita ':' como fallback)."""
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip().strip('",[]').rstrip(",").strip()
        if not line:
            continue
        if "->" in line:
            termo, traducao = (part.strip() for part in line.split("->", 1))
        elif ":" in line:
            termo, traducao = (part.strip() for part in line.split(":", 1))
        else:
            continue
        if termo and traducao:
            entries.append((termo, traducao))
    return entries
