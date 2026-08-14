"""Testes de regressao para parsing e serializacao UTF-8 sem declaracao de charset.

Garante que documentos XHTML sem tag <meta charset="utf-8"> ou sem declaracao XML
sejam processados estritamente em UTF-8 por lxml.html, sem introduzir artefatos Â\xa0
ou corromper pontuacoes de 3 bytes (aspas curvas, travessoes, etc.).
"""

from __future__ import annotations

from tradutor.epub.index_rebuilder import is_index_document, rebuild_index_xhtml
from tradutor.epub.segments import parse_chapter, render_chapter
from tradutor.epub.toc import apply_nav_labels, extract_nav_labels


def test_parse_and_render_chapter_without_meta_charset():
    # XHTML em bytes sem <meta charset> nem <?xml ...?>
    # Contem &nbsp; (\xc2\xa0), aspas curvas inglesas (\xe2\x80\x9c e \xe2\x80\x9d) e travessao (\xe2\x80\x94)
    raw_xhtml = (
        b'<html xmlns="http://www.w3.org/1999/xhtml">'
        b"<head><title>Teste Sem Charset</title></head>"
        b"<body>"
        b"<h1>Cap\xc3\xadtulo &nbsp; 1 \xe2\x80\x94 Introdu\xc3\xa7\xc3\xa3o</h1>"
        b"<p>Texto com &nbsp;&nbsp; recuo, \xe2\x80\x9caspas curvas\xe2\x80\x9d e travess\xc3\xa3o \xe2\x80\x94 aqui.</p>"
        b"</body></html>"
    )

    chapter = parse_chapter(raw_xhtml, path="ch01.xhtml")

    assert len(chapter.blocks) == 2
    assert "Â" not in chapter.blocks[0].text
    assert "Â" not in chapter.blocks[1].text
    assert "\xa0" in chapter.blocks[0].text
    assert "“aspas curvas”" in chapter.blocks[1].text
    assert "travessão — aqui" in chapter.blocks[1].text

    # Reconstrucao
    translations = {
        0: "Capítulo &nbsp; 1 — Traduzido",
        1: "Texto com &nbsp;&nbsp; recuo traduzido, “aspas traduzidas” e travessão — fim.",
    }
    rendered = render_chapter(raw_xhtml, chapter.blocks, translations)

    # Verifica se nao ha byte Â (\xc3\x82) antes de \xa0 (\xc2\xa0)
    assert b"\xc3\x82\xc2\xa0" not in rendered
    decoded = rendered.decode("utf-8")
    assert "“aspas traduzidas”" in decoded
    assert "travessão — fim." in decoded
    assert "Â" not in decoded


def test_index_rebuilder_without_meta_charset():
    raw_index = (
        b'<html xmlns="http://www.w3.org/1999/xhtml">'
        b"<head><title>Index</title></head>"
        b'<body epub:type="index">'
        b"<h1>Index</h1>"
        b'<h2 class="index-letter">A</h2>'
        b'<p class="entry"><a href="ch1.xhtml#a1">Architecture &nbsp; Patterns</a>, 10</p>'
        b'<p class="entry"><a href="ch1.xhtml#a2">\xe2\x80\x9cAgile\xe2\x80\x9d Principles \xe2\x80\x94 \xc3\x89tica</a>, 12</p>'
        b"</body></html>"
    )

    assert is_index_document(raw_index, path="index.xhtml")

    chapter = parse_chapter(raw_index, path="index.xhtml")
    translations = {b.id: f"Traducao {b.text}" for b in chapter.blocks}
    rebuilt = rebuild_index_xhtml(raw_index, chapter.blocks, translations, target_lang="pt-BR")

    assert b"\xc3\x82\xc2\xa0" not in rebuilt
    decoded = rebuilt.decode("utf-8")
    assert "Â" not in decoded


def test_toc_nav_labels_without_meta_charset():
    raw_nav = (
        b'<html xmlns="http://www.w3.org/1999/xhtml">'
        b"<head><title>TOC</title></head>"
        b"<body>"
        b'<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc">'
        b"<ol>"
        b'<li><a href="ch1.xhtml">\xe2\x80\x9cCap\xc3\xadtulo 1\xe2\x80\x9d \xe2\x80\x93 Introdu\xc3\xa7\xc3\xa3o &nbsp;</a></li>'
        b"</ol>"
        b"</nav>"
        b"</body></html>"
    )

    labels = extract_nav_labels(raw_nav)
    assert len(labels) == 1
    assert "Â" not in labels[0]
    assert "“Capítulo 1” – Introdução" in labels[0]

    updated = apply_nav_labels(raw_nav, ["“Capítulo 1” — Introdução Traduzida"])
    assert b"\xc3\x82" not in updated
    decoded = updated.decode("utf-8")
    assert "“Capítulo 1” — Introdução Traduzida" in decoded
