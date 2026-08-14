"""Testes unitarios e de integracao para o index_rebuilder (tarefas 3.1 a 3.5)."""

from __future__ import annotations

import zipfile

import lxml.html

from tests.epub import builders
from tradutor.epub.container import open_ebook
from tradutor.epub.index_rebuilder import (
    IndexTerm,
    extract_term_label,
    get_group_letter,
    get_sort_key,
    is_index_document,
    rebuild_index_xhtml,
    sort_and_group_terms,
)
from tradutor.epub.segments import parse_chapter
from tradutor.epub.writer import write_translated


def test_is_index_document_by_property():
    assert is_index_document(b"<html/>", properties="index")
    assert is_index_document(b"<html/>", properties="nav index")


def test_is_index_document_by_path():
    assert is_index_document(b"<html/>", path="OEBPS/index.xhtml")
    assert is_index_document(b"<html/>", path="OEBPS/idx.xhtml")
    assert is_index_document(b"<html/>", path="OEBPS/indice.html")
    assert is_index_document(b"<html/>", path="OEBPS/ix01.xhtml")
    assert not is_index_document(b"<html/>", path="OEBPS/chapter01.xhtml")


def test_is_index_document_by_content_and_headers():
    doc = b"""<?xml version="1.0" encoding="utf-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <h2>A</h2>
        <p class="index-entry">Agile, <a href="ch1.xhtml#p1">1</a></p>
        <h2>B</h2>
        <p class="index-entry">Bounded Context, <a href="ch2.xhtml#p2">2</a></p>
    </body>
    </html>"""
    assert is_index_document(doc, path="OEBPS/backmatter.xhtml")


def test_is_index_document_by_epub_type_or_role():
    doc1 = b"""<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
    <body epub:type="index"><p>Some text</p></body></html>"""
    assert is_index_document(doc1)

    doc2 = b"""<html><body role="doc-index"><p>Some text</p></body></html>"""
    assert is_index_document(doc2)


def test_extract_term_label():
    assert extract_term_label("Architectural styles, {{0}}, {{1}}") == "Architectural styles"
    assert extract_term_label("Contexto Delimitado, {{0}}") == "Contexto Delimitado"
    assert extract_term_label("Ágil, 10, 25-30") == "Ágil"
    assert extract_term_label("Domain-Driven Design, see DDD") == "Domain-Driven Design"
    assert extract_term_label("<b>Arquitetura</b>") == "Arquitetura"


def test_get_group_letter():
    assert get_group_letter("Contexto Delimitado") == "C"
    assert get_group_letter("Ágil") == "A"
    assert get_group_letter("Épico") == "E"
    assert get_group_letter("Índice") == "I"
    assert get_group_letter("Ópera") == "O"
    assert get_group_letter("Último") == "U"
    assert get_group_letter("Ção") == "C"
    assert get_group_letter("12-Factor App") == "0-9"
    assert get_group_letter('"Design Patterns"') == "D"
    assert get_group_letter("") == "#"


def test_get_sort_key_alphabetical_collation():
    terms = [
        "Arquitetura",
        "Ágil",
        "Agilidade",
        "Abstrato",
        "Contexto Delimitado",
        "12-Factor App",
    ]
    sorted_terms = sorted(terms, key=lambda t: get_sort_key(t, "pt-BR"))
    assert sorted_terms == [
        "Abstrato",
        "Ágil",
        "Agilidade",
        "Arquitetura",
        "Contexto Delimitado",
        "12-Factor App",
    ]


def test_sort_and_group_terms():
    terms = [
        IndexTerm(block_id=1, term_text="Bounded Context", translated_text="Contexto Delimitado"),
        IndexTerm(block_id=2, term_text="Architecture", translated_text="Arquitetura"),
        IndexTerm(block_id=3, term_text="Agile", translated_text="Ágil"),
    ]
    grouped = sort_and_group_terms(terms, target_lang="pt-BR")
    assert list(grouped.keys()) == ["A", "C"]
    assert [t.translated_text for t in grouped["A"]] == ["Ágil", "Arquitetura"]
    assert [t.translated_text for t in grouped["C"]] == ["Contexto Delimitado"]


