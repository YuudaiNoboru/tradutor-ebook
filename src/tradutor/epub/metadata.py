"""Atualizacao de metadados do OPF (dc:language, dc:title, dc:date).

Manifest e spine nunca sao tocados; apenas os nos de metadados sao
alterados (ou criados quando ausentes).
"""

from __future__ import annotations

from lxml import etree

OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"


def update_metadata(
    source: bytes,
    *,
    language: str | None = None,
    title: str | None = None,
    modified: str | None = None,
) -> bytes:
    """Devolve o OPF com os metadados solicitados atualizados.

    ``modified`` preenche ``dc:date`` e o meta ``dcterms:modified``
    (obrigatorio em EPUB 3), criando-os quando ausentes.
    """
    root = etree.fromstring(source)
    metadata = root.find(f".//{{{OPF_NS}}}metadata")
    if metadata is None:
        raise ValueError("OPF sem elemento metadata")
    if language is not None:
        _set_or_create(metadata, f"{{{DC_NS}}}language", language)
    if title is not None:
        _set_or_create(metadata, f"{{{DC_NS}}}title", title)
    if modified is not None:
        _set_or_create(metadata, f"{{{DC_NS}}}date", modified)
        meta = _find_meta(metadata, "dcterms:modified")
        if meta is None:
            meta = etree.SubElement(metadata, f"{{{OPF_NS}}}meta")
            meta.set("property", "dcterms:modified")
        meta.text = modified
    return etree.tostring(root, xml_declaration=True, encoding="utf-8")


def _set_or_create(metadata: etree._Element, tag: str, value: str) -> None:
    el = metadata.find(tag)
    if el is None:
        el = etree.SubElement(metadata, tag)
    el.text = value


def _find_meta(metadata: etree._Element, property_name: str) -> etree._Element | None:
    for el in metadata.findall(f"{{{OPF_NS}}}meta"):
        if el.get("property") == property_name:
            return el
    return None
