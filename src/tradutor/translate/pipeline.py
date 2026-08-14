"""Pipeline de tradução executado em worker (decisão D10).

Orquestra a tradução do livro, glossário, priming, motor de tradução e gravação.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tradutor.domain import (
    Block,
    Chapter,
    MachineTranslationContext,
    PromptContext,
    Translator,
    Usage,
    fix_mojibake,
    sanitize_pre_send,
)
from tradutor.domain.events import (
    TranslationCompletedEvent,
    TranslationEvent,
    TranslationLogEvent,
    TranslationProgressEvent,
    TranslationStartedEvent,
)
from tradutor.epub.container import Ebook, output_path_for
from tradutor.epub.writer import write_translated
from tradutor.infra.config import AppConfig
from tradutor.providers.errors import ProviderError
from tradutor.translate.estado import STATE_FILENAME
from tradutor.translate.glossary_store import (
    load_glossary,
    save_glossary,
)
from tradutor.translate.orchestrator import TranslationCancelled, translate_book
from tradutor.translate.passadas import (
    build_priming,
    extract_glossary,
    load_priming,
    save_priming,
)

DEFAULT_LATENCY_SECONDS = 20.0
DEFAULT_MAX_TOKENS = 3000


@dataclass(frozen=True, slots=True)
class RunResult:
    """Resultado de uma execução completa: traduções, uso e caminho de saída."""

    translations: dict[str, dict[int, str]]
    usage: Usage
    out_path: Path


def run_translation(
    ebook: Ebook,
    provider: Translator,
    config: AppConfig,
    work_dir: str | Path,
    on_event: Callable[[TranslationEvent], None],
    cancel_check: Callable[[], bool],
    *,
    token_counter: Callable[[str], int] | None = None,
    book_hash: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    reset: bool = False,
    enable_quality_passes: bool = True,
) -> RunResult:
    """Traduz o livro e grava a saída `<livro>-<idioma>.epub` notificando progresso por eventos.

    Levanta as mesmas exceções de translate_book (cancelamento, teto, provider) e
    write_translated (EPUB inválido). Passadas de qualidade e tradução de título/sumário
    são melhor esforço: falha neles nunca aborta a tradução.
    """

    def log(message: str) -> None:
        on_event(TranslationLogEvent(message=message))

    # Obter hash do livro se não fornecido
    if book_hash is None:
        from tradutor.translate.planner import book_hash as calc_hash

        book_hash = calc_hash(ebook.path)

    # Obter contador de tokens padrão se não fornecido
    if token_counter is None:
        import tiktoken

        try:
            encoding = tiktoken.get_encoding("cl100k_base")

            def default_counter(text: str) -> int:
                return len(encoding.encode(text, disallowed_special=()))

            token_counter = default_counter
        except Exception:

            def fallback_counter(text: str) -> int:
                return len(text.split())

            token_counter = fallback_counter

    all_chapters = list(ebook.chapters)
    if ebook.container.title and ebook.container.title.strip():
        all_chapters.append(
            Chapter(
                path="__title__",
                blocks=[
                    Block(
                        id=0,
                        kind="titulo",
                        text=sanitize_pre_send(ebook.container.title.strip()),
                    )
                ],
                title="Título",
            )
        )
    if ebook.toc_labels:
        toc_blocks = [
            Block(id=i, kind="titulo", text=sanitize_pre_send(label))
            for i, label in enumerate(ebook.toc_labels)
            if label.strip()
        ]
        if toc_blocks:
            all_chapters.append(
                Chapter(
                    path="__toc__",
                    blocks=toc_blocks,
                    title="Sumário",
                )
            )

    blocks = [
        block
        for chapter in all_chapters
        for block in chapter.blocks
        if not block.protected and block.text.strip()
    ]

    if cancel_check():
        raise TranslationCancelled(
            "traducao cancelada; o progresso concluido foi preservado em estado.json"
        )

    # Notificar início da tradução com a volumetria total de blocos
    on_event(TranslationStartedEvent(total_blocks=len(blocks)))

    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    caps = getattr(provider, "capabilities", None)
    if caps is not None:
        supports_glossary = caps.supports_glossary and enable_quality_passes
        supports_priming = caps.supports_priming and enable_quality_passes
    else:
        supports_glossary = (config.family == "llm") and enable_quality_passes
        supports_priming = (config.family == "llm") and enable_quality_passes
    glossary: list[tuple[str, str]] = []
    priming = ""

    def run_glossary() -> list[tuple[str, str]]:
        if cancel_check():
            return []
        log("passada 1/2: extraindo glossario da amostra do livro...")
        try:
            entries = extract_glossary(
                provider,
                ebook.chapters,
                source_language=config.translation.source,
                target_language=config.translation.target,
            )
            entries = [(fix_mojibake(src), fix_mojibake(tgt)) for src, tgt in entries]
        except ProviderError as exc:
            log(f"aviso: glossario indisponivel ({exc}); seguindo sem glossario")
            return []
        save_glossary(glossary_path, entries)
        log(f"glossario salvo com {len(entries)} termo(s) em {glossary_path.name}")
        return entries

    def run_priming() -> str:
        if cancel_check():
            return ""
        priming_path = work / "priming.txt"
        log("passada 2/2: analisando estilo e tom do livro (guia de estilo e tom)...")
        try:
            res = build_priming(
                provider,
                ebook.chapters,
                source_language=config.translation.source,
                target_language=config.translation.target,
            )
            if res:
                res = fix_mojibake(res)
                save_priming(priming_path, res)
                log(f"guia de estilo e tom salvo em {priming_path.name}")
            return res
        except ProviderError as exc:
            log(f"aviso: guia de estilo e tom indisponivel ({exc}); seguindo sem estilo")
            return ""

    if supports_glossary:
        glossary_path = work / "glossario.json"
        glossary = list(load_glossary(glossary_path))
    if supports_priming:
        priming_path = work / "priming.txt"
        priming = load_priming(priming_path)
        if priming:
            log(f"guia de estilo e tom carregado de {priming_path.name}")

    if supports_glossary and supports_priming and not glossary and not priming:
        log("passadas 1/2 e 2/2: glossario e guia de estilo e tom executados em paralelo...")
        with ThreadPoolExecutor(max_workers=2) as pool:
            glossary_future = pool.submit(run_glossary)
            priming_future = pool.submit(run_priming)
            glossary = glossary_future.result()
            priming = priming_future.result()
    else:
        if supports_glossary and not glossary:
            glossary = run_glossary()
        if supports_priming and not priming:
            priming = run_priming()

    if cancel_check():
        raise TranslationCancelled(
            "traducao cancelada; o progresso concluido foi preservado em estado.json"
        )

    if not supports_glossary and not supports_priming:
        if not enable_quality_passes:
            log("passadas de qualidade (glossario e guia de estilo e tom) desativadas pelo usuario")
        else:
            log(
                "provider comum: glossario, guia de estilo e tom, politica de termos e apendice nao se aplicam"
            )

    if reset:
        estado_path = work / STATE_FILENAME
        if estado_path.exists():
            estado_path.unlink()
            log("cache anterior descartado (recomecando do zero)")

    policy = config.term_policy
    context: PromptContext | MachineTranslationContext
    if config.family == "machine_translation":
        context = MachineTranslationContext(
            source_language=config.translation.source,
            target_language=config.translation.target,
        )
    else:
        context = PromptContext(
            source_language=config.translation.source,
            target_language=config.translation.target,
            policy=policy,
            glossary=tuple(glossary),
            priming=priming,
        )

    log(
        f"traduzindo {len(ebook.chapters)} capitulo(s) para "
        f"{config.translation.target} (paralelismo {config.execution.parallelism})..."
    )
    prices = config.prices_for()

    def emit_progress(done: int, total: int) -> None:
        on_event(TranslationProgressEvent(done=done, total=total))

    outcome = translate_book(
        all_chapters,
        translator=provider,
        context=context,
        work_dir=work,
        book_hash=book_hash,
        model=config.active_model,
        max_tokens=max_tokens,
        token_count=token_counter,
        parallelism=config.execution.parallelism,
        cancel=cancel_check,
        progress=emit_progress,
        spending_limit_usd=config.cost.spending_limit_usd if prices is not None else 0.0,
        prices=prices,
        family=config.family,
        provider_id=config.provider,
        transport_variant=config.provider_variant(),
    )

    translated_title = outcome.translations.get("__title__", {}).get(0, None)
    if translated_title is None and ebook.container.title:
        translated_title = ebook.container.title
    if translated_title is not None:
        translated_title = fix_mojibake(translated_title)

    toc_trans = outcome.translations.get("__toc__", {})
    labels = (
        [fix_mojibake(toc_trans.get(i, label)) for i, label in enumerate(ebook.toc_labels)]
        if ebook.toc_labels
        else list(ebook.toc_labels)
    )

    out_path = output_path_for(ebook.path, config.translation.target)
    log(f"gravando o EPUB de saida em {out_path}...")
    write_translated(
        ebook,
        out_path,
        translations={
            block_id: text
            for path, blocks in outcome.translations.items()
            if path not in ("__title__", "__toc__")
            for block_id, text in blocks.items()
        },
        toc_labels=labels,
        target_lang=config.translation.target,
        translated_title=translated_title,
        modified=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        appendix_entries=glossary if supports_glossary else (),
    )
    log(f"concluido: {out_path}")

    # Notificar conclusão da tradução com traduções e uso finais
    on_event(
        TranslationCompletedEvent(
            translations=outcome.translations,
            usage=outcome.usage,
        )
    )

    return RunResult(
        translations=outcome.translations,
        usage=outcome.usage,
        out_path=out_path,
    )