def test_rebuild_index_xhtml_flat_structure():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Index</title></head>
<body>
    <h1>Index</h1>
    <div class="index">
        <h2 class="index-letter" id="letter_a">A</h2>
        <p class="index-entry">Architectural styles, <a href="ch01.xhtml#p10">10</a>, <a href="ch02.xhtml#p25">25</a></p>
        <p class="index-entry">Asynchronous messaging, <a href="ch04.xhtml#p60">60</a></p>
        <h2 class="index-letter" id="letter_b">B</h2>
        <p class="index-entry">Bounded Context, <a href="ch05.xhtml#p80">80</a></p>
        <p class="index-subentry">definition, <a href="ch05.xhtml#p81">81</a></p>
        <p class="index-subentry">mapping, <a href="ch05.xhtml#p85">85</a></p>
        <h2 class="index-letter" id="letter_c">C</h2>
        <p class="index-entry">Coupling, <a href="ch03.xhtml#p30">30</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")

    translations = {
        0: "Índice",
        # block 1: "A"
        2: 'Estilos arquitetônicos, <a href="ch01.xhtml#p10">10</a>, <a href="ch02.xhtml#p25">25</a>',
        3: 'Mensageria assíncrona, <a href="ch04.xhtml#p60">60</a>',
        # block 4: "B"
        5: 'Contexto Delimitado, <a href="ch05.xhtml#p80">80</a>',
        6: 'definição, <a href="ch05.xhtml#p81">81</a>',
        7: 'mapeamento, <a href="ch05.xhtml#p85">85</a>',
        # block 8: "C"
        9: 'Acoplamento, <a href="ch03.xhtml#p30">30</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")

    root = lxml.html.document_fromstring(result)
    assert root.findtext(".//h1") == "Índice"

    letters = [el.text_content().strip() for el in root.xpath(".//h2[@class='index-letter']")]
    assert letters == ["A", "C", "E", "M"]

    entries = [el.text_content().strip() for el in root.xpath(".//p")]
    assert entries[0] == "Acoplamento, 30"
    assert entries[1] == "Contexto Delimitado, 80"
    assert entries[2] == "definição, 81"
    assert entries[3] == "mapeamento, 85"
    assert entries[4] == "Estilos arquitetônicos, 10, 25"
    assert entries[5] == "Mensageria assíncrona, 60"

    links = root.xpath(".//a/@href")
    assert links == [
        "ch03.xhtml#p30",
        "ch05.xhtml#p80",
        "ch05.xhtml#p81",
        "ch05.xhtml#p85",
        "ch01.xhtml#p10",
        "ch02.xhtml#p25",
        "ch04.xhtml#p60",
    ]


def test_rebuild_index_xhtml_with_letter_decorators():
    source = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <h3 class="index-heading" id="index-A">— A —</h3>
        <p class="index_1">Big Data, <a href="c1.xhtml#p1">1</a></p>
    </div>
</body>
</html>""".encode()

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "— A —",
        1: 'Grandes Volumes de Dados (Big Data), <a href="c1.xhtml#p1">1</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    heading = root.xpath(".//h3")[0]
    assert heading.text_content().strip() == "— G —"
    assert heading.get("id") == "index-G"


def test_rebuild_index_empty_terms():
    source = b"<html><body><div></div></body></html>"
    res = rebuild_index_xhtml(source, [], {})
    assert b"<html>" in res


def test_integration_write_translated_with_index(tmp_path):
    index_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Index</title></head>
<body>
    <h1>Index</h1>
    <div class="index">
        <h2 class="index-letter" id="letter_a">A</h2>
        <p class="index-entry">Architecture, <a href="ch1.xhtml#p1">1</a></p>
        <h2 class="index-letter" id="letter_b">B</h2>
        <p class="index-entry">Bounded Context, <a href="ch1.xhtml#p2">2</a></p>
    </div>
</body>
</html>"""

    ch1_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
    <h1>Chapter 1</h1>
    <p id="p1">Software Architecture concepts.</p>
    <p id="p2">Bounded Context in Domain-Driven Design.</p>
</body>
</html>"""

    container_xml = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:test-index</dc:identifier>
    <dc:title>Test Index Book</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ch1" href="text/ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="idx" href="text/index.xhtml" media-type="application/xhtml+xml" properties="index"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="idx"/>
  </spine>
</package>
"""
    epub_bytes = builders._build(
        [
            ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
            ("META-INF/container.xml", container_xml.encode("utf-8")),
            ("OEBPS/content.opf", opf.encode("utf-8")),
            ("OEBPS/text/ch1.xhtml", ch1_xhtml.encode("utf-8")),
            ("OEBPS/text/index.xhtml", index_xhtml.encode("utf-8")),
        ]
    )
    epub_path = tmp_path / "book.epub"
    epub_path.write_bytes(epub_bytes)

    ebook = open_ebook(epub_path)
    assert len(ebook.chapters) == 2

    # Map translations
    # ch1 has blocks: 0 (Chapter 1), 1 (p1), 2 (p2)
    # index has blocks: 3 (Index), 4 (A), 5 (Architecture, 1), 6 (B), 7 (Bounded Context, 2)
    translations = {
        0: "Capítulo 1",
        1: "Conceitos de Arquitetura de Software.",
        2: "Contexto Delimitado em Domain-Driven Design.",
        3: "Índice Remissivo",
        5: 'Arquitetura, <a href="ch1.xhtml#p1">1</a>',
        7: 'Contexto Delimitado, <a href="ch1.xhtml#p2">2</a>',
    }

    out_path = tmp_path / "book-pt-BR.epub"
    write_translated(
        ebook,
        out_path,
        translations=translations,
        target_lang="pt-BR",
        translated_title="Livro Traduzido",
    )

    translated_ebook = open_ebook(out_path)
    index_chapter = [c for c in translated_ebook.chapters if c.path.endswith("index.xhtml")][0]
    index_source = translated_ebook._sources[index_chapter.path]
    root = lxml.html.document_fromstring(index_source)

    letters = [el.text_content().strip() for el in root.xpath(".//h2[@class='index-letter']")]
    assert letters == ["A", "C"]

    entries = [el.text_content().strip() for el in root.xpath(".//p")]
    assert entries[0] == "Arquitetura, 1"
    assert entries[1] == "Contexto Delimitado, 2"


def test_rebuild_index_with_placeholders_and_anchors():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <h2 class="index-letter">A</h2>
        <p class="index-entry"><a id="term_arch"/>Architecture, <a href="c1.xhtml#p1">1</a></p>
        <h2 class="index-letter">B</h2>
        <p class="index-entry"><span id="term_bc"/>Bounded Context, <a href="c2.xhtml#p2">2</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "A",
        1: '{{0}}Arquitetura, <a href="c1.xhtml#p1">1</a>',
        2: "B",
        3: '{{0}}Contexto Delimitado, <a href="c2.xhtml#p2">2</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    assert root.xpath(".//p[1]/a[@id='term_arch']")
    assert root.xpath(".//p[2]/span[@id='term_bc']")


def test_rebuild_index_multilevel_subterms():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <h2 class="index-letter">B</h2>
        <p class="index-entry">Bounded Context</p>
        <p class="index_2">definition, <a href="c1.xhtml#p1">1</a></p>
        <p class="index_3">sub-item, <a href="c1.xhtml#p2">2</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "B",
        1: "Contexto Delimitado",
        2: 'definição, <a href="c1.xhtml#p1">1</a>',
        3: 'subitem, <a href="c1.xhtml#p2">2</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    assert root.xpath(".//h2[@class='index-letter']")[0].text_content().strip() == "C"
    p_texts = [el.text_content().strip() for el in root.xpath(".//p")]
    assert p_texts == ["Contexto Delimitado", "definição, 1", "subitem, 2"]


def test_rebuild_index_number_and_symbol_grouping():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <h2 class="index-letter">#</h2>
        <p class="index-entry">12-Factor App, <a href="c1.xhtml#p1">1</a></p>
        <p class="index-entry">3-Tier Architecture, <a href="c1.xhtml#p2">2</a></p>
        <p class="index-entry">.NET Framework, <a href="c1.xhtml#p3">3</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "#",
        1: '12-Factor App, <a href="c1.xhtml#p1">1</a>',
        2: 'Arquitetura de 3 Camadas (3-Tier), <a href="c1.xhtml#p2">2</a>',
        3: '.NET Framework, <a href="c1.xhtml#p3">3</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    letters = [el.text_content().strip() for el in root.xpath(".//h2[@class='index-letter']")]
    assert "A" in letters
    assert "0-9" in letters or "#" in letters


def test_collation_various_languages():
    terms_es = ["Árbol", "Avión", "Barco", "Zapato"]
    sorted_es = sorted(terms_es, key=lambda t: get_sort_key(t, "es"))
    assert sorted_es == ["Árbol", "Avión", "Barco", "Zapato"]

    terms_fr = ["Éléphant", "Eau", "École", "Zèbre"]
    sorted_fr = sorted(terms_fr, key=lambda t: get_sort_key(t, "fr"))
    assert sorted_fr == ["Eau", "École", "Éléphant", "Zèbre"]


def test_letter_header_bracket_and_dash_styles():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <h2 class="index-letter">[ A ]</h2>
        <p class="index-entry">Bounded Context, <a href="c1.xhtml#p1">1</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "[ A ]",
        1: 'Contexto Delimitado, <a href="c1.xhtml#p1">1</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    header = root.xpath(".//h2")[0]
    assert header.text_content().strip() == "[ C ]"


def test_is_index_document_edge_cases():
    assert not is_index_document(b"")
    assert not is_index_document(b"<<not xml>>")

    # section with epub:type="index"
    doc_section = (
        b"""<html><body><section epub:type="index"><p>Content</p></section></body></html>"""
    )
    assert is_index_document(doc_section)

    # class index with >= 5 links
    doc_links = b"""<html><body><div class="index">
        <a href="1.xhtml">1</a>
        <a href="2.xhtml">2</a>
        <a href="3.xhtml">3</a>
        <a href="4.xhtml">4</a>
        <a href="5.xhtml">5</a>
    </div></body></html>"""
    assert is_index_document(doc_links)


def test_update_letter_header_element_various_ids_and_styles():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <h2 id="idx_a">- A -<span>icon</span></h2>
        <p class="index-entry">Architecture, <a href="c1.xhtml#p1">1</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "- A -",
        1: 'Contexto Delimitado, <a href="c1.xhtml#p1">1</a>',
    }
    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    header = root.xpath(".//h2")[0]
    assert header.text_content().strip() == "- C -"
    assert header.get("id") == "idx_c"


