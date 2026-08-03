"""Testes de segmentacao de capitulos (task 3.2)."""

import lxml.html
import pytest

from tests.epub import builders
from tradutor.epub.segments import parse_chapter, render_chapter


def test_parse_chapter_block_kinds():
    chapter = parse_chapter(builders.CH1.encode("utf-8"), path="ch1.xhtml")
    assert [block.kind for block in chapter.blocks] == [
        "titulo",
        "paragrafo",
        "paragrafo",
        "codigo",
        "paragrafo",
    ]
    assert chapter.path == "ch1.xhtml"
    assert chapter.title == "Chapter One"


def test_block_level_protected_pre():
    chapter = parse_chapter(builders.CH1.encode("utf-8"))
    pre = chapter.blocks[3]
    assert pre.protected is True
    assert pre.kind == "codigo"
    assert "def f()" in pre.text


def test_inline_code_becomes_placeholder():
    chapter = parse_chapter(builders.CH1.encode("utf-8"))
    paragraph = chapter.blocks[2]
    assert paragraph.protected is False
    assert "{{0}}" in paragraph.text
    assert "var x = 1;" not in paragraph.text


def test_placeholder_numbering_is_deterministic():
    source = builders.CH1.encode("utf-8")
    first = parse_chapter(source).blocks[2].text
    second = parse_chapter(source).blocks[2].text
    assert first == second


def test_render_applies_translation_and_restores_protected():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    paragraph = chapter.blocks[2]
    translations = {
        paragraph.id: "Codigo inline: {{0}} e {{1}}.",
    }
    out = render_chapter(source, chapter.blocks, translations).decode("utf-8")
    root = lxml.html.document_fromstring(out.encode("utf-8"))
    assert "Codigo inline:" in root.text_content()
    assert "<code>var x = 1;</code>" in out
    assert "<code>x + 1</code>" in out


def test_parse_keeps_text_and_child_tails_once():
    """Regressao: tails de filhos nao podem ser duplicados no bloco."""
    chapter = parse_chapter(builders.CH1.encode("utf-8"))
    assert chapter.blocks[1].text == "Hello <b>world</b>! This is the first paragraph."
    assert chapter.blocks[2].text == "Inline code: {{0}} and {{1}}."


def test_render_keeps_child_tails_once():
    """Regressao: restore de protegidos nao pode duplicar tails."""
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    paragraph = chapter.blocks[2]
    out = render_chapter(
        source, chapter.blocks, {paragraph.id: "Codigo inline: {{0}} e {{1}}."}
    ).decode("utf-8")
    assert out.count("<code>var x = 1;</code> e <code>x + 1</code>.") == 1
    assert out.count("x + 1</code>.") == 1


def test_render_keeps_formatting_markup():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    hello = chapter.blocks[1]
    out = render_chapter(source, chapter.blocks, {hello.id: "Ola <b>tudo</b> bem!"}).decode("utf-8")
    assert "<b>tudo</b>" in out
    assert "Ola " in out


def test_render_untouched_blocks_kept():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    heading = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {heading.id: "Capitulo Um"}).decode("utf-8")
    assert "Last line." in out


def test_render_empty_translation_keeps_original():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    heading = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {heading.id: "   "}).decode("utf-8")
    assert "Chapter One" in out


def test_render_plain_text_fallback():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    heading = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {heading.id: "100% & pronto"})
    root = lxml.html.document_fromstring(out)
    assert "100%" in root.text_content()


def test_render_keeps_doctype_and_xml_declaration():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    heading = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {heading.id: "Capitulo Um"})
    assert out.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
    assert b"<!DOCTYPE html>" in out


def test_render_block_count_mismatch_raises():
    source = builders.CH1.encode("utf-8")
    chapter = parse_chapter(source)
    with pytest.raises(ValueError):
        render_chapter(source, chapter.blocks[:-1], {})


def test_render_svg_and_math_protected(tmp_path):
    chapter = parse_chapter(SVG_MATH_XHTML.encode("utf-8"))
    assert [block.kind for block in chapter.blocks] == ["paragrafo", "grafico", "formula"]
    svg_block = chapter.blocks[1]
    math_block = chapter.blocks[2]
    assert svg_block.protected is True
    assert math_block.protected is True


def test_render_keeps_protected_blocks_intact():
    source = SVG_MATH_XHTML.encode("utf-8")
    chapter = parse_chapter(source)
    first = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {first.id: "Texto traduzido."}).decode("utf-8")
    assert "Texto traduzido." in out
    assert '<svg id="diagrama"' in out
    assert "<math>" in out


def test_loose_text_at_body_level_is_dropped():
    source = b"<html><body>texto solto<p>x</p></body></html>"
    chapter = parse_chapter(source)
    assert [block.kind for block in chapter.blocks] == ["paragrafo"]


def test_table_cells_become_blocks():
    source = b"<html><body><table><tr><td>a</td><td>b</td></tr></table></body></html>"
    chapter = parse_chapter(source)
    assert [block.kind for block in chapter.blocks] == ["celula_tabela", "celula_tabela"]
    assert [block.text for block in chapter.blocks] == ["a", "b"]


def test_comment_nodes_skipped():
    chapter = parse_chapter(b"<html><body><!-- nota --><p>x</p></body></html>")
    assert [block.kind for block in chapter.blocks] == ["paragrafo"]


def test_document_without_body():
    chapter = parse_chapter(b"<html><head><title>t</title></head></html>")
    assert chapter.blocks == []


def test_render_sibling_tails():
    source = b"<html><body><p>x</p></body></html>"
    chapter = parse_chapter(source)
    paragraph = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {paragraph.id: "um <b>dois</b> tres"})
    root = lxml.html.document_fromstring(out)
    paragraph_out = root.body[0]
    assert paragraph_out.text == "um "
    assert paragraph_out[0].text == "dois"
    assert paragraph_out[0].tail == " tres"


def test_replace_inner_empty_fragment_keeps_element():
    from tradutor.epub.segments import _replace_inner

    el = lxml.html.fromstring("<p>original</p>")
    _replace_inner(el, "")
    assert el.tag == "p"
    assert len(el) == 0
    assert el.text is None


def test_serialize_without_declaration_and_doctype():
    source = b"<html><body><p>x</p></body></html>"
    chapter = parse_chapter(source)
    paragraph = chapter.blocks[0]
    out = render_chapter(source, chapter.blocks, {paragraph.id: "y"})
    assert b"<?xml" not in out
    assert b"<!DOCTYPE" not in out
    assert b"<p>y</p>" in out


SVG_MATH_XHTML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<p>Texto com diagrama e formula abaixo.</p>
<svg id="diagrama" width="10" height="10"><circle cx="5" cy="5" r="4"/></svg>
<math><mi>x</mi><mo>=</mo><mn>1</mn></math>
</body>
</html>
"""
