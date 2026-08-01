"""Utilitarios compartilhados de serializacao XHTML.

O parser ``lxml.html`` nao re-emite o doctype nem a declaracao XML na
serializacao; este modulo re-anexa o prefixo original (normalizado) para
que capitulos tocados continuem sendo XHTML valido.
"""

from __future__ import annotations

import re

import lxml.html

_XML_DECL_RE = re.compile(rb"<\?xml[^>]*\?>", re.IGNORECASE)
_DOCTYPE_RE = re.compile(rb"<!DOCTYPE[^>]*>", re.IGNORECASE)


def serialize_xhtml(root: lxml.html.HtmlElement, source: bytes) -> bytes:
    """Serializa ``root`` em UTF-8, re-anexando declaracao XML e doctype.

    A declaracao XML e sempre re-emitida na forma padrao UTF-8 (o conteudo
    serializado ja e UTF-8); o doctype e copiado verbatim do original.
    """
    body = lxml.html.tostring(root, encoding="utf-8")
    prefix = b""
    if _XML_DECL_RE.search(source):
        prefix += b'<?xml version="1.0" encoding="utf-8"?>\n'
    doctype = _DOCTYPE_RE.search(source)
    if doctype:
        prefix += doctype.group(0) + b"\n"
    return prefix + body
