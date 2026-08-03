"""Pipeline da traducao executado em worker da TUI (decisao D10).

``run_translation`` abre o fluxo completo sobre um livro ja aberto:
passada de glossario (se existir glossario salvo, reutiliza), passada de
priming, traducao por lotes com retomada/cancelamento, traduz o titulo e
os rotulos do sumario (melhor esforco) e grava o EPUB de saida com o
apendice de glossario. Toda mensagem emitida por ``hooks.log`` e
redigida pela camada de interface antes de aparecer na tela.

``plan_book`` produz a estimativa pre-voo da tela 9.3 e
``cache_status`` decide se a tela oferece retomada (tarefa 9.5).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tradutor.domain import (
    Block,
    CostEstimate,
    Prices,
    PromptContext,
    TermPolicy,
    Translator,
    Usage,
    translatable_tokens,
)
from tradutor.domain import (
    estimate as domain_estimate,
)
from tradutor.epub.container import Ebook, output_path_for
from tradutor.epub.writer import write_translated
from tradutor.infra.config import AppConfig
from tradutor.providers.errors import ProviderError
from tradutor.translate.batching import make_batches
from tradutor.translate.estado import STATE_FILENAME, load_estado, state_compat_key
from tradutor.translate.glossary_store import (
    glossary_version,
    load_glossary,
    save_glossary,
)
from tradutor.translate.orchestrator import translate_book
from tradutor.translate.passadas import build_priming, extract_glossary

DEFAULT_LATENCY_SECONDS = 20.0
DEFAULT_MAX_TOKENS = 4000


@dataclass(frozen=True, slots=True)
class RunnerHooks:
    """Callbacks que a TUI injeta: progresso, log redigido e cancelamento."""

    progress: Callable[[int, int], None] | None = None
    log: Callable[[str], None] | None = None
    cancel: Callable[[], bool] | None = None


@dataclass(frozen=True, slots=True)
class RunResult:
    """Resultado de uma execucao completa: traducoes, uso e caminho de saida."""

    translations: dict[str, dict[int, str]]
    usage: Usage
    out_path: Path


@dataclass(frozen=True, slots=True)
class BookPlan:
    """Resumo e estimativa pre-voo exibidos na tela 9.3."""

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
    """Situacao do cache do livro: chave compativel e blocos ja traduzidos."""

    compatible: bool
    saved_blocks: int
    key: str


def model_for(config: AppConfig) -> str:
    """Nome do modelo do provider ativo (default da DeepSeek)."""
    from tradutor.providers.openai_compat import DEFAULT_MODEL

    provider = config.providers.get(config.provider)
    return provider.model if provider else DEFAULT_MODEL


def default_work_dir_for(book_path: str | Path) -> Path:
    """Diretorio de trabalho por livro na area de dados do usuario."""
    from platformdirs import user_data_dir

    from tradutor.infra.config import APP_DIR

    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in Path(book_path).stem)
    return Path(user_data_dir(APP_DIR)) / "trabalho" / slug


def book_hash(path: str | Path) -> str:
    """Hash do conteudo do arquivo (chave de compatibilidade do estado, 6.2)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def term_policy(config: AppConfig) -> TermPolicy:
    """Politica de termos do config com fallback seguro para 'hibrido'."""
    try:
        return TermPolicy(config.translation.policy)
    except ValueError:
        return TermPolicy.HIBRIDO


def plan_book(
    ebook: Ebook,
    *,
    config: AppConfig,
    token_counter: Callable[[str], int],
    max_tokens: int = DEFAULT_MAX_TOKENS,
    latency_seconds: float = DEFAULT_LATENCY_SECONDS,
    parallelism: int | None = None,
) -> BookPlan:
    """Resumo do livro e estimativa de tokens/custo/tempo (tarefa 9.3)."""
    blocks = [
        block
        for chapter in ebook.chapters
        for block in chapter.blocks
        if not block.protected and block.text.strip()
    ]
    input_tokens = translatable_tokens(ebook.chapters, token_counter)
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
            parallelism=parallelism if parallelism is not None else config.execution.parallelism,
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
    """Estado salvo compativel com a configuracao atual (retomada, 9.5)."""
    key = state_compat_key(
        book_hash=book_hash,
        source_language=config.translation.source,
        target_language=config.translation.target,
        model=model_for(config),
        policy=term_policy(config),
        glossary_version=glossary_version(glossary),
    )
    state = load_estado(Path(work_dir) / STATE_FILENAME)
    compatible = state.key == key
    saved = sum(len(blocks) for blocks in state.translations.values()) if compatible else 0
    return CacheStatus(compatible=compatible, saved_blocks=saved, key=key)


def run_translation(
    *,
    ebook: Ebook,
    provider: Translator,
    token_counter: Callable[[str], int],
    config: AppConfig,
    work_dir: str | Path,
    book_hash: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    reset: bool = False,
    hooks: RunnerHooks | None = None,
) -> RunResult:
    """Traduz o livro e grava a saida ``<livro>-<idioma>.epub``.

    Levanta as mesmas excecoes de ``translate_book`` (cancelamento,
    teto, provider) e ``write_translated`` (EPUB invalido). Passadas de
    qualidade e traducao de titulo/sumario sao melhor esforco: falha
    neles nunca aborta a traducao.
    """
    hooks = hooks or RunnerHooks()
    log = hooks.log or (lambda _msg: None)

    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
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
            glossary = []
        else:
            save_glossary(glossary_path, glossary)
            log(f"glossario salvo com {len(glossary)} termo(s) em {glossary_path.name}")

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
        priming = ""

    if reset:
        estado_path = work / STATE_FILENAME
        if estado_path.exists():
            estado_path.unlink()
            log("cache anterior descartado (recomecando do zero)")

    policy = term_policy(config)
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
    outcome = translate_book(
        ebook.chapters,
        translator=provider,
        context=context,
        work_dir=work,
        book_hash=book_hash,
        model=model_for(config),
        max_tokens=max_tokens,
        token_count=token_counter,
        parallelism=config.execution.parallelism,
        cancel=hooks.cancel,
        progress=hooks.progress,
        spending_limit_usd=config.cost.spending_limit_usd,
        prices=config.prices_for(),
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
        appendix_entries=glossary,
    )
    log(f"concluido: {out_path}")
    return RunResult(
        translations=outcome.translations,
        usage=outcome.usage,
        out_path=out_path,
    )


def _translate_toc_labels(
    provider: Translator,
    ebook: Ebook,
    context: PromptContext,
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
    return [text for text in batch.texts]


def _translate_title(
    provider: Translator,
    ebook: Ebook,
    context: PromptContext,
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
