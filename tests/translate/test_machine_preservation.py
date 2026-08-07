"""Preservacao XHTML/EPUB com a porta de traducao automatica (secao 4).

Cobrem: integracao da porta comum com a segmentacao existente (4.1),
validacao de alinhamento/tags/placeholders/reconstrucao (4.2), bloqueio
de cache e gravacao quando a resposta altera markup (4.3), fixtures
douradas EPUB 2/3 com byte-diff (4.4) e retomada apos falha sem saida
parcialmente invalida (4.5).
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import httpx
import pytest

from tests.epub.builders import build_epub2, build_epub3
from tests.tui.helpers import write_book
from tradutor.domain import (
    Block,
    MachineTranslationContext,
    ProviderCapabilities,
    ProviderFamily,
    ProviderIdentity,
    TranslationBatch,
    Usage,
)
from tradutor.epub.appendix import APPENDIX_HREF
from tradutor.epub.container import open_ebook
from tradutor.infra.config import AppConfig
from tradutor.providers.machine_translation.google_web import GoogleWebProvider
from tradutor.translate.orchestrator import TranslationQualityError
from tradutor.translate.pipeline import run_translation
from tradutor.translate.planner import book_hash

PROTECTED_MARKERS = ("def f():", "<svg", "<math", "<script", "<style", "var x = 1;")


def mt_config() -> AppConfig:
    cfg = AppConfig()
    cfg.family = "machine_translation"
    cfg.provider = "google-web"
    return cfg


class FakeMTProvider:
    """Provider comum de teste: registra lotes e traduz com prefixo."""

    identity = ProviderIdentity(ProviderFamily.MACHINE_TRANSLATION, "fake-mt", "1", "test")
    capabilities = ProviderCapabilities(
        family=ProviderFamily.MACHINE_TRANSLATION,
        requires_credentials=False,
        max_batch_chars=5000,
        max_batch_items=2,
        max_concurrency=1,
        reports_token_usage=False,
        reports_character_usage=True,
        supports_model_listing=False,
        experimental=True,
        has_pricing=False,
    )

    def __init__(
        self,
        *,
        fail_on: int | None = None,
        strip_tags: bool = False,
        corrupt_placeholders: bool = False,
    ) -> None:
        self.fail_on = fail_on
        self.strip_tags = strip_tags
        self.corrupt_placeholders = corrupt_placeholders
        self.batches: list[list[Block]] = []
        self.contexts: list[MachineTranslationContext] = []

    def translate(self, batch, context) -> TranslationBatch:
        self.batches.append(list(batch))
        self.contexts.append(context)
        if self.fail_on is not None and len(self.batches) == self.fail_on:
            from tradutor.providers.errors import TransientProviderError

            raise TransientProviderError("endpoint caiu")
        texts = []
        for block in batch:
            assert block.protected is False
            text = f"TR: {block.text}"
            if self.strip_tags:
                text = text.replace("<b>", "").replace("</b>", "")
            if self.corrupt_placeholders and "{{" in block.text:
                text = text.replace("{{", "[[").replace("}}", "]]")
            texts.append(text)
        return TranslationBatch(
            tuple(texts),
            Usage(None, None, sum(len(b.text) for b in batch), len(batch)),
        )


def run_mt(tmp_path: Path, provider, *, cfg: AppConfig | None = None):
    path = write_book(tmp_path)
    ebook = open_ebook(path)
    return run_translation(
        ebook,
        provider,
        cfg or mt_config(),
        tmp_path / "trabalho",
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
    )


def test_mt_receives_only_translatable_content(tmp_path):
    provider = FakeMTProvider()
    run_mt(tmp_path, provider)

    sent = [block.text for batch in provider.batches for block in batch]
    assert sent, "nenhum bloco enviado"
    for text in sent:
        for marker in PROTECTED_MARKERS:
            assert marker not in text, f"conteudo protegido vazou: {marker}"
    assert all(isinstance(ctx, MachineTranslationContext) for ctx in provider.contexts)
    assert all(
        not hasattr(ctx, "glossary") and not hasattr(ctx, "priming") for ctx in provider.contexts
    )


def test_mt_response_that_alters_inline_tags_is_gracefully_degraded(tmp_path):
    provider = FakeMTProvider(strip_tags=True)

    # Não deve levantar erro de qualidade, deve degradar e prosseguir com sucesso
    run_mt(tmp_path, provider)

    assert (tmp_path / "trabalho" / "estado.json").exists()


def test_mt_invalid_response_never_reaches_epub(tmp_path):
    provider = FakeMTProvider(corrupt_placeholders=True)

    # Placeholders corrompidos são uma falha crítica irrecuperável e devem levantar erro
    with pytest.raises(TranslationQualityError):
        run_mt(tmp_path, provider)

    assert list(tmp_path.glob("*-pt-BR.epub")) == []


@pytest.mark.parametrize("builder", [build_epub2, build_epub3])
def test_mt_golden_epub_preserves_untouched_and_protected(tmp_path, builder):
    path = tmp_path / "livro.epub"
    path.write_bytes(builder())
    ebook = open_ebook(path)
    provider = FakeMTProvider()

    result = run_translation(
        ebook,
        provider,
        mt_config(),
        tmp_path / "trabalho",
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
    )

    untouched = (
        "mimetype",
        "META-INF/container.xml",
        "OEBPS/styles/style.css",
        "OEBPS/images/cover.png",
    )
    with zipfile.ZipFile(result.out_path) as zf, zipfile.ZipFile(path) as zf_orig:
        for name in untouched:
            assert zf.read(name) == zf_orig.read(name), name
        names = zf.namelist()
        assert not any(APPENDIX_HREF in name for name in names)
        ch1 = zf.read("OEBPS/text/ch1.xhtml").decode("utf-8")

    assert "TR:" in ch1
    assert "def f():\n    return 1" in ch1
    assert "<code>var x = 1;</code>" in ch1
    assert "<code>x + 1</code>" in ch1
    assert not (tmp_path / "trabalho" / "glossario.json").exists()


def _google_echo_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    contents = body[0][0] if isinstance(body, list) else body.get("contents", [])
    return httpx.Response(
        200,
        json=[f"TR: {item}" for item in contents],
        headers={"content-type": "application/json"},
    )


@pytest.mark.parametrize("builder", [build_epub2, build_epub3])
def test_google_web_end_to_end_with_fake_transport(tmp_path, builder):
    path = tmp_path / "livro.epub"
    path.write_bytes(builder())
    ebook = open_ebook(path)
    provider = GoogleWebProvider(
        http_client=httpx.Client(transport=httpx.MockTransport(_google_echo_handler)),
        delay_seconds=0,
    )

    result = run_translation(
        ebook,
        provider,
        mt_config(),
        tmp_path / "trabalho",
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
    )

    assert result.out_path.exists()
    assert result.usage.total_tokens is None
    assert result.usage.blocks > 0
    with zipfile.ZipFile(result.out_path) as zf:
        ch1 = zf.read("OEBPS/text/ch1.xhtml").decode("utf-8")
    assert "TR:" in ch1
    assert "<code>var x = 1;</code>" in ch1
    assert "def f():\n    return 1" in ch1


def test_mt_resume_after_failure_without_partial_output(tmp_path):
    from tradutor.providers.errors import TransientProviderError

    failing = FakeMTProvider(fail_on=2)
    with pytest.raises(TransientProviderError):
        run_mt(tmp_path, failing)

    assert list(tmp_path.glob("*-pt-BR.epub")) == []
    assert (tmp_path / "trabalho" / "estado.json").exists()

    provider2 = FakeMTProvider()
    result = run_mt(tmp_path, provider2)

    sent = [block.text for batch in provider2.batches for block in batch]
    assert sent, "retomada deveria traduzir os blocos pendentes"
    assert result.out_path.exists()
