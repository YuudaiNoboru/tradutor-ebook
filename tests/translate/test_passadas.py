"""Testes das passadas de qualidade (tarefas 5.1, 5.2 e 5.6).

Usam um provider fake implementando a porta ``Translator``: glossario
extraido e aplicado consistentemente, politica hibrida na primeira
ocorrencia, priming incluido no contexto e saida limpa (sem marcas de
IA).
"""

from __future__ import annotations

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
