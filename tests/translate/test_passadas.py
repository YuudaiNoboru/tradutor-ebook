"""Testes das passadas de qualidade (tarefas 5.1, 5.2 e 5.6).

Usam um provider fake implementando a porta ``Translator``: glossario
extraido e aplicado consistentemente, politica hibrida na primeira
ocorrencia, priming incluido no contexto e saida limpa (sem marcas de
IA).
"""

from __future__ import annotations

import threading

from tradutor.domain import (
    Block,
    Chapter,
    PassadaTask,
    PromptContext,
    TermPolicy,
    TranslationBatch,
    Usage,
)
from tradutor.translate import build_priming, extract_glossary

SAMPLES = [
    "This book covers queue data structures and threading.",
    "A queue is a FIFO structure. The cache speeds up reads.",
]


def chapter(text: str, title: str = "Cap") -> Chapter:
    return Chapter(
        blocks=[Block(id=0, kind="titulo", text=title), Block(id=1, kind="paragrafo", text=text)],
        title=title,
    )


def chapters() -> list[Chapter]:
    return [chapter(SAMPLES[0], "One"), chapter(SAMPLES[1], "Two")]


class FakeTranslator:
    """Provider fake: devolve respostas predefinidas e registra chamadas."""

    def __init__(self, responses: list[TranslationBatch]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[list[Block], PromptContext]] = []

    def translate(self, batch: list[Block], context: PromptContext) -> TranslationBatch:
        self.calls.append((list(batch), context))
        return self._responses.pop(0)


class GlossaryTranslator:
    """Provider fake que aplica o glossario com politica hibrida.

    Na primeira ocorrencia de um termo traduz: ``traducao (original)``;
    nas demais, apenas a traducao. Termos sem mudanca de grafia nao
    recebem parenteses. Tambem aplica o priming no texto quando presente,
    simulando consistencia de tom.
    """

    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        self.last_context: PromptContext | None = None
        self.calls = 0

    def translate(self, batch: list[Block], context: PromptContext) -> TranslationBatch:
        self.last_context = context
        self.calls += 1
        texts = []
        for block in batch:
            text = block.text
            seen: set[str] = set()
            for termo, traducao in context.glossary:
                if termo.lower() not in text.lower():
                    continue
                if context.policy is TermPolicy.MANTER:
                    replacement = termo
                elif (
                    context.policy is TermPolicy.TRADUZIR
                    or termo in seen
                    or traducao.lower() == termo.lower()
                ):
                    replacement = traducao
                else:
                    replacement = f"{traducao} ({termo})"
                text = _replace_ci(text, termo, replacement)
                seen.add(termo)
            if context.priming:
                text = f"{text}{self.suffix}"
            texts.append(text)
        return TranslationBatch(texts=tuple(texts), usage=Usage(10, 5))


def _replace_ci(text: str, termo: str, replacement: str) -> str:
    lower = text.lower()
    start = 0
    while True:
        found = lower.find(termo.lower(), start)
        if found == -1:
            return text
        text = text[:found] + replacement + text[found + len(termo) :]
        lower = text.lower()
        start = found + len(replacement)


def test_extract_glossary_parses_entries_with_glossario_task():
    fake = FakeTranslator(
        [TranslationBatch(texts=("queue -> fila\ncache -> cache",), usage=Usage(10, 5))]
    )
    entries = extract_glossary(fake, chapters())

    assert entries == [("queue", "fila"), ("cache", "cache")]
    batch, context = fake.calls[0]
    assert context.task is PassadaTask.GLOSSARIO
    assert context.source_language == "auto"
    assert context.target_language == "pt-BR"
    assert len(batch) == 1
    assert "queue data structures" in batch[0].text


def test_extract_glossary_accepts_colon_separator():
    fake = FakeTranslator([TranslationBatch(texts=("queue: fila",), usage=Usage(10, 5))])
    entries = extract_glossary(fake, chapters())
    assert entries == [("queue", "fila")]


def test_extract_glossary_ignores_malformed_lines():
    fake = FakeTranslator(
        [TranslationBatch(texts=("queue -> fila\nsem separador",), usage=Usage(10, 5))]
    )
    entries = extract_glossary(fake, chapters())
    assert entries == [("queue", "fila")]


def test_extract_glossary_accepts_multi_item_response():
    """Resposta como array com uma entrada por item (caso real do DeepSeek)."""
    fake = FakeTranslator(
        [
            TranslationBatch(
                texts=("queue -> fila", "cache -> cache", "threading:\nthread -> thread"),
                usage=Usage(10, 5),
            )
        ]
    )
    entries = extract_glossary(fake, chapters())
    assert entries == [("queue", "fila"), ("cache", "cache"), ("thread", "thread")]


def test_build_priming_joins_multi_item_response():
    fake = FakeTranslator(
        [TranslationBatch(texts=("Tom formal.", "Vocabulario tecnico."), usage=Usage(10, 5))]
    )
    priming = build_priming(fake, chapters())
    assert priming == "Tom formal.\nVocabulario tecnico."


