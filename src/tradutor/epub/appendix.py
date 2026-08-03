"""Apendice de glossario no backmatter do livro de saida (tarefa 5.5).

Adiciona ao EPUB traduzido um capitulo final com as entradas
original -> traducao do glossario usado na traducao: gera o XHTML do
apendice, registra o item no manifest e o itemref no spine do OPF.
"""

from __future__ import annotations

from collections.abc import Sequence

from lxml import etree

from tradutor.epub.metadata import OPF_NS

APPENDIX_HREF = "apendice-glossario.xhtml"
APPENDIX_ITEM_ID = "apendice-glossario"
APPENDIX_TITLE = "Glossário"

XHTML_NS = "http://www.w3.org/1999/xhtml"


def _tag(local: str) -> str:
    return f"{{{XHTML_NS}}}{local}"


def build_appendix_xhtml(
    entries: Sequence[tuple[str, str]],
    *,
    title: str = APPENDIX_TITLE,
) -> bytes:
    """Devolve o XHTML do apendice: titulo + lista de definicoes."""
    html = etree.Element(_tag("html"), nsmap={None: XHTML_NS})
    head = etree.SubElement(html, _tag("head"))
    meta = etree.SubElement(head, _tag("meta"))
    meta.set("charset", "utf-8")
    title_el = etree.SubElement(head, _tag("title"))
    title_el.text = title
    body = etree.SubElement(html, _tag("body"))
    h1 = etree.SubElement(body, _tag("h1"))
    h1.text = title
    dl = etree.SubElement(body, _tag("dl"))
    for termo, traducao in entries:
        dt = etree.SubElement(dl, _tag("dt"))
        dt.text = termo
        dd = etree.SubElement(dl, _tag("dd"))
        dd.text = traducao
    return etree.tostring(html, xml_declaration=True, encoding="utf-8", pretty_print=True)


def add_appendix_to_opf(source: bytes, href: str = APPENDIX_HREF) -> bytes:
    """Registra o apendice no OPF: item no manifest + itemref no spine.

    O itemref e acrescentado ao fim do spine (backmatter). Levanta
    ``ValueError`` se o OPF nao tiver manifest/spine ou se o id ja
    existir no manifest.
    """
    root = etree.fromstring(source)
    manifest = root.find(f".//{{{OPF_NS}}}manifest")
    spine = root.find(f".//{{{OPF_NS}}}spine")
    if manifest is None or spine is None:
        raise ValueError("OPF sem manifest ou spine")
    existing = manifest.find(f".//{{{OPF_NS}}}item[@id='{APPENDIX_ITEM_ID}']")
    if existing is not None:
        raise ValueError(f"item duplicado no manifest: {APPENDIX_ITEM_ID}")
    item = etree.SubElement(manifest, f"{{{OPF_NS}}}item")
    item.set("id", APPENDIX_ITEM_ID)
    item.set("href", href)
    item.set("media-type", "application/xhtml+xml")
    itemref = etree.SubElement(spine, f"{{{OPF_NS}}}itemref")
    itemref.set("idref", APPENDIX_ITEM_ID)
    return etree.tostring(root, xml_declaration=True, encoding="utf-8")
