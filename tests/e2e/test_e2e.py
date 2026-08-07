"""Testes ponta a ponta (grupo 10, tarefas 10.1 e 10.2).

EPUB real (fixtures douradas EPUB 2 e EPUB 3) -> traducao completa com
provider fake -> saida ``<nome>-pt-BR.epub`` valida: reaberta pelo
container, aprovada no validador epubcheck-like local (XML bem formado,
manifest/spine integros), arquivos intocados identicos byte a byte,
protegidos intactos e apendice de glossario presente.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tests.e2e.epubcheck_like import validate_epub
from tests.epub.builders import build_epub2, build_epub3
from tests.tui.helpers import FakeProvider, write_book
from tradutor.epub.appendix import APPENDIX_HREF
from tradutor.epub.container import open_ebook
from tradutor.infra.config import AppConfig
from tradutor.translate.pipeline import run_translation
from tradutor.translate.planner import book_hash

MAX_TOKENS = 4000

UNTOUCHED = {
    "mimetype",
    "META-INF/container.xml",
    "OEBPS/styles/style.css",
    "OEBPS/images/cover.png",
}

CASES = [
    pytest.param(
        build_epub2(),
        "livro2.epub",
        "OEBPS/toc.ncx",
        id="epub2",
    ),
    pytest.param(
        build_epub3(),
        "livro3.epub",
        "OEBPS/nav.xhtml",
        id="epub3",
    ),
]


def run_pipeline(tmp_path: Path, *, data: bytes, name: str):
    """Pipeline completo: abre o EPUB real, traduz e grava a saida."""
    path = write_book(tmp_path, name=name, data=data)
    result = run_translation(
        open_ebook(path),
        FakeProvider(),
        AppConfig(),
        tmp_path / "trabalho",
        lambda _ev: None,
        lambda: False,
        token_counter=len,
        book_hash=book_hash(path),
        max_tokens=MAX_TOKENS,
    )
    return path, result


@pytest.mark.parametrize("data,name,toc_path", CASES)
def test_e2e_translation_output_is_valid_epub(tmp_path, data, name, toc_path):
    source, result = run_pipeline(tmp_path, data=data, name=name)

    assert result.out_path == tmp_path / name.replace(".epub", "-pt-BR.epub")
    assert result.out_path != source
    assert result.out_path.exists()

    report = validate_epub(result.out_path)
    assert report.ok, "\n".join(f"{issue.severity}: {issue.message}" for issue in report.issues)

    with zipfile.ZipFile(result.out_path) as out, zipfile.ZipFile(source) as orig:
        assert out.namelist()[0] == "mimetype"
        for entry in UNTOUCHED:
            assert out.read(entry) == orig.read(entry), f"arquivo intocado mudou: {entry}"

        ch1 = out.read("OEBPS/text/ch1.xhtml").decode("utf-8")
        assert "TR: Hello" in ch1
        assert "TR: Last line." in ch1
        assert "var x = 1;" in ch1
        assert "def f():" in ch1

        ch2 = out.read("OEBPS/text/ch2.xhtml").decode("utf-8")
        assert "TR: Second chapter content." in ch2

        toc = out.read(toc_path).decode("utf-8")
        assert "TR: Chapter One" in toc

        opf = out.read("OEBPS/content.opf").decode("utf-8")
        assert "TR: The English Book" in opf
        assert "pt-BR" in opf

        assert f"OEBPS/{APPENDIX_HREF}" in out.namelist()

    reopened = open_ebook(result.out_path)
    assert reopened.container.title == "TR: The English Book"
    assert reopened.container.language == "pt-BR"
    assert [chapter.path for chapter in reopened.chapters] == [
        "OEBPS/text/ch1.xhtml",
        "OEBPS/text/ch2.xhtml",
        f"OEBPS/{APPENDIX_HREF}",
    ]
    assert len(reopened.toc_labels) == 2


@pytest.mark.parametrize("data,name,_toc", CASES)
def test_e2e_source_book_remains_untouched(tmp_path, data, name, _toc):
    source, result = run_pipeline(tmp_path, data=data, name=name)

    assert source.read_bytes() == data
    assert result.out_path != source
