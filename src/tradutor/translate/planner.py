"""Planejador da tradução (decisão D10).

Produz a estimativa pré-voo e gerência o status do cache do livro.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tradutor.domain import (
    CostEstimate,
    Prices,
    estimate_unmetered,
    translatable_tokens,
)
from tradutor.domain import (
    estimate as domain_estimate,
)
from tradutor.epub.container import Ebook
from tradutor.infra.config import AppConfig
from tradutor.translate.batching import make_batches, make_batches_by_limits
from tradutor.translate.estado import STATE_FILENAME, load_estado, state_compat_key
from tradutor.translate.glossary_store import glossary_version

DEFAULT_LATENCY_SECONDS = 20.0
DEFAULT_MAX_TOKENS = 4000


@dataclass(frozen=True, slots=True)
class BookPlan:
    """Resumo e estimativa pré-voo."""

    title: str
    language: str | None
    chapter_count: int
    translatable_blocks: int
    input_tokens: int
    batch_count: int
    estimate: CostEstimate | None
    prices: Prices | None


@dataclass(frozen=True, slots=True)
class CacheStatus:
    """Situação do cache do livro: chave compatível e blocos já traduzidos."""

    compatible: bool
    saved_blocks: int
    key: str


def default_work_dir_for(book_path: str | Path) -> Path:
    """Diretório de trabalho por livro na área de dados do usuário."""
    from platformdirs import user_data_dir

    from tradutor.infra.config import APP_DIR

    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in Path(book_path).stem)
    return Path(user_data_dir(APP_DIR)) / "trabalho" / slug


def book_hash(path: str | Path) -> str:
    """Hash do conteúdo do arquivo (chave de compatibilidade do estado)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan_book(
    ebook: Ebook,
    *,
    config: AppConfig,
    token_counter: Callable[[str], int],
    max_tokens: int = DEFAULT_MAX_TOKENS,
    latency_seconds: float = DEFAULT_LATENCY_SECONDS,
    parallelism: int | None = None,
) -> BookPlan:
    """Resumo do livro e estimativa de tokens/custo/tempo."""
    blocks = [
        block
        for chapter in ebook.chapters
        for block in chapter.blocks
        if not block.protected and block.text.strip()
    ]
    input_tokens = translatable_tokens(ebook.chapters, token_counter)
    characters = sum(len(block.text) for block in blocks)
    if config.family == "machine_translation":
        max_chars, max_items, provider_delay, provider_parallelism = config.provider_limits()
        batch_count = len(make_batches_by_limits(blocks, max_chars=max_chars, max_items=max_items))
        prices = None
        estimate = estimate_unmetered(
            characters=characters,
            blocks=len(blocks),
            batch_count=batch_count,
            latency_seconds=provider_delay or latency_seconds,
            parallelism=parallelism if parallelism is not None else provider_parallelism,
        )
    else:
        batch_count = len(make_batches(blocks, token_count=token_counter, max_tokens=max_tokens))
        prices = config.prices_for()
        estimate = None
        if prices is not None:
            estimate = domain_estimate(
                input_tokens=input_tokens,
                target_language=config.translation.target,
                prices=prices,
                batch_count=batch_count,
                latency_seconds=latency_seconds,
                parallelism=parallelism
                if parallelism is not None
                else config.execution.parallelism,
            )
    return BookPlan(
        title=ebook.container.title or Path(ebook.path).name,
        language=ebook.container.language,
        chapter_count=len(ebook.chapters),
        translatable_blocks=len(blocks),
        input_tokens=input_tokens,
        batch_count=batch_count,
        estimate=estimate,
        prices=prices,
    )


def cache_status(
    work_dir: str | Path,
    *,
    book_hash: str,
    config: AppConfig,
    glossary: Sequence[tuple[str, str]],
) -> CacheStatus:
    """Estado salvo compatível com a configuração atual (retomada)."""
    key = state_compat_key(
        book_hash=book_hash,
        source_language=config.translation.source,
        target_language=config.translation.target,
        model=config.active_model,
        policy=config.term_policy,
        glossary_version=glossary_version(glossary) if config.family == "llm" else "",
        family=config.family,
        provider_id=config.provider,
        transport_variant=config.provider_variant(),
    )
    state = load_estado(Path(work_dir) / STATE_FILENAME)
    compatible = state.key == key
    saved = sum(len(blocks) for blocks in state.translations.values()) if compatible else 0
    return CacheStatus(compatible=compatible, saved_blocks=saved, key=key)
