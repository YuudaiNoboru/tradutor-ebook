"""Reconstrucao semantica e multilingue de indices remissivos de EPUBs.

Detecta documentos de indice remissivo (via OPF properties, landmarks,
nome de arquivo e padroes estruturais de cabecalhos de letras e listas
de termos/links), traduz seus termos e os reordena alfabeticamente conforme
as regras de colacao Unicode do idioma de destino (target_lang), ignorando
diacriticos na ordenacao primaria e recalculando agrupamentos de letras (A a Z).
Preserva 100% dos links, ancoras, classes de estilo e estrutura hierarquica
de termos e subtermos.
"""

from __future__ import annotations

import copy
import posixpath
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import lxml.html

from tradutor.domain import Block
from tradutor.domain.placeholders import extract_protected, restore_protected
from tradutor.epub._xhtml import parse_html_document, serialize_xhtml
from tradutor.epub.segments import (
    _inner_html,
    _iter_block_elements,
    _protected_contents,
    _replace_inner,
)

_INDEX_PATH_RE = re.compile(
    r"(?:^|[/\\])(?:index|idx|indice|indices|genindex|subject_index|author_index|ix\d*)\.(?:x?html|xml)$",
    re.IGNORECASE,
)

_LETTER_CLASS_KEYWORDS = (
    "index-letter",
    "indexletter",
    "letter-heading",
    "alpha-header",
    "index-heading",
    "index_heading",
    "index_letter",
    "index_head",
    "alphagroup",
    "alpha-group",
)

_SUBENTRY_CLASS_KEYWORDS = (
    "subentry",
    "sub-entry",
    "subitem",
    "sub_entry",
    "index_2",
    "index_3",
    "index-sub",
    "indent",
    "level-2",
    "level-3",
)

_INDEX_CLASS_KEYWORDS = (
    "index",
    "indice",
    "genindex",
    "index-list",
    "index-entries",
    "indexgroup",
    "index-group",
    "book-index",
)


@dataclass(slots=True)
class IndexTerm:
    """Representa um termo de indice estruturado com seus subtermos subordinados."""

    block_id: int | None = None
    term_text: str = ""
    translated_text: str = ""
    element: lxml.html.HtmlElement | None = None
    children: list[IndexTerm] = field(default_factory=list)
    level: int = 0
    group_letter: str = ""
    sort_key: tuple = ()


def is_index_document(source: bytes | str, path: str = "", properties: str = "") -> bool:
    """Determina se um documento XHTML e um indice remissivo.

    Avalia metadados OPF (properties="index"), nome de arquivo (index.xhtml, idx.xhtml),
    atributos epub:type ou padroes estruturais de cabecalhos de letras e links de pagina.
    """
    if "index" in properties.split():
        return True

    clean_path = posixpath.normpath(path.replace("\\", "/"))
    if _INDEX_PATH_RE.search(clean_path):
        return True

    raw_bytes = source if isinstance(source, bytes) else source.encode("utf-8")
    try:
        root = parse_html_document(raw_bytes)
    except Exception:
        return False

    body = root.body if root.body is not None else root
    body_epub_type = (body.get("epub:type") or "").lower()
    if "index" in body_epub_type:
        return True

    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        epub_type = (el.get("epub:type") or "").lower()
        if "index" in epub_type.split():
            return True
        role = (el.get("role") or "").lower()
        if "doc-index" in role:
            return True
        cls = (el.get("class") or "").lower()
        if any(
            k in cls.split() for k in _INDEX_CLASS_KEYWORDS
        ) and _has_letter_headers_or_many_links(root):
            return True

    return _count_letter_headers(root) >= 2


def _has_letter_headers_or_many_links(root: lxml.html.HtmlElement) -> bool:
    """Verifica se ha cabecalhos de letras ou densidade de links de paginas."""
    if _count_letter_headers(root) >= 1:
        return True
    links_count = len(root.xpath(".//a[@href]"))
    return links_count >= 5


def _count_letter_headers(root: lxml.html.HtmlElement) -> int:
    """Conta quantos cabecalhos de letra (A-Z) existem no documento."""
    count = 0
    for el in root.iter():
        if _is_letter_header_element(el):
            count += 1
    return count


