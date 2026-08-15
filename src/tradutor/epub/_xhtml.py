"""Utilitarios compartilhados de serializacao XHTML.

O parser ``lxml.html`` nao re-emite o doctype nem a declaracao XML na
serializacao; este modulo re-anexa o prefixo original (normalizado) para
que capitulos tocados continuem sendo XHTML valido.
"""

from __future__ import annotations

import re
from typing import cast

import lxml.html

_XML_DECL_RE = re.compile(rb"<\?xml[^>]*\?>", re.IGNORECASE)
_DOCTYPE_RE = re.compile(rb"<!DOCTYPE[^>]*>", re.IGNORECASE)


def make_html_parser() -> lxml.html.HTMLParser:
    """Cria um parser HTML configurado para UTF-8 por padrao."""
    return lxml.html.HTMLParser(encoding="utf-8")


def parse_html_document(source: bytes | str) -> lxml.html.HtmlElement:
    """Parseia um documento HTML/XHTML forcando decodificacao UTF-8 por padrao."""
    return cast(
        lxml.html.HtmlElement, lxml.html.document_fromstring(source, parser=make_html_parser())
    )


def parse_html_fragments(fragment: str) -> list[lxml.html.HtmlElement | str]:
    """Parseia fragmentos HTML garantindo decodificacao UTF-8."""
    return cast(
        list[lxml.html.HtmlElement | str],
        lxml.html.fragments_fromstring(fragment, parser=make_html_parser()),
    )


def serialize_xhtml(root: lxml.html.HtmlElement, source: bytes) -> bytes:
    """Serializa ``root`` em UTF-8, re-anexando declaracao XML e doctype.

    A declaracao XML e sempre re-emitida na forma padrao UTF-8 (o conteudo
    serializado ja e UTF-8); o doctype e copiado verbatim do original.
    """
    body = cast(bytes, lxml.html.tostring(root, encoding="utf-8"))
    prefix = b""
    if _XML_DECL_RE.search(source):
        prefix += b'<?xml version="1.0" encoding="utf-8"?>\n'
    doctype = _DOCTYPE_RE.search(source)
    if doctype:
        prefix += doctype.group(0) + b"\n"
    return prefix + body
