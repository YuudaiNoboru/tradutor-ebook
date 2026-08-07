"""Orquestração condicionada pelas capacidades declaradas."""

from __future__ import annotations

import pytest

from tradutor.domain import (
    Block,
    Chapter,
    MachineTranslationContext,
    ProviderCapabilities,
    ProviderFamily,
    ProviderIdentity,
    TranslationBatch,
    Usage,
)
from tradutor.providers.errors import ProviderError
from tradutor.translate.orchestrator import translate_book


class _MachineFake:
    identity = ProviderIdentity(ProviderFamily.MACHINE_TRANSLATION, "fake", "1", "test")
    capabilities = ProviderCapabilities(
        family=ProviderFamily.MACHINE_TRANSLATION,
        requires_credentials=False,
        max_batch_chars=5,
        max_batch_items=1,
        max_concurrency=1,
        reports_token_usage=False,
        reports_character_usage=True,
    )

    def __init__(self) -> None:
        self.contexts = []
        self.batches = []

    def translate(self, batch, context):
        self.contexts.append(context)
        self.batches.append(tuple(block.text for block in batch))
        return TranslationBatch(
            tuple(block.text for block in batch),
            Usage(None, None, sum(len(block.text) for block in batch), len(batch)),
        )


def test_machine_provider_gets_small_context_and_character_batches(tmp_path):
    provider = _MachineFake()
    chapters = [
        Chapter(
            path="chapter.xhtml",
            blocks=[Block(0, "texto", "one"), Block(1, "texto", "two")],
        )
    ]

    outcome = translate_book(
        chapters,
        translator=provider,
        context=MachineTranslationContext("en", "pt-BR"),
        work_dir=tmp_path,
        book_hash="book",
        model="",
        max_tokens=100,
        token_count=len,
        parallelism=4,
    )

    assert outcome.usage.total_tokens is None
    assert all(isinstance(context, MachineTranslationContext) for context in provider.contexts)
    assert provider.batches == [("one",), ("two",)]


def test_machine_block_over_limit_raises_actionable_error(tmp_path):
    provider = _MachineFake()
    chapters = [
        Chapter(
            path="chapter.xhtml",
            blocks=[Block(0, "texto", "texto muito maior que o limite de cinco")],
        )
    ]

    with pytest.raises(ProviderError, match="limites do provider"):
        translate_book(
            chapters,
            translator=provider,
            context=MachineTranslationContext("en", "pt-BR"),
            work_dir=tmp_path,
            book_hash="book",
            model="",
            max_tokens=100,
            token_count=len,
        )


def test_machine_family_cache_key_isolates_from_llm(tmp_path):
    provider = _MachineFake()
    chapters = [Chapter(path="c.xhtml", blocks=[Block(0, "texto", "one")])]

    translate_book(
        chapters,
        translator=provider,
        context=MachineTranslationContext("en", "pt-BR"),
        work_dir=tmp_path,
        book_hash="book",
        model="deepseek-chat",
        max_tokens=100,
        token_count=len,
    )

    class _LLMFake:
        def translate(self, batch, context):
            return TranslationBatch(tuple(f"LLM: {block.text}" for block in batch), Usage(1, 1))

    llm = _LLMFake()
    from tradutor.domain import PromptContext

    outcome = translate_book(
        chapters,
        translator=llm,
        context=PromptContext(source_language="en", target_language="pt-BR"),
        work_dir=tmp_path,
        book_hash="book",
        model="deepseek-chat",
        max_tokens=100,
        token_count=len,
    )

    assert outcome.translations["c.xhtml"] == {0: "LLM: one"}
