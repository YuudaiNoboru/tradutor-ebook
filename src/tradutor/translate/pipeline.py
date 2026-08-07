"""Pipeline de tradução executado em worker (decisão D10).

Orquestra a tradução do livro, glossário, priming, motor de tradução e gravação.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tradutor.domain import (
    Block,
    MachineTranslationContext,
    PromptContext,
    Translator,
    Usage,
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
from tradutor.translate.orchestrator import translate_book
from tradutor.translate.passadas import build_priming, extract_glossary

DEFAULT_LATENCY_SECONDS = 20.0
DEFAULT_MAX_TOKENS = 4000


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

    blocks = [
        block
        for chapter in ebook.chapters
        for block in chapter.blocks
        if not block.protected and block.text.strip()
    ]

    # Notificar início da tradução com a volumetria total de blocos
    on_event(TranslationStartedEvent(total_blocks=len(blocks)))

    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    caps = getattr(provider, "capabilities", None)
    if caps is not None:
        supports_glossary = caps.supports_glossary
        supports_priming = caps.supports_priming
    else:
        supports_glossary = config.family == "llm"
        supports_priming = config.family == "llm"
    glossary: list[tuple[str, str]] = []
    priming = ""

    if supports_glossary:
        glossary_path = work / "glossario.json"
        glossary = list(load_glossary(glossary_path))
        if not glossary:
            log("passada 1/2: extraindo glossario da amostra do livro...")
            try:
                glossary = extract_glossary(
                    provider,
                    ebook.chapters,
                    source_language=config.translation.source,
                    target_language=config.translation.target,
                )
            except ProviderError as exc:
                log(f"aviso: glossario indisponivel ({exc}); seguindo sem glossario")
            else:
                save_glossary(glossary_path, glossary)
                log(f"glossario salvo com {len(glossary)} termo(s) em {glossary_path.name}")

    if supports_priming:
        log("passada 2/2: analisando estilo e tom do livro (priming)...")
        try:
            priming = build_priming(
                provider,
                ebook.chapters,
                source_language=config.translation.source,
                target_language=config.translation.target,
            )
        except ProviderError as exc:
            log(f"aviso: priming indisponivel ({exc}); seguindo sem estilo")

    if not supports_glossary and not supports_priming:
        log("provider comum: glossario, priming, politica de termos e apendice nao se aplicam")

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
        ebook.chapters,
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

    labels = _translate_toc_labels(provider, ebook, context, log)
    translated_title = _translate_title(provider, ebook, context, log)

    out_path = output_path_for(ebook.path, config.translation.target)
    log(f"gravando o EPUB de saida em {out_path}...")
    write_translated(
        ebook,
        out_path,
        translations={
            block_id: text
            for blocks in outcome.translations.values()
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


def _translate_toc_labels(
    provider: Translator,
    ebook: Ebook,
    context: PromptContext | MachineTranslationContext,
    log: Callable[[str], None],
) -> list[str]:
    """Traduz os rotulos do sumario; falha mantem os rotulos originais."""
    labels = list(ebook.toc_labels)
    if not labels:
        return labels
    log("traduzindo os rotulos do sumario...")
    blocks = [Block(id=index, kind="titulo", text=label) for index, label in enumerate(labels)]
    try:
        batch = provider.translate(blocks, context)
    except ProviderError as exc:
        log(f"aviso: sumario mantido no original ({exc})")
        return labels
    if len(batch.texts) != len(blocks):
        log("aviso: resposta do sumario incompleta; mantido no original")
        return labels
    return list(batch.texts)


def _translate_title(
    provider: Translator,
    ebook: Ebook,
    context: PromptContext | MachineTranslationContext,
    log: Callable[[str], None],
) -> str | None:
    """Traduz o titulo do livro; falha mantem o titulo original."""
    title = ebook.container.title
    if not title:
        return None
    log("traduzindo o titulo...")
    try:
        batch = provider.translate([Block(id=0, kind="titulo", text=title)], context)
    except ProviderError as exc:
        log(f"aviso: titulo mantido no original ({exc})")
        return None
    if not batch.texts:
        return None
    return batch.texts[0]
