"""Testes da orquestracao (tarefas 6.4, 6.5, 6.6 e 6.7).

Cobrem: retomada apos falha de rede e cancelamento (6.5), invalidacao
do estado por mudanca de modelo/idioma/glossario (6.7), cache corrompido
parcial e total (6.6), paralelismo default 4 (6.4), fidelidade de
placeholders com reprocessamento do lote e acumulo de uso entre
execucoes.
"""

from __future__ import annotations

import json
import re
import threading
import time

import pytest

from tradutor.domain import (
    Block,
    Chapter,
    PromptContext,
    TermPolicy,
    TranslationBatch,
    Usage,
)
from tradutor.providers.errors import ProviderError, TransientProviderError
from tradutor.translate import (
    TranslationCancelled,
    TranslationQualityError,
    translate_book,
)
from tradutor.translate.estado import STATE_FILENAME


def chapter(path: str, *texts: str) -> Chapter:
    return Chapter(
        blocks=[Block(id=i, kind="texto", text=text) for i, text in enumerate(texts)],
        path=path,
    )


def book() -> list[Chapter]:
    return [
        chapter("cap1.xhtml", "Primeiro bloco", "Segundo bloco"),
        chapter("cap2.xhtml", "Terceiro bloco"),
    ]


def context() -> PromptContext:
    return PromptContext(
        source_language="en",
        target_language="pt-BR",
        policy=TermPolicy.HIBRIDO,
        glossary=(("cache", "cache"),),
    )


class ScriptedTranslator:
    """Provider fake com script: prefixo nas traducoes, falhas e corrupcao."""

    def __init__(
        self,
        *,
        error: Exception | None = None,
        error_on_calls: frozenset[int] = frozenset(),
        corrupt_on_calls: frozenset[int] = frozenset(),
    ) -> None:
        self.error = error
        self.error_on_calls = error_on_calls
        self.corrupt_on_calls = corrupt_on_calls
        self.calls: list[list[Block]] = []

    def translate(self, batch, context: PromptContext) -> TranslationBatch:
        self.calls.append(list(batch))
        call = len(self.calls)
        if call in self.error_on_calls:
            raise self.error
        texts = []
        for block in batch:
            if call in self.corrupt_on_calls and "{{" in block.text:
                texts.append(
                    re.sub(
                        r"\{\{(\d+)\}\}",
                        lambda m: "{{" + str(int(m.group(1)) + 1) + "}}",
                        block.text,
                    )
                )
            else:
                texts.append(f"TR: {block.text}")
        return TranslationBatch(texts=tuple(texts), usage=Usage(1, 1))


def run(tmp_path, *, translator=None, **overrides):
    kwargs = dict(
        chapters=book(),
        context=context(),
        work_dir=tmp_path,
        book_hash="hash-1",
        model="deepseek-chat",
        max_tokens=30,
        token_count=len,
        parallelism=2,
    )
    kwargs.update(overrides)
    return translate_book(
        translator=translator if translator is not None else ScriptedTranslator(),
        **kwargs,
    )


def sent_texts(translator: ScriptedTranslator) -> list[str]:
    return [block.text for batch in translator.calls for block in batch]


def test_translates_all_blocks_and_persists_state(tmp_path):
    outcome = run(tmp_path)

    assert outcome.translations == {
        "cap1.xhtml": {0: "TR: Primeiro bloco", 1: "TR: Segundo bloco"},
        "cap2.xhtml": {0: "TR: Terceiro bloco"},
    }
    assert outcome.usage == Usage(2, 2)

    path = tmp_path / STATE_FILENAME
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["key"]
    assert saved["translations"]["cap1.xhtml"]["0"] == "TR: Primeiro bloco"
    assert saved["usage"] == {"prompt_tokens": 2, "completion_tokens": 2}


def test_second_run_with_complete_state_makes_no_calls(tmp_path):
    run(tmp_path)
    translator = ScriptedTranslator()
    outcome = run(tmp_path, translator=translator)

    assert translator.calls == []
    assert outcome.translations["cap1.xhtml"] == {0: "TR: Primeiro bloco", 1: "TR: Segundo bloco"}


def test_progress_callback_counts_blocks(tmp_path):
    seen: list[tuple[int, int]] = []
    run(tmp_path, progress=lambda done, total: seen.append((done, total)))

    assert seen[0] == (0, 3)
    assert seen[-1] == (3, 3)
    assert [done for done, _ in seen] == sorted(done for done, _ in seen)


def test_resume_after_network_failure_skips_translated_blocks(tmp_path):
    error = TransientProviderError("rede caiu")
    with pytest.raises(TransientProviderError):
        run(
            tmp_path,
            translator=ScriptedTranslator(error=error, error_on_calls=frozenset({2})),
            parallelism=1,
        )

    translator = ScriptedTranslator()
    outcome = run(tmp_path, translator=translator)

    assert sent_texts(translator) == ["Terceiro bloco"]
    assert outcome.translations == {
        "cap1.xhtml": {0: "TR: Primeiro bloco", 1: "TR: Segundo bloco"},
        "cap2.xhtml": {0: "TR: Terceiro bloco"},
    }


