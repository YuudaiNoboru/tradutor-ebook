"""Testes do teto de gasto na orquestracao (tarefas 7.5 e 7.7).

Cobrem: teto dispara apos cada lote contra o uso acumulado e aborta com
aviso, o progresso concluido fica preservado no cache para retomada com
novo teto, sem teto a traducao prossegue normalmente, e teto exige
tabela de precos.
"""

from __future__ import annotations

import json

import pytest

from tradutor.domain import (
    Block,
    Chapter,
    Prices,
    PromptContext,
    TermPolicy,
    TranslationBatch,
    Usage,
)
from tradutor.translate import SpendingLimitExceeded, translate_book
from tradutor.translate.estado import STATE_FILENAME

PRICES = Prices(input_per_million=1.0, output_per_million=1.0)


def book() -> list[Chapter]:
    return [
        Chapter(
            blocks=[
                Block(id=i, kind="texto", text=word)
                for i, word in enumerate(["aa", "bb", "cc", "dd"])
            ],
            path="c.xhtml",
        )
    ]


class UsageTranslator:
    """Provider fake que cobra US$ 1,00 por lote (1M de tokens de entrada)."""

    def __init__(self) -> None:
        self.calls = 0

    def translate(self, batch, context: PromptContext) -> TranslationBatch:
        self.calls += 1
        return TranslationBatch(
            texts=tuple(f"TR: {block.text}" for block in batch),
            usage=Usage(1_000_000, 0),
        )


def run(tmp_path, *, translator=None, **overrides):
    kwargs = dict(
        chapters=book(),
        context=PromptContext(
            source_language="en",
            target_language="pt-BR",
            policy=TermPolicy.HIBRIDO,
        ),
        work_dir=tmp_path,
        book_hash="h",
        model="m",
        max_tokens=2,
        token_count=len,
        parallelism=1,
        prices=PRICES,
    )
    kwargs.update(overrides)
    return translate_book(
        translator=translator if translator is not None else UsageTranslator(),
        **kwargs,
    )


def saved_translations(tmp_path) -> dict[int, str]:
    path = tmp_path / STATE_FILENAME
    assert path.exists()
    return {
        int(block_id): text
        for block_id, text in json.loads(path.read_text(encoding="utf-8"))["translations"][
            "c.xhtml"
        ].items()
    }


def test_spending_limit_aborts_and_preserves_cache(tmp_path):
    translator = UsageTranslator()
    with pytest.raises(SpendingLimitExceeded, match="teto de gasto atingido"):
        run(tmp_path, translator=translator, spending_limit_usd=2.5)

    assert translator.calls == 3
    assert saved_translations(tmp_path) == {0: "TR: aa", 1: "TR: bb", 2: "TR: cc"}


def test_resume_after_limit_with_new_limit_completes(tmp_path):
    with pytest.raises(SpendingLimitExceeded):
        run(tmp_path, spending_limit_usd=2.5)

    translator = UsageTranslator()
    outcome = run(tmp_path, translator=translator, spending_limit_usd=10.0)

    assert translator.calls == 1
    assert outcome.translations["c.xhtml"] == {
        0: "TR: aa",
        1: "TR: bb",
        2: "TR: cc",
        3: "TR: dd",
    }


def test_no_limit_completes_full_book(tmp_path):
    translator = UsageTranslator()
    outcome = run(tmp_path, translator=translator)

    assert translator.calls == 4
    assert len(outcome.translations["c.xhtml"]) == 4


def test_zero_limit_means_no_limit_even_with_prices(tmp_path):
    translator = UsageTranslator()
    outcome = run(tmp_path, translator=translator, spending_limit_usd=0.0)

    assert translator.calls == 4
    assert len(outcome.translations["c.xhtml"]) == 4


def test_limit_exact_boundary_does_not_abort(tmp_path):
    chapters = [
        Chapter(
            blocks=[
                Block(id=i, kind="texto", text=word) for i, word in enumerate(["aa", "bb", "cc"])
            ],
            path="c.xhtml",
        )
    ]
    translator = UsageTranslator()
    outcome = run(tmp_path, translator=translator, chapters=chapters, spending_limit_usd=3.0)

    assert translator.calls == 3
    assert len(outcome.translations["c.xhtml"]) == 3


def test_spending_limit_requires_prices(tmp_path):
    with pytest.raises(ValueError, match="tabela de precos"):
        run(tmp_path, spending_limit_usd=1.0, prices=None)


def test_negative_limit_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="teto"):
        run(tmp_path, spending_limit_usd=-1.0)


def test_accumulated_cost_from_cache_counts_toward_limit(tmp_path):
    with pytest.raises(SpendingLimitExceeded):
        run(tmp_path, spending_limit_usd=2.5)

    translator = UsageTranslator()
    with pytest.raises(SpendingLimitExceeded):
        run(tmp_path, translator=translator, spending_limit_usd=3.5)

    assert translator.calls == 1
    assert saved_translations(tmp_path) == {0: "TR: aa", 1: "TR: bb", 2: "TR: cc", 3: "TR: dd"}