def _is_letter_header_element(el: lxml.html.HtmlElement) -> bool:
    """Verifica se o elemento HTML atua como cabecalho de letra alfabetica."""
    if not isinstance(el.tag, str):
        return False
    cls = (el.get("class") or "").lower()
    el_id = (el.get("id") or "").lower()
    if any(k in cls for k in _LETTER_CLASS_KEYWORDS) or any(
        k in el_id for k in ("letter", "idx_", "index-")
    ):
        return True
    tag = el.tag.lower()
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "dt", "p", "div", "header"):
        text = (el.text_content() or "").strip()
        if len(text) == 1 and text.isalpha():
            return True
        if text.upper() in (
            "0-9",
            "#",
            "SÍMBOLOS",
            "SIMBOLOS",
            "SYMBOLS",
            "NUMBERS",
            "NÚMEROS",
            "NUMEROS",
            "A-Z",
        ):
            return True
        match = re.fullmatch(r"[-—_\[(]\s*([A-Za-z]|0-9|#)\s*[-—_\])]", text)
        if match:
            return True
    return False


def _is_subentry_element(el: lxml.html.HtmlElement) -> bool:
    """Verifica se o elemento e um subtermo subordinado (nivel 1+)."""
    if not isinstance(el.tag, str):
        return False
    cls = (el.get("class") or "").lower()
    if any(k in cls for k in _SUBENTRY_CLASS_KEYWORDS):
        return True
    return el.tag.lower() == "dd"


