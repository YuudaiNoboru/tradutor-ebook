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

import logging
import re
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from tradutor.domain import (
    Block,
    Chapter,
    MachineTranslationContext,
    Prices,
    PromptContext,
    ProviderFamily,
    TermPolicy,
    TranslationBatch,
    Translator,
    Usage,
    clean_placeholders,
    cost_of,
    fix_mojibake,
    has_ai_mark,
    is_faithful,
    is_formatting_faithful,
    sanitize_pre_send,
)
from tradutor.providers.errors import ProviderError
from tradutor.translate.batching import make_batches, make_batches_by_limits
from tradutor.translate.estado import (
    STATE_FILENAME,
    WorkState,
    load_estado,
    save_estado,
    state_compat_key,
)
from tradutor.translate.glossary_store import glossary_version

_TAG_RE = re.compile(r"</?([A-Za-z][\w:-]*)(?:\s[^>]*)?/?>")
_MASK_RE = re.compile(r"@@(\d+)@@")


def strip_markup(text: str) -> str:
    """Remove tags HTML/XHTML inline e máscaras de tag @@N@@, colapsando espaços simples."""
    text = _TAG_RE.sub("", text)
    text = _MASK_RE.sub("", text)
    return re.sub(r" +", " ", text).strip()


def fallback_markup(original: str, translated: str) -> str:
    """Aplica fallback limpando formatação, preservando tag <a> externa se o bloco original for um link."""
    clean = strip_markup(translated)
    orig_stripped = original.strip()
    if (
        orig_stripped.startswith("<a ")
        and orig_stripped.endswith("</a>")
        and orig_stripped.count("<a ") == 1
    ):
        open_a = orig_stripped[: orig_stripped.index(">") + 1]
        if not clean.startswith("<a"):
            return f"{open_a}{clean}</a>"
    return clean


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
    family: ProviderFamily | str | None = None,
    provider_id: str | None = None,
    transport_variant: str | None = None,
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
    identity = getattr(translator, "identity", None)
    if identity is not None:
        family = family if family is not None else identity.family
        provider_id = provider_id if provider_id is not None else identity.provider_id
        transport_variant = (
            transport_variant if transport_variant is not None else identity.transport_variant
        )
    key = state_compat_key(
        book_hash=book_hash,
        source_language=context.source_language,
        target_language=context.target_language,
        model=model,
        policy=getattr(context, "policy", TermPolicy.HIBRIDO),
        glossary_version=glossary_version(getattr(context, "glossary", ())),
        family=family,
        provider_id=provider_id,
        transport_variant=transport_variant,
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

    MAX_GLOBAL_PARALLELISM = 20
    provider_caps = getattr(translator, "capabilities", None)
    provider_family = getattr(provider_caps, "family", family)
    is_machine = provider_family == ProviderFamily.MACHINE_TRANSLATION
    provider_max = (
        getattr(provider_caps, "max_concurrency", parallelism)
        if provider_caps is not None
        else parallelism
    )
    effective_parallelism = min(parallelism, provider_max, MAX_GLOBAL_PARALLELISM)
    pending_blocks = [block for _, block in pending]
    if is_machine:
        try:
            batches = make_batches_by_limits(
                pending_blocks,
                max_chars=getattr(provider_caps, "max_batch_chars", None),
                max_items=getattr(provider_caps, "max_batch_items", None),
            )
        except ValueError as exc:
            raise ProviderError(
                f"conteudo incompativel com os limites do provider: {exc}; "
                "o progresso anterior ficou salvo no cache"
            ) from exc
    else:
        raw_items = (
            getattr(provider_caps, "max_batch_items", 15) if provider_caps is not None else 15
        )
        max_batch_items = 15 if (raw_items is None or raw_items > 15) else raw_items
        batches = make_batches(
            pending_blocks,
            token_count=token_count,
            max_tokens=max_tokens,
            max_items=max_batch_items,
        )
    queue: list[list[tuple[str, Block]]] = []
    index = 0
    for batch in batches:
        queue.append(pending[index : index + len(batch)])
        index += len(batch)

    def translate_batch(batch: list[Block]) -> TranslationBatch:
        call_context = context
        if is_machine:
            call_context = MachineTranslationContext(
                source_language=context.source_language, target_language=context.target_language
            )
        sanitized_batch = [
            Block(
                id=b.id,
                kind=b.kind,
                text=sanitize_pre_send(b.text),
                protected=b.protected,
            )
            for b in batch
        ]
        result = translator.translate(sanitized_batch, call_context)
        if len(result.texts) != len(batch):
            raise TranslationQualityError("resposta desalinhada com o lote")
        return result

    done = 0
    over_limit = False
    block_attempts: dict[int, int] = {}
    requeue_pairs: list[tuple[str, Block]] = []
    failed_blocks: list[int] = []

    def record(result: TranslationBatch, pairs: list[tuple[str, Block]]) -> None:
        nonlocal done, over_limit
        state.usage = state.usage + result.usage
        logger = logging.getLogger(__name__)
        for (chapter_path, block), raw_text in zip(pairs, result.texts, strict=True):
            text = fix_mojibake(clean_placeholders(raw_text))
            is_valid = (
                bool(text.strip())
                and (not has_ai_mark(text) or has_ai_mark(block.text))
                and is_formatting_faithful(block.text, text)
            )

            if is_valid:
                state.translations.setdefault(chapter_path, {})[block.id] = text
                done += 1
            else:
                attempts = block_attempts.get(block.id, 0) + 1
                block_attempts[block.id] = attempts
                if attempts < max_batch_attempts:
                    requeue_pairs.append((chapter_path, block))
                elif (
                    is_faithful(block.text, text)
                    and bool(text.strip())
                    and (not has_ai_mark(text) or has_ai_mark(block.text))
                ):
                    logger.warning(
                        f"Bloco {block.id}: formatação HTML corrompida pelo tradutor. "
                        "Aplicando fallback sem formatação (tags limpas)."
                    )
                    state.translations.setdefault(chapter_path, {})[block.id] = fallback_markup(
                        block.text, text
                    )
                    done += 1
                else:
                    failed_blocks.append(block.id)

        if state.translations:
            save_estado(estado_path, state)
        if not over_limit and spending_limit_usd > 0:
            assert prices is not None
            cost = cost_of(state.usage, prices)
            over_limit = cost is not None and cost > spending_limit_usd
        if progress:
            progress(done, total)

    first_error: ProviderError | None = None
    cancelled = False
    next_index = 0
    inflight: dict[Future[TranslationBatch], list[tuple[str, Block]]] = {}

    def submit_next() -> None:
        nonlocal next_index
        if cancelled or first_error is not None:
            return
        if next_index >= len(queue) and requeue_pairs:
            to_retry = list(requeue_pairs)
            requeue_pairs.clear()
            retry_blocks = [b for _, b in to_retry]
            if is_machine:
                retry_batches = make_batches_by_limits(
                    retry_blocks,
                    max_chars=getattr(provider_caps, "max_batch_chars", None),
                    max_items=getattr(provider_caps, "max_batch_items", None),
                )
            else:
                raw_items = (
                    getattr(provider_caps, "max_batch_items", 15)
                    if provider_caps is not None
                    else 15
                )
                max_batch_items = 15 if (raw_items is None or raw_items > 15) else raw_items
                retry_batches = make_batches(
                    retry_blocks,
                    token_count=token_count,
                    max_tokens=max_tokens,
                    max_items=max_batch_items,
                )
            idx = 0
            for b_list in retry_batches:
                queue.append(to_retry[idx : idx + len(b_list)])
                idx += len(b_list)

        if next_index >= len(queue):
            return

        pairs = queue[next_index]
        next_index += 1
        future = pool.submit(translate_batch, [block for _, block in pairs])
        inflight[future] = pairs

    pool = ThreadPoolExecutor(max_workers=effective_parallelism)
    try:
        if cancel is not None and cancel():
            cancelled = True
        else:
            for _ in range(effective_parallelism):
                submit_next()
            while inflight:
                done_set, _ = wait(list(inflight), timeout=0.2, return_when=FIRST_COMPLETED)
                for future in done_set:
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
                    if cancel is not None and cancel():
                        cancelled = True
                    elif first_error is None and not over_limit:
                        submit_next()
                if cancelled:
                    break
                if cancel is not None and cancel():
                    cancelled = True
                    break
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    if over_limit:
        assert prices is not None
        total_cost = cost_of(state.usage, prices) or 0.0
        raise SpendingLimitExceeded(
            f"teto de gasto atingido: custo acumulado de US$ {total_cost:.2f} "
            f"supera o teto de US$ {spending_limit_usd:.2f}; o progresso "
            "concluido ficou salvo no cache — defina um novo teto e retome"
        )
    if first_error is not None:
        raise first_error
    if failed_blocks:
        raise TranslationQualityError(
            f"resposta reprovada na verificacao de qualidade para {len(failed_blocks)} bloco(s)"
        )
    if cancelled:
        raise TranslationCancelled(
            "traducao cancelada; o progresso concluido foi preservado em estado.json"
        )
    return TranslationOutcome(
        translations={path: dict(blocks) for path, blocks in state.translations.items()},
        usage=state.usage,
    )


def _batch_is_clean(batch: Sequence[Block], result: TranslationBatch) -> bool:
    if len(batch) != len(result.texts):
        return False
    return all(
        is_formatting_faithful(block.text, clean_placeholders(text))
        and bool(text.strip())
        and (not has_ai_mark(text) or has_ai_mark(block.text))
        for block, text in zip(batch, result.texts, strict=True)
    )