def test_extract_glossary_skips_protected_blocks_and_limits_sample():
    book = [
        Chapter(
            blocks=[
                Block(id=0, kind="codigo", text="secret code here", protected=True),
                Block(id=1, kind="paragrafo", text="only this text is sampled"),
            ]
        )
    ]
    fake = FakeTranslator([TranslationBatch(texts=("termo -> termo",), usage=Usage(1, 1))])
    extract_glossary(fake, book)
    batch, _ = fake.calls[0]
    assert "secret code" not in batch[0].text
    assert "only this text is sampled" in batch[0].text


def test_extract_glossary_respects_max_chapters_and_chars():
    book = [
        chapter("Texto do capitulo um.", title="Um"),
        chapter("Texto do capitulo dois.", title="Dois"),
    ]
    fake = FakeTranslator([TranslationBatch(texts=("termo -> termo",), usage=Usage(1, 1))])
    extract_glossary(fake, book, max_chapters=1)
    batch, _ = fake.calls[0]
    assert "capitulo um" in batch[0].text
    assert "capitulo dois" not in batch[0].text

    fake2 = FakeTranslator([TranslationBatch(texts=("termo -> termo",), usage=Usage(1, 1))])
    extract_glossary(fake2, book, max_chapters=2, max_chars=10)
    batch2, _ = fake2.calls[0]
    assert "capitulo dois" not in batch2[0].text
    assert batch2[0].text.strip()


def test_extract_glossary_handles_blank_and_empty_lines():
    fake = FakeTranslator(
        [
            TranslationBatch(
                texts=("queue -> fila\n\n-> so alvo\n  \ncache : cache",), usage=Usage(10, 5)
            )
        ]
    )
    entries = extract_glossary(fake, chapters())
    assert entries == [("queue", "fila"), ("cache", "cache")]


def test_extract_glossary_empty_book_returns_without_calling():
    fake = FakeTranslator([])
    assert extract_glossary(fake, []) == []
    assert fake.calls == []


def test_build_priming_returns_summary_with_priming_task():
    fake = FakeTranslator(
        [TranslationBatch(texts=("Livro tecnico, tom direto.",), usage=Usage(10, 5))]
    )
    priming = build_priming(fake, chapters())

    assert priming == "Livro tecnico, tom direto."
    _, context = fake.calls[0]
    assert context.task is PassadaTask.PRIMING


def test_build_priming_empty_book_returns_without_calling():
    fake = FakeTranslator([])
    assert build_priming(fake, []) == ""
    assert fake.calls == []


def test_glossary_applied_consistently_with_hybrid_policy():
    translator = GlossaryTranslator()
    glossary = (("queue", "fila"), ("cache", "cache"))
    context = PromptContext(
        source_language="en",
        target_language="pt-BR",
        policy=TermPolicy.HIBRIDO,
        glossary=glossary,
        priming="Livro tecnico, tom direto.",
    )
    batch = [chapter(SAMPLES[0]).blocks[1], chapter(SAMPLES[1]).blocks[1]]
    result = translator.translate(batch, context)

    first = result.texts[0]
    assert "fila (queue)" in first
    second = result.texts[1]
    assert "fila (queue)" in second
    assert "(queue)" not in first.replace("fila (queue)", "", 1)
    assert "(queue)" not in second.replace("fila (queue)", "", 1)
    assert "cache" in second
    assert translator.last_context is context


def test_glossary_manter_policy_keeps_original():
    translator = GlossaryTranslator()
    context = PromptContext(policy=TermPolicy.MANTER, glossary=(("queue", "fila"),))
    result = translator.translate([chapter(SAMPLES[0]).blocks[1]], context)
    assert "queue" in result.texts[0]
    assert "fila" not in result.texts[0]


def test_glossary_traduzir_policy_translates_all_occurrences():
    translator = GlossaryTranslator()
    context = PromptContext(policy=TermPolicy.TRADUZIR, glossary=(("queue", "fila"),))
    result = translator.translate([chapter(SAMPLES[0]).blocks[1]], context)
    assert "fila" in result.texts[0]
    assert "queue" not in result.texts[0]
    assert "(queue)" not in result.texts[0]


def test_priming_included_in_context_reaches_translation():
    translator = GlossaryTranslator(suffix=" (estilo direto)")
    context = PromptContext(priming="Livro tecnico, tom direto.")
    result = translator.translate([chapter(SAMPLES[0]).blocks[1]], context)
    assert "(estilo direto)" in result.texts[0]


class _ParallelProbe:
    """Prova o paralelismo das passadas: a primeira chamada bloqueia ate a
    segunda iniciar; se a primeira terminar sem a segunda chegar (execucao
    sequencial), falha com mensagem clara."""

    def __init__(self, provider) -> None:
        self._provider = provider
        self._lock = threading.Lock()
        self._first_started = threading.Event()
        self._second_started = threading.Event()
        self.overlap = False

    def translate(self, batch, context) -> TranslationBatch:
        with self._lock:
            first = not self._first_started.is_set()
            if first:
                self._first_started.set()
            else:
                self.overlap = True
                self._second_started.set()
        if first and not self._second_started.wait(5):
            raise AssertionError("primeira passada terminou sem a segunda iniciar")
        return self._provider.translate(batch, context)


