"""Orquestracao da traducao em lotes paralelos com cache e retomada (secao 6).

- Estado por livro em ``estado.json`` gravado atomicamente a cada lote
  concluido (6.1) e descartado quando a chave de compatibilidade muda
  (6.2: livro, idiomas, modelo, politica e versao do glossario).
- Lotes respeitam o limite de contexto do modelo (6.3) e rodam em
  paralelo com fila de lotes (6.4, default 4).
- Cancelamento ordenado e retomada: blocos concluidos nunca sao
  re-traduzidos (6.5); estado corrompido e lido com tolerancia (6.6).
- Qualidade por lote: placeholders fieis e sem marcas de IA; resposta
  reprovada reprocessa o lote e, esgotadas as tentativas, o bloco fica
  pendente para retomada.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tradutor.domain import (
    Block,
    Chapter,
    Prices,
    PromptContext,
    TranslationBatch,
    Translator,
    Usage,
    cost_of,
    has_ai_mark,
    is_faithful,
)
from tradutor.providers.errors import ProviderError
from tradutor.translate.batching import make_batches
from tradutor.translate.estado import (
    STATE_FILENAME,
    WorkState,
    load_estado,
    save_estado,
    state_compat_key,
)
from tradutor.translate.glossary_store import glossary_version

DEFAULT_PARALLELISM = 4


class TranslationCancelled(Exception):
    """Traducao cancelada pelo usuario; o progresso concluido ja foi salvo."""


class TranslationQualityError(ProviderError):
    """Lote reprocessado sem obter fidelidade de placeholders/saida limpa."""


class SpendingLimitExceeded(ProviderError):
    """Teto de gasto atingido; o progresso concluido ficou salvo no cache."""


@dataclass(frozen=True, slots=True)
class TranslationOutcome:
    """Resultado da traducao: traducoes por capitulo e uso total acumulado."""

    translations: dict[str, dict[int, str]]
    usage: Usage


def translate_book(
    chapters: Sequence[Chapter],
    *,
    translator: Translator,
    context: PromptContext,
    work_dir: str | Path,
    book_hash: str,
    model: str,
    max_tokens: int,
    token_count: Callable[[str], int],
    parallelism: int = DEFAULT_PARALLELISM,
    cancel: Callable[[], bool] | None = None,
    progress: Callable[[int, int], None] | None = None,
    max_batch_attempts: int = 3,
    spending_limit_usd: float = 0.0,
    prices: Prices | None = None,
) -> TranslationOutcome:
    """Traduz os blocos pendentes do livro, retomando do estado salvo.

    Levanta ``TranslationCancelled`` no cancelamento, ``ProviderError``
    em falha do provedor, ``SpendingLimitExceeded`` quando o custo real
    acumulado ultrapassa o teto (tarefa 7.5) e
    ``TranslationQualityError`` quando um lote esgota as tentativas de
    qualidade — sempre com o progresso ja concluido persistido em
    ``estado.json`` para retomada.

    ``spending_limit_usd`` > 0 exige ``prices``: apos cada lote, o custo
    acumulado (usage exato x tabela de precos) e comparado ao teto; se
    ultrapassar, a traducao para e o progresso fica preservado no cache.
    """
    if parallelism < 1:
        raise ValueError("paralelismo deve ser >= 1")
    if spending_limit_usd < 0:
        raise ValueError("teto de gasto nao pode ser negativo")
    if spending_limit_usd > 0 and prices is None:
        raise ValueError("teto de gasto exige a tabela de precos")
    key = state_compat_key(
        book_hash=book_hash,
        source_language=context.source_language,
        target_language=context.target_language,
        model=model,
        policy=context.policy,
        glossary_version=glossary_version(context.glossary),
    )
    estado_path = Path(work_dir) / STATE_FILENAME
    state = load_estado(estado_path)
    if state.key != key:
        state = WorkState(key=key)

    pending: list[tuple[str, Block]] = []
    for chapter in chapters:
        saved = state.translations.get(chapter.path)
        for block in chapter.blocks:
            if block.protected or not block.text.strip():
                continue
            if saved is not None and block.id in saved:
                continue
            pending.append((chapter.path, block))
    total = len(pending)
    if total == 0:
        return TranslationOutcome(
            translations={path: dict(blocks) for path, blocks in state.translations.items()},
            usage=state.usage,
        )
    if progress:
        progress(0, total)

    batches = make_batches(
        [block for _, block in pending],
        token_count=token_count,
        max_tokens=max_tokens,
    )
    queue: list[list[tuple[str, Block]]] = []
    index = 0
    for batch in batches:
        queue.append(pending[index : index + len(batch)])
        index += len(batch)

    def translate_batch(batch: list[Block]) -> TranslationBatch:
        last_error: TranslationQualityError | None = None
        for attempt in range(max_batch_attempts):
            result = translator.translate(batch, context)
            if _batch_is_clean(batch, result):
                return result
            last_error = TranslationQualityError(
                f"resposta reprovada na verificacao de qualidade (tentativa {attempt + 1})"
            )
        assert last_error is not None
        raise last_error

    done = 0
    over_limit = False

    def record(result: TranslationBatch, pairs: list[tuple[str, Block]]) -> None:
        nonlocal done, over_limit
        state.usage = state.usage + result.usage
        for (chapter_path, block), text in zip(pairs, result.texts, strict=True):
            state.translations.setdefault(chapter_path, {})[block.id] = text
        done += len(pairs)
        save_estado(estado_path, state)
        if not over_limit and spending_limit_usd > 0:
            assert prices is not None
            over_limit = cost_of(state.usage, prices) > spending_limit_usd
        if progress:
            progress(done, total)

    first_error: ProviderError | None = None
    cancelled = False
    next_index = 0
    inflight: dict[Future[TranslationBatch], list[tuple[str, Block]]] = {}

    def submit_next() -> None:
        nonlocal next_index
        if cancelled or first_error is not None or next_index >= len(queue):
            return
        pairs = queue[next_index]
        next_index += 1
        future = pool.submit(translate_batch, [block for _, block in pairs])
        inflight[future] = pairs

    with ThreadPoolExecutor(max_workers=parallelism) as pool:
        for _ in range(parallelism):
            submit_next()
        while inflight:
            for future in as_completed(list(inflight)):
                pairs = inflight.pop(future)
                try:
                    result = future.result()
                except ProviderError as exc:
                    if first_error is None:
                        first_error = exc
                    continue
                except Exception as exc:
                    if first_error is None:
                        first_error = ProviderError(f"falha interna no lote: {exc}")
                    continue
                record(result, pairs)
                if over_limit:
                    continue
                if first_error is not None:
                    continue
                if cancel is not None and cancel():
                    cancelled = True
                    continue
                submit_next()

    if over_limit:
        assert prices is not None
        total_cost = cost_of(state.usage, prices)
        raise SpendingLimitExceeded(
            f"teto de gasto atingido: custo acumulado de US$ {total_cost:.2f} "
            f"supera o teto de US$ {spending_limit_usd:.2f}; o progresso "
            "concluido ficou salvo no cache — defina um novo teto e retome"
        )
    if first_error is not None:
        raise first_error
    if cancelled:
        raise TranslationCancelled(
            "traducao cancelada; o progresso concluido foi preservado em estado.json"
        )
    return TranslationOutcome(
        translations={path: dict(blocks) for path, blocks in state.translations.items()},
        usage=state.usage,
    )


def _batch_is_clean(batch: Sequence[Block], result: TranslationBatch) -> bool:
    return all(
        is_faithful(block.text, text) and bool(text.strip()) and not has_ai_mark(text)
        for block, text in zip(batch, result.texts, strict=True)
    )