def test_resume_accumulates_usage_across_runs(tmp_path):
    error = TransientProviderError("rede caiu")
    with pytest.raises(TransientProviderError):
        run(
            tmp_path,
            translator=ScriptedTranslator(error=error, error_on_calls=frozenset({2})),
            parallelism=1,
        )

    outcome = run(tmp_path)
    assert outcome.usage == Usage(2, 2)


def test_cancel_preserves_progress_and_resume_completes(tmp_path):
    first_done = threading.Event()

    class CancelTranslator:
        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            first_done.set()
            return TranslationBatch(texts=tuple(f"TR: {b.text}" for b in batch), usage=Usage(1, 1))

    with pytest.raises(TranslationCancelled):
        run(tmp_path, translator=CancelTranslator(), parallelism=1, cancel=first_done.is_set)

    saved = json.loads((tmp_path / STATE_FILENAME).read_text(encoding="utf-8"))
    assert saved["translations"]["cap1.xhtml"]["0"] == "TR: Primeiro bloco"

    outcome = run(tmp_path)
    assert outcome.translations == {
        "cap1.xhtml": {0: "TR: Primeiro bloco", 1: "TR: Segundo bloco"},
        "cap2.xhtml": {0: "TR: Terceiro bloco"},
    }


def test_model_change_invalidates_cached_state(tmp_path):
    run(tmp_path)

    translator = ScriptedTranslator()
    outcome = run(tmp_path, translator=translator, model="outro-modelo")

    assert sent_texts(translator) == ["Primeiro bloco", "Segundo bloco", "Terceiro bloco"]
    assert outcome.translations["cap1.xhtml"][0] == "TR: Primeiro bloco"


def test_language_change_invalidates_cached_state(tmp_path):
    run(tmp_path)

    changed = PromptContext(
        source_language="en",
        target_language="es",
        policy=TermPolicy.HIBRIDO,
        glossary=(("cache", "cache"),),
    )
    translator = ScriptedTranslator()
    outcome = translate_book(
        chapters=book(),
        translator=translator,
        context=changed,
        work_dir=tmp_path,
        book_hash="hash-1",
        model="deepseek-chat",
        max_tokens=100,
        token_count=len,
        parallelism=2,
    )

    assert sent_texts(translator) == ["Primeiro bloco", "Segundo bloco", "Terceiro bloco"]
    assert outcome.translations["cap2.xhtml"][0] == "TR: Terceiro bloco"


def test_glossary_edit_invalidates_cached_state(tmp_path):
    run(tmp_path)

    edited = PromptContext(
        source_language="en",
        target_language="pt-BR",
        policy=TermPolicy.HIBRIDO,
        glossary=(("cache", "cache editado"),),
    )
    translator = ScriptedTranslator()
    translate_book(
        chapters=book(),
        translator=translator,
        context=edited,
        work_dir=tmp_path,
        book_hash="hash-1",
        model="deepseek-chat",
        max_tokens=100,
        token_count=len,
        parallelism=2,
    )

    assert sent_texts(translator) == ["Primeiro bloco", "Segundo bloco", "Terceiro bloco"]


def test_corrupted_state_file_is_ignored_and_book_retranslated(tmp_path):
    (tmp_path / STATE_FILENAME).write_text("{quebrado", encoding="utf-8")

    translator = ScriptedTranslator()
    outcome = run(tmp_path, translator=translator)

    assert sent_texts(translator) == ["Primeiro bloco", "Segundo bloco", "Terceiro bloco"]
    assert outcome.translations["cap1.xhtml"][0] == "TR: Primeiro bloco"


def test_partially_corrupted_state_retranslates_only_affected(tmp_path):
    run(tmp_path)
    path = tmp_path / STATE_FILENAME
    data = json.loads(path.read_text(encoding="utf-8"))
    data["translations"]["cap1.xhtml"]["1"] = 12345
    path.write_text(json.dumps(data), encoding="utf-8")

    translator = ScriptedTranslator()
    outcome = run(tmp_path, translator=translator)

    assert sent_texts(translator) == ["Segundo bloco"]
    assert outcome.translations == {
        "cap1.xhtml": {0: "TR: Primeiro bloco", 1: "TR: Segundo bloco"},
        "cap2.xhtml": {0: "TR: Terceiro bloco"},
    }


def test_unfaithful_batch_is_retried_until_clean(tmp_path):
    chapters = [Chapter(blocks=[Block(id=0, kind="texto", text="Ola {{0}} mundo")], path="c.xhtml")]
    translator = ScriptedTranslator(corrupt_on_calls=frozenset({1}))

    outcome = translate_book(
        chapters=chapters,
        translator=translator,
        context=context(),
        work_dir=tmp_path,
        book_hash="h",
        model="m",
        max_tokens=100,
        token_count=len,
        parallelism=1,
    )

    assert outcome.translations["c.xhtml"] == {0: "TR: Ola {{0}} mundo"}
    assert len(translator.calls) == 2