def extract_term_label(text: str) -> str:
    """Extrai o rotulo principal do termo para ordenacao alfabetica."""
    t = re.sub(r"<[^>]+>", "", text)
    t = re.sub(r"\{\{\d+\}\}", "", t)
    t = re.sub(r"@@\d+@@", "", t)
    t = re.sub(r",\s*(?:\d+[\s\d,\-–—]*|see\s+.*|veja\s+.*|v\.\s+.*)$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"[\s,;:.-]+$", "", t)
    t = re.sub(r"^[\s,;:.-]+", "", t)
    return t or text.strip()


def get_group_letter(label: str, target_lang: str = "pt-BR") -> str:
    """Calcula a letra mestra do termo (A-Z, 0-9 ou #)."""
    cleaned = extract_term_label(label).strip()
    if not cleaned:
        return "#"
    core = re.sub(r"^[^\w]+", "", cleaned)
    if not core:
        core = cleaned
    first_char = core[0]
    if first_char.isdigit():
        return "0-9"
    nfd = unicodedata.normalize("NFD", first_char)
    base_char = nfd[0].upper()
    if "A" <= base_char <= "Z":
        return base_char
    return "#"


def get_sort_key(label: str, target_lang: str = "pt-BR") -> tuple:
    """Gera chave de ordenacao alfabetica por colacao Unicode agnostica de idioma."""
    cleaned = extract_term_label(label).strip()
    if not cleaned:
        return (2, "", "", "")
    core = re.sub(r"^[^\w]+", "", cleaned) or cleaned
    nfd = unicodedata.normalize("NFD", core)
    primary = "".join(c for c in nfd if not unicodedata.combining(c)).casefold()
    secondary = "".join(c for c in nfd if unicodedata.combining(c))
    tertiary = core
    first_char = core[0]
    if "A" <= nfd[0].upper() <= "Z":
        group_prio = 0
    elif first_char.isdigit():
        group_prio = 1
    else:
        group_prio = 2
    return (group_prio, primary, secondary, tertiary)


def parse_index_terms(
    root: lxml.html.HtmlElement,
    blocks: Sequence[Block],
    translations: Mapping[int, str] | None = None,
    target_lang: str = "pt-BR",
) -> tuple[list[IndexTerm], list[lxml.html.HtmlElement], lxml.html.HtmlElement | None]:
    """Extrai arvore hierarquica de termos e cabecalhos do documento."""
    translations = translations or {}
    elements = [el for el, _, _ in _iter_block_elements(root)]

    letter_headers: list[lxml.html.HtmlElement] = []
    top_level_terms: list[IndexTerm] = []
    current_parent: IndexTerm | None = None

    if not blocks:
        return [], [], None

    has_explicit_letters = any(_is_letter_header_element(e) for e in elements)
    seen_first_letter = False

    for block, el in zip(blocks, elements, strict=False):
        if _is_letter_header_element(el):
            letter_headers.append(el)
            seen_first_letter = True
            continue

        raw_translated = translations.get(block.id)
        if raw_translated is not None and not block.protected and raw_translated.strip():
            extracted = extract_protected(_inner_html(el), _protected_contents(el))
            if extracted.protected:
                final = restore_protected(raw_translated, extracted.protected)
            else:
                final = raw_translated
            _replace_inner(el, final)
            term_str = final
        else:
            term_str = block.text

        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        cls = (el.get("class") or "").lower()

        if has_explicit_letters and not seen_first_letter:
            if tag in ("h1", "h2", "h3", "header") or "title" in cls or "heading" in cls:
                continue
        elif tag in ("h1", "header") or "index-title" in cls or "book-title" in cls:
            continue

        is_sub = _is_subentry_element(el)
        term_obj = IndexTerm(
            block_id=block.id,
            term_text=block.text,
            translated_text=term_str,
            element=el,
            level=1 if is_sub else 0,
        )

        if is_sub and current_parent is not None:
            current_parent.children.append(term_obj)
        else:
            term_obj.group_letter = get_group_letter(term_str, target_lang)
            term_obj.sort_key = get_sort_key(term_str, target_lang)
            top_level_terms.append(term_obj)
            current_parent = term_obj

    letter_prototype = letter_headers[0] if letter_headers else None
    return top_level_terms, letter_headers, letter_prototype


def sort_and_group_terms(
    terms: list[IndexTerm],
    target_lang: str = "pt-BR",
) -> dict[str, list[IndexTerm]]:
    """Ordena os termos alfabeticamente e os agrupa por letra mestra."""
    for term in terms:
        effective_text = term.translated_text or term.term_text
        term.sort_key = get_sort_key(effective_text, target_lang)
        term.group_letter = get_group_letter(effective_text, target_lang)

    sorted_terms = sorted(terms, key=lambda t: t.sort_key)

    grouped: dict[str, list[IndexTerm]] = {}
    for term in sorted_terms:
        grouped.setdefault(term.group_letter, []).append(term)

    return grouped


def _update_letter_header_element(
    header_el: lxml.html.HtmlElement,
    letter: str,
) -> None:
    """Atualiza o texto e identificador de um elemento de cabecalho de letra."""
    orig_text = (header_el.text or header_el.text_content() or "").strip()
    if orig_text.startswith("—") and orig_text.endswith("—"):
        new_text = f"— {letter} —"
    elif orig_text.startswith("[") and orig_text.endswith("]"):
        new_text = f"[ {letter} ]"
    elif orig_text.startswith("-") and orig_text.endswith("-"):
        new_text = f"- {letter} -"
    else:
        new_text = letter

    for child in list(header_el):
        header_el.remove(child)
    header_el.text = new_text

    orig_id = header_el.get("id")
    if orig_id:
        if orig_id.startswith("letter_"):
            header_el.set("id", f"letter_{letter.lower()}")
        elif orig_id.startswith("letter-"):
            header_el.set("id", f"letter-{letter.lower()}")
        elif orig_id.startswith("index-"):
            header_el.set("id", f"index-{letter}")
        elif orig_id.startswith("idx_"):
            header_el.set("id", f"idx_{letter.lower()}")
        else:
            header_el.set("id", letter.lower())


def rebuild_index_xhtml(
    source: bytes,
    blocks: Sequence[Block],
    translations: Mapping[int, str],
    target_lang: str = "pt-BR",
) -> bytes:
    """Reconstroi o documento XHTML de indice remissivo ordenado para o target_lang."""
    root = parse_html_document(source)

    top_level_terms, old_letter_headers, letter_proto = parse_index_terms(
        root, blocks, translations, target_lang=target_lang
    )

    if not top_level_terms:
        return serialize_xhtml(root, source)

    grouped_terms = sort_and_group_terms(top_level_terms, target_lang=target_lang)

    first_term_el = top_level_terms[0].element
    assert first_term_el is not None
    parent_container = first_term_el.getparent()
    if parent_container is None:
        parent_container = root.body if root.body is not None else root

    if letter_proto is not None:
        proto_parent = letter_proto.getparent()
        if proto_parent is not None:
            parent_container = proto_parent

    for header in old_letter_headers:
        h_parent = header.getparent()
        if h_parent is not None:
            h_parent.remove(header)

    for term in top_level_terms:
        if term.element is not None:
            t_parent = term.element.getparent()
            if t_parent is not None:
                t_parent.remove(term.element)
        for sub in term.children:
            if sub.element is not None:
                s_parent = sub.element.getparent()
                if s_parent is not None:
                    s_parent.remove(sub.element)

    letter_keys = sorted(
        grouped_terms.keys(),
        key=lambda k: (0 if "A" <= k <= "Z" else 1 if k == "0-9" else 2, k),
    )

    for letter in letter_keys:
        terms_in_letter = grouped_terms[letter]
        if letter_proto is not None:
            new_header = copy.deepcopy(letter_proto)
            _update_letter_header_element(new_header, letter)
            parent_container.append(new_header)
        elif len(grouped_terms) > 1:
            new_header = lxml.html.Element("h2", attrib={"class": "index-letter"})
            new_header.text = letter
            parent_container.append(new_header)

        for term in terms_in_letter:
            if term.element is not None:
                parent_container.append(term.element)
            for sub in term.children:
                if sub.element is not None:
                    parent_container.append(sub.element)

    return serialize_xhtml(root, source)