def test_rebuild_index_without_explicit_letter_headers():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div class="index">
        <p class="index-entry">Architecture, <a href="c1.xhtml#p1">1</a></p>
        <p class="index-entry">Bounded Context, <a href="c2.xhtml#p2">2</a></p>
        <p class="index-entry">Coupling, <a href="c3.xhtml#p3">3</a></p>
    </div>
</body>
</html>"""

    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: 'Arquitetura, <a href="c1.xhtml#p1">1</a>',
        1: 'Contexto Delimitado, <a href="c2.xhtml#p2">2</a>',
        2: 'Acoplamento, <a href="c3.xhtml#p3">3</a>',
    }

    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    letters = [el.text_content().strip() for el in root.xpath(".//h2[@class='index-letter']")]
    assert letters == ["A", "C"]
    entries = [el.text_content().strip() for el in root.xpath(".//p")]
    assert entries[0] == "Acoplamento, 3"
    assert entries[1] == "Arquitetura, 1"
    assert entries[2] == "Contexto Delimitado, 2"


def test_get_group_letter_symbols_and_numbers():
    assert get_group_letter("@decorator") == "D"
    assert get_group_letter("___") == "#"
    assert get_group_letter("99 Bottles") == "0-9"
    assert get_group_letter("###") == "#"


def test_get_sort_key_empty_and_special():
    assert get_sort_key("") == (2, "", "", "")
    assert get_sort_key("   ") == (2, "", "", "")
    prio, prim, _, _ = get_sort_key("123 Test")
    assert prio == 1
    assert prim == "123 test"
    prio_sym, prim_sym, _, _ = get_sort_key("!!!")
    assert prio_sym == 2


def test_header_id_variants():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <div>
        <h2 id="letter-a">A</h2>
        <p class="index-entry">Apple, <a href="c1.xhtml#p1">1</a></p>
        <h2 id="letter-b">B</h2>
        <p class="index-entry">Banana, <a href="c2.xhtml#p2">2</a></p>
        <h2 id="letter-c">C</h2>
        <p class="index-entry">Cat, <a href="c3.xhtml#p3">3</a></p>
    </div>
</body>
</html>"""
    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "A",
        1: 'Abacaxi, <a href="c1.xhtml#p1">1</a>',
        2: "B",
        3: 'Banana, <a href="c2.xhtml#p2">2</a>',
        4: "C",
        5: 'Gato, <a href="c3.xhtml#p3">3</a>',
    }
    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    headers = root.xpath(".//h2")
    assert len(headers) == 3
    assert headers[0].get("id") == "letter-a"
    assert headers[1].get("id") == "letter-b"
    assert headers[2].get("id") == "letter-g"