def _run_pipeline(tmp_path, provider) -> None:
    from tests.tui.helpers import write_book
    from tradutor.epub.container import open_ebook
    from tradutor.infra.config import AppConfig
    from tradutor.translate.pipeline import run_translation
    from tradutor.translate.planner import book_hash

    path = write_book(tmp_path)
    run_translation(
        open_ebook(path),
        provider,
        AppConfig(),
        tmp_path / "trabalho",
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
        max_tokens=3000,
    )


def test_pipeline_runs_glossary_and_priming_in_parallel(tmp_path):
    from tests.tui.helpers import FakeProvider

    provider = FakeProvider()
    probe = _ParallelProbe(provider)
    _run_pipeline(tmp_path, probe)

    assert probe.overlap is True
    assert (tmp_path / "trabalho" / "glossario.json").exists()
    assert any(context.task is PassadaTask.GLOSSARIO for context in provider.contexts)
    assert any(context.task is PassadaTask.PRIMING for context in provider.contexts)


def test_pipeline_glossary_failure_does_not_block_priming(tmp_path):
    from tests.tui.helpers import FakeProvider
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(
        fail_task=PassadaTask.GLOSSARIO, error=ProviderError("falha no glossario")
    )
    _run_pipeline(tmp_path, provider)

    assert not (tmp_path / "trabalho" / "glossario.json").exists()
    assert any(context.task is PassadaTask.PRIMING for context in provider.contexts)


def test_pipeline_priming_failure_does_not_block_glossary(tmp_path):
    from tests.tui.helpers import FakeProvider
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(fail_task=PassadaTask.PRIMING, error=ProviderError("falha no priming"))
    _run_pipeline(tmp_path, provider)

    assert (tmp_path / "trabalho" / "glossario.json").exists()
    assert any(context.task is PassadaTask.GLOSSARIO for context in provider.contexts)


def test_load_save_priming(tmp_path):
    from tradutor.translate.passadas import load_priming, save_priming

    file_path = tmp_path / "priming.txt"
    assert load_priming(file_path) == ""

    save_priming(file_path, "Tom informal, estilo jornalístico.")
    assert file_path.exists()
    assert load_priming(file_path) == "Tom informal, estilo jornalístico."


def test_pipeline_saves_priming_txt_and_reuses_on_subsequent_run(tmp_path):
    from tests.tui.helpers import FakeProvider, write_book
    from tradutor.epub.container import open_ebook
    from tradutor.infra.config import AppConfig
    from tradutor.translate.pipeline import run_translation
    from tradutor.translate.planner import book_hash

    path = write_book(tmp_path)
    trabalho_dir = tmp_path / "trabalho_priming"

    provider1 = FakeProvider()
    run_translation(
        open_ebook(path),
        provider1,
        AppConfig(),
        trabalho_dir,
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
        max_tokens=3000,
    )

    priming_file = trabalho_dir / "priming.txt"
    assert priming_file.exists()

    # Segunda execução: com glossario.json e priming.txt existentes
    provider2 = FakeProvider()
    run_translation(
        open_ebook(path),
        provider2,
        AppConfig(),
        trabalho_dir,
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
        max_tokens=3000,
    )

    # Não deve ter chamado a passada de priming na segunda execução
    assert not any(context.task is PassadaTask.PRIMING for context in provider2.contexts)


def test_pipeline_skips_quality_passes_when_disabled(tmp_path):
    from tests.tui.helpers import FakeProvider, write_book
    from tradutor.epub.container import open_ebook
    from tradutor.infra.config import AppConfig
    from tradutor.translate.pipeline import run_translation
    from tradutor.translate.planner import book_hash

    path = write_book(tmp_path)
    trabalho_dir = tmp_path / "trabalho_no_quality"

    provider = FakeProvider()
    run_translation(
        open_ebook(path),
        provider,
        AppConfig(),
        trabalho_dir,
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
        max_tokens=3000,
        enable_quality_passes=False,
    )

    assert not any(context.task is PassadaTask.GLOSSARIO for context in provider.contexts)
    assert not any(context.task is PassadaTask.PRIMING for context in provider.contexts)


def test_pipeline_default_token_counter_and_book_hash(tmp_path):
    from tests.tui.helpers import FakeProvider, write_book
    from tradutor.epub.container import open_ebook
    from tradutor.infra.config import AppConfig
    from tradutor.translate.pipeline import run_translation

    path = write_book(tmp_path)
    trabalho_dir = tmp_path / "trabalho_defaults"

    provider = FakeProvider()
    res = run_translation(
        open_ebook(path),
        provider,
        AppConfig(),
        trabalho_dir,
        lambda _ev: None,
        lambda: False,
    )
    assert res.out_path.exists()
