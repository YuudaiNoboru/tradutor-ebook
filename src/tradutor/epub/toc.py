"""Rotulos do sumario: nav.xhtml (EPUB 3) e toc.ncx (EPUB 2).

Extrai os rotulos em ordem de documento e os escreve de volta, sempre
mantendo os atributos (destinos dos links) intactos.
"""

from __future__ import annotations

from collections.abc import Sequence

import lxml.etree
import lxml.html

from tradutor.epub._xhtml import serialize_xhtml

NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"


def extract_nav_labels(source: bytes) -> list[str]:
    """Rotulos de todos os links do nav.xhtml, em ordem de documento."""
    root = lxml.html.document_fromstring(source)
    return [link.text_content() for link in root.iter("a")]


def apply_nav_labels(source: bytes, labels: Sequence[str]) -> bytes:
    """Substitui os rotulos dos links, preservando os atributos (href)."""
    root = lxml.html.document_fromstring(source)
    links = [link for link in root.iter("a")]
    _check_count(links, labels)
    for link, label in zip(links, labels, strict=True):
        for child in list(link):
            link.remove(child)
        link.text = label
    return serialize_xhtml(root, source)


def extract_ncx_labels(source: bytes) -> list[str]:
    """Rotulos dos ``navLabel`` do toc.ncx, em ordem de documento."""
    root = lxml.etree.fromstring(source)
    return [el.text or "" for el in _ncx_label_texts(root)]


def apply_ncx_labels(source: bytes, labels: Sequence[str]) -> bytes:
    """Substitui os rotulos dos ``navLabel``, preservando os atributos (src)."""
    root = lxml.etree.fromstring(source)
    texts = list(_ncx_label_texts(root))
    _check_count(texts, labels)
    for el, label in zip(texts, labels, strict=True):
        for child in list(el):
            el.remove(child)
        el.text = label
    return lxml.etree.tostring(root, xml_declaration=True, encoding="utf-8")


def _ncx_label_texts(root: lxml.etree._Element):
    label_tag = f"{{{NCX_NS}}}navLabel"
    text_tag = f"{{{NCX_NS}}}text"
    for el in root.iter(text_tag):
        parent = el.getparent()
        if parent is not None and parent.tag == label_tag:
            yield el


def _check_count(elements: list, labels: Sequence[str]) -> None:
    if len(elements) != len(labels):
        raise ValueError(
            f"sumario com {len(elements)} rotulos, mas {len(labels)} traducoes fornecidas"
        )
