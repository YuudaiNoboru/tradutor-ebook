"""Segmentacao de capitulos XHTML em blocos e reconstrucao cirurgica.

O parsing usa ``lxml.html`` (tolerante) e caminha os elementos de texto
em ordem de documento: cada "bloco de texto" vira um ``Block`` do dominio.
Elementos protegidos (code, pre, svg, math, script, style) nunca sao
enviados para traducao: em nivel de bloco viram ``Block(protected=True)``;
em nivel inline sao substituidos por placeholders ``{{N}}`` no texto do
bloco (ver ``tradutor.domain.placeholders``).

A reconstrucao (``render_chapter``) caminha o mesmo documento na mesma
ordem e substitui apenas o conteudo interno dos blocos traduzidos — a
estrutura do capitulo permanece identica e os arquivos nao traduzidos
sao copiados byte a byte pelo escritor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import lxml.html

from tradutor.domain import Block, Chapter
from tradutor.domain.placeholders import extract_protected, restore_protected
from tradutor.domain.protection import is_protected
from tradutor.epub._xhtml import serialize_xhtml

DEFAULT_KIND = "texto"

KIND_BY_TAG: dict[str, str] = {
    "p": "paragrafo",
    "h1": "titulo",
    "h2": "titulo",
    "h3": "titulo",
    "h4": "titulo",
    "h5": "titulo",
    "h6": "titulo",
    "li": "item_lista",
    "td": "celula_tabela",
    "th": "celula_tabela",
    "dt": "termo",
    "dd": "definicao",
    "blockquote": "citacao",
    "figcaption": "legenda",
    "caption": "legenda",
    "div": "divisao",
    "section": "secao",
    "article": "artigo",
    "aside": "nota",
    "header": "cabecalho",
    "footer": "rodape",
    "pre": "codigo",
    "code": "codigo",
    "script": "codigo",
    "style": "codigo",
    "svg": "grafico",
    "math": "formula",
}

BLOCK_LEVEL: frozenset[str] = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "td",
        "th",
        "dt",
        "dd",
        "figcaption",
        "caption",
        "pre",
        "div",
        "section",
        "article",
        "aside",
        "header",
        "footer",
        "figure",
        "table",
        "tr",
        "ul",
        "ol",
    }
)


def _is_leaf_block(el: lxml.html.HtmlElement) -> bool:
    if el.tag not in BLOCK_LEVEL:
        return False
    for child in el.iterdescendants():
        if isinstance(child.tag, str) and child.tag in BLOCK_LEVEL:
            return False
    return True


def _iter_block_elements(root: lxml.html.HtmlElement):
    """Gera ``(elemento, kind, protegido)`` em ordem de documento.

    A mesma caminhada e usada pelo parsing e pela reconstrucao, o que
    garante correspondencia 1:1 entre blocos e elementos.
    """
    body = root.body
    if body is None:
        body = root

    def walk(el: lxml.html.HtmlElement):
        if not isinstance(el.tag, str):
            return
        if is_protected(el.tag, el.attrib):
            yield (el, KIND_BY_TAG.get(el.tag, DEFAULT_KIND), True)
            return
        if _is_leaf_block(el):
            yield (el, KIND_BY_TAG.get(el.tag, DEFAULT_KIND), False)
            return
        for child in el:
            yield from walk(child)

    yield from walk(body)


def _inner_html(el: lxml.html.HtmlElement) -> str:
    """Serializa o conteudo interno (texto + filhos) do elemento."""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(lxml.html.tostring(child, encoding="unicode"))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _protected_contents(el: lxml.html.HtmlElement) -> list[str]:
    """Conteudos protegidos serializados, em ordem de documento."""
    return [
        lxml.html.tostring(child, encoding="unicode")
        for child in el.iterdescendants()
        if isinstance(child.tag, str) and is_protected(child.tag, child.attrib)
    ]


def parse_chapter(source: bytes, path: str = "") -> Chapter:
    """Converte um capitulo XHTML em uma lista de blocos do dominio.

    O texto de cada bloco e o conteudo interno serializado, com conteudos
    protegidos inline substituidos por placeholders ``{{N}}``. A numeracao
    de placeholders e deterministica (mesma entrada, mesmo resultado), o
    que permite reconstruir o mapeamento na hora de escrever de volta.
    """
    root = lxml.html.document_fromstring(source)
    blocks: list[Block] = []
    title = ""
    for index, (el, kind, protected) in enumerate(_iter_block_elements(root)):
        if protected:
            blocks.append(Block(id=index, kind=kind, text=_inner_html(el), protected=True))
        else:
            extracted = extract_protected(_inner_html(el), _protected_contents(el))
            blocks.append(Block(id=index, kind=kind, text=extracted.template))
        if not title and kind == "titulo":
            title = el.text_content().strip()
    return Chapter(blocks=blocks, path=path, title=title)


def render_chapter(
    source: bytes,
    blocks: Sequence[Block],
    translations: Mapping[int, str],
) -> bytes:
    """Aplica as traducoes ao capitulo e devolve o XHTML de saida.

    Elementos sem traducao permanecem intactos; conteudos protegidos sao
    restaurados dos placeholders verbatim.
    """
    root = lxml.html.document_fromstring(source)
    elements = [el for el, _, _ in _iter_block_elements(root)]
    if len(elements) != len(blocks):
        raise ValueError(
            f"capitulo {blocks[0].id if blocks else '?'}: numero de blocos divergiu"
            " entre parsing e escrita (capitulo alterado apos a leitura?)"
        )
    for block, el in zip(blocks, elements, strict=True):
        translated = translations.get(block.id)
        if translated is None or block.protected or not translated.strip():
            continue
        extracted = extract_protected(_inner_html(el), _protected_contents(el))
        final = restore_protected(translated, extracted.protected)
        _replace_inner(el, final)
    return serialize_xhtml(root, source)


def _replace_inner(el: lxml.html.HtmlElement, fragment: str) -> None:
    """Substitui o conteudo interno por um fragmento HTML traduzido.

    O parser HTML do lxml e tolerante e aceita qualquer fragmento; um
    fragmento vazio resulta em elemento sem conteudo.
    """
    nodes = lxml.html.fragments_fromstring(fragment)
    for child in list(el):
        el.remove(child)
    el.text = None
    for node in nodes:
        if isinstance(node, str):
            el.text = (el.text or "") + node
        else:
            el.append(node)
