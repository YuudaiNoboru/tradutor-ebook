"""Helpers para testes da TUI: provider fake, cofre em memoria e ambiente.

Reaproveita as fixtures douradas de ``tests/epub/builders.py`` para
montar livros reais em disco.
"""

from __future__ import annotations

import threading
from pathlib import Path

from tradutor.domain import PromptContext, TranslationBatch, Usage
from tradutor.providers import ConnectionResult


class DictSecretStore:
    """Cofre de segredos em memoria (substituto do keyring nos testes)."""

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(values or {})

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str) -> None:
        self.values[name] = value


class FakeProvider:
    """Provider fake: traduz com prefixo ``TR:`` e controla falhas/bloqueio.

    ``gate`` bloqueia as chamadas a partir de ``gate_from`` (1-based) ate
    ser liberado — usado no teste de cancelamento. ``fail_on`` levanta
    ``error`` na enesima chamada.
    """

    DEFAULT_USAGE = Usage(1, 1)

    def __init__(
        self,
        *,
        prefix: str = "TR: ",
        usage: Usage = DEFAULT_USAGE,
        gate: threading.Event | None = None,
        gate_from: int | None = None,
        fail_on: int | None = None,
        error: Exception | None = None,
        short_on: int | None = None,
        empty_on: int | None = None,
        connection: ConnectionResult | None = None,
        connection_error: Exception | None = None,
    ) -> None:
        self.prefix = prefix
        self.usage = usage
        self.gate = gate
        self.gate_from = gate_from
        self.fail_on = fail_on
        self.error = error
        self.short_on = short_on
        self.empty_on = empty_on
        self.connection = connection or ConnectionResult(True, "conexao OK", ("modelo-a",))
        self.connection_error = connection_error
        self.calls: list[list] = []
        self.contexts: list[PromptContext] = []

    def translate(self, batch, context: PromptContext) -> TranslationBatch:
        self.calls.append(list(batch))
        self.contexts.append(context)
        if (
            self.gate is not None
            and self.gate_from is not None
            and len(self.calls) >= self.gate_from
        ):
            self.gate.wait(10)
        if self.fail_on is not None and len(self.calls) == self.fail_on:
            assert self.error is not None
            raise self.error
        if self.empty_on is not None and len(self.calls) == self.empty_on:
            return TranslationBatch(texts=(), usage=self.usage)
        texts = tuple(f"{self.prefix}{block.text}" for block in batch)
        if self.short_on is not None and len(self.calls) == self.short_on:
            texts = texts[:1]
        return TranslationBatch(texts=texts, usage=self.usage)

    def test_connection(self) -> ConnectionResult:
        if self.connection_error is not None:
            raise self.connection_error
        return self.connection


def write_book(tmp_path: Path, name: str = "livro.epub", data: bytes | None = None) -> Path:
    """Grava um EPUB real em disco a partir dos builders dourados."""
    from tests.epub.builders import build_epub3

    path = tmp_path / name
    path.write_bytes(data if data is not None else build_epub3())
    return path