def test_update_letter_header_element_prefixes():
    from tradutor.epub.index_rebuilder import _update_letter_header_element

    el1 = lxml.html.fromstring('<h2 id="index-A">A</h2>')
    _update_letter_header_element(el1, "B")
    assert el1.get("id") == "index-B"

    el2 = lxml.html.fromstring('<h2 id="idx_a">A</h2>')
    _update_letter_header_element(el2, "B")
    assert el2.get("id") == "idx_b"

    el3 = lxml.html.fromstring('<h2 id="custom">A</h2>')
    _update_letter_header_element(el3, "B")
    assert el3.get("id") == "b"


def test_rebuild_index_dl_dt_dd():
    source = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <h1 class="index-title">Index</h1>
    <dl class="index">
        <dt class="letter-heading" id="letter_a">A</dt>
        <dt>Algorithm, <a href="c1.xhtml#p1">1</a></dt>
        <dd>sorting, <a href="c1.xhtml#p2">2</a></dd>
        <dt class="letter-heading" id="letter_b">B</dt>
        <dt>Binary Search, <a href="c2.xhtml#p1">3</a></dt>
    </dl>
</body>
</html>"""
    chapter_obj = parse_chapter(source, path="index.xhtml")
    translations = {
        0: "Índice",
        1: "A",
        2: 'Algoritmo, <a href="c1.xhtml#p1">1</a>',
        3: 'ordenação, <a href="c1.xhtml#p2">2</a>',
        4: "B",
        5: 'Busca Binária, <a href="c2.xhtml#p1">3</a>',
    }
    result = rebuild_index_xhtml(source, chapter_obj.blocks, translations, target_lang="pt-BR")
    root = lxml.html.document_fromstring(result)
    dts = [el.text_content().strip() for el in root.xpath(".//dt")]
    assert "A" in dts
    assert "B" in dts
    assert "Algoritmo, 1" in dts
    assert "Busca Binária, 3" in dts


def test_rebuild_index_empty_blocks():
    source = b"<html><body></body></html>"
    result = rebuild_index_xhtml(source, [], {})
    assert b"<html>" in result


def test_letter_headers_special_names():
    doc = b"""<html><body>
    <h2>0-9</h2><p>123</p>
    <h2>#</h2><p>Special</p>
    <h2>SYMBOLS</h2><p>Symbols</p>
    </body></html>"""
    assert is_index_document(doc)