def test_unfaithful_batch_exhausts_attempts_and_raises(tmp_path):
    chapters = [Chapter(blocks=[Block(id=0, kind="texto", text="Ola {{0}} mundo")], path="c.xhtml")]
    translator = ScriptedTranslator(corrupt_on_calls=frozenset({1, 2, 3}))

    with pytest.raises(TranslationQualityError):
        translate_book(
            chapters=chapters,
            translator=translator,
            context=context(),
            work_dir=tmp_path,
            book_hash="h",
            model="m",
            max_tokens=100,
            token_count=len,
            parallelism=1,
        )
    assert len(translator.calls) == 3
    assert not (tmp_path / STATE_FILENAME).exists()


def test_ai_mark_rejected_and_retried(tmp_path):
    chapters = [Chapter(blocks=[Block(id=0, kind="texto", text="Texto normal")], path="c.xhtml")]

    class MarkTranslator:
        def __init__(self) -> None:
            self.calls = 0

        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            self.calls += 1
            text = "Texto [traduzido por IA]" if self.calls == 1 else "Texto limpo"
            return TranslationBatch(texts=(text,), usage=Usage(1, 1))

    translator = MarkTranslator()
    outcome = translate_book(
        chapters=chapters,
        translator=translator,
        context=context(),
        work_dir=tmp_path,
        book_hash="h",
        model="m",
        max_tokens=100,
        token_count=len,
        parallelism=1,
    )

    assert outcome.translations["c.xhtml"] == {0: "Texto limpo"}
    assert translator.calls == 2


def test_rejects_invalid_parallelism(tmp_path):
    with pytest.raises(ValueError, match="paralelismo"):
        run(tmp_path, parallelism=0)


def test_protected_and_blank_blocks_are_not_sent(tmp_path):
    chapters = [
        Chapter(
            blocks=[
                Block(id=0, kind="texto", text="Normal"),
                Block(id=1, kind="codigo", text="code", protected=True),
                Block(id=2, kind="texto", text="   "),
            ],
            path="c.xhtml",
        )
    ]
    translator = ScriptedTranslator()
    outcome = translate_book(
        chapters=chapters,
        translator=translator,
        context=context(),
        work_dir=tmp_path,
        book_hash="h",
        model="m",
        max_tokens=100,
        token_count=len,
        parallelism=1,
    )

    assert sent_texts(translator) == ["Normal"]
    assert outcome.translations["c.xhtml"] == {0: "TR: Normal"}


def test_sibling_failure_keeps_success_and_raises(tmp_path):
    class SlowSuccessTranslator:
        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            if any("Terceiro" in block.text for block in batch):
                raise TransientProviderError("rede caiu")
            time.sleep(0.2)
            return TranslationBatch(texts=tuple(f"TR: {b.text}" for b in batch), usage=Usage(1, 1))

    with pytest.raises(TransientProviderError):
        run(tmp_path, translator=SlowSuccessTranslator(), parallelism=2)

    saved = json.loads((tmp_path / STATE_FILENAME).read_text(encoding="utf-8"))
    assert saved["translations"]["cap1.xhtml"]["0"] == "TR: Primeiro bloco"
    assert "cap2.xhtml" not in saved["translations"]


def test_multiple_failures_report_first_error(tmp_path):
    class AlwaysFail:
        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            raise TransientProviderError("rede caiu")

    with pytest.raises(TransientProviderError, match="rede caiu"):
        run(tmp_path, translator=AlwaysFail(), parallelism=2)


def test_internal_error_is_reported_as_provider_error(tmp_path):
    class BrokenTranslator:
        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            raise ValueError("estourou")

    with pytest.raises(ProviderError, match="falha interna no lote: estourou"):
        run(tmp_path, translator=BrokenTranslator(), parallelism=1)


def test_second_internal_error_keeps_first_error(tmp_path):
    class MixedFail:
        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            if any("Primeiro" in block.text for block in batch):
                time.sleep(0.2)
                raise ValueError("estourou")
            raise TransientProviderError("rede caiu")

    with pytest.raises(TransientProviderError, match="rede caiu"):
        run(tmp_path, translator=MixedFail(), parallelism=2)


def test_default_parallelism_is_four(tmp_path):
    started: list[list[Block]] = []
    lock = threading.Lock()
    entered = threading.Event()
    release = threading.Event()

    class BlockingTranslator:
        def translate(self, batch, context: PromptContext) -> TranslationBatch:
            with lock:
                started.append(batch)
                now = len(started)
            if now >= 4:
                entered.set()
            assert release.wait(timeout=10)
            return TranslationBatch(texts=tuple(f"TR: {b.text}" for b in batch), usage=Usage(1, 1))

    chapters = [chapter(f"cap{i}.xhtml", f"texto {i}") for i in range(5)]
    thread = threading.Thread(
        target=translate_book,
        kwargs={
            "chapters": chapters,
            "translator": BlockingTranslator(),
            "context": context(),
            "work_dir": tmp_path,
            "book_hash": "h",
            "model": "m",
            "max_tokens": 3,
            "token_count": len,
        },
    )
    thread.start()

    assert entered.wait(timeout=10)
    assert len(started) == 4
    release.set()
    thread.join(timeout=10)
    assert not thread.is_alive()
