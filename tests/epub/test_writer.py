"""Testes do escritor: byte-diff dourado, mimetype, metadados, sumario
(tasks 3.3, 3.4, 3.5 e 3.8)."""

import zipfile

import lxml.html
import pytest
from lxml import etree

from tests.epub import builders
from tradutor.epub import MalformedEpubError, open_ebook, write_translated
from tradutor.epub.metadata import DC_NS, OPF_NS, update_metadata
from tradutor.epub.toc import (
    apply_nav_labels,
    apply_ncx_labels,
    extract_nav_labels,
    extract_ncx_labels,
)
from tradutor.epub.writer import write_zip

NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"


@pytest.fixture
def epub2_path(tmp_path):
    path = tmp_path / "book.epub"
    path.write_bytes(builders.build_epub2())
    return path


@pytest.fixture
def epub3_path(tmp_path):
    path = tmp_path / "book3.epub"
    path.write_bytes(builders.build_epub3())
    return path


@pytest.mark.parametrize("builder", [builders.build_epub2, builders.build_epub3])
def test_untouched_roundtrip_byte_identical(tmp_path, builder):
    path = tmp_path / "in.epub"
    path.write_bytes(builder())
    out = tmp_path / "out.epub"
    ebook = open_ebook(path)
    write_translated(ebook, out, translations={})
    assert out.read_bytes() == builder()


@pytest.mark.parametrize("builder", [builders.build_epub2, builders.build_epub3])
def test_untouched_entries_identical_after_translation(tmp_path, builder):
    path = tmp_path / "in.epub"
    path.write_bytes(builder())
    out = tmp_path / "out.epub"
    ebook = open_ebook(path)
    first = ebook.chapters[0].blocks[0]
    write_translated(ebook, out, translations={first.id: "Capitulo Um"})
    with zipfile.ZipFile(out) as zf, zipfile.ZipFile(path) as zf_orig:
        for name in zf.namelist():
            if name == "OEBPS/text/ch1.xhtml":
                assert zf.read(name) != zf_orig.read(name)
            else:
                assert zf.read(name) == zf_orig.read(name)


def test_touched_chapter_differs_only_in_text(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    blocks = ebook.chapters[0].blocks
    translations = {
        blocks[0].id: "Capitulo Um",
        blocks[1].id: "Ola <b>mundo</b>! Este e o primeiro paragrafo.",
        blocks[2].id: "Codigo inline: {{0}} e {{1}}.",
        blocks[4].id: "Ultima linha.",
    }
    write_translated(ebook, out, translations=translations)

    original = ebook._sources["OEBPS/text/ch1.xhtml"]
    with zipfile.ZipFile(out) as zf:
        translated = zf.read("OEBPS/text/ch1.xhtml")

    orig_root = lxml.html.document_fromstring(original)
    new_root = lxml.html.document_fromstring(translated)
    assert skeleton(orig_root) == skeleton(new_root)
    body = new_root.body
    text = body.text_content() if body is not None else new_root.text_content()
    assert "Capitulo Um" in text
    assert "Ultima linha." in text
    assert "var x = 1;" in translated.decode("utf-8")
    assert "Chapter One" not in text
    assert "Hello" not in text


def test_mimetype_first_and_stored(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    first = ebook.chapters[0].blocks[0]
    write_translated(ebook, out, translations={first.id: "Capitulo Um"})
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert names[0] == "mimetype"
        info = zf.getinfo("mimetype")
        assert info.compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"
        assert names == [entry.filename for entry in zipfile.ZipFile(epub2_path).infolist()]


def test_metadata_updated_epub2(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    write_translated(
        ebook,
        out,
        target_lang="pt-BR",
        translated_title="O Livro Ingles",
        modified="2024-05-01T10:00:00Z",
    )
    with zipfile.ZipFile(out) as zf:
        opf = etree.fromstring(zf.read("OEBPS/content.opf"))
    metadata = opf.find(f".//{{{OPF_NS}}}metadata")
    assert metadata.findtext(f"{{{DC_NS}}}language") == "pt-BR"
    assert metadata.findtext(f"{{{DC_NS}}}title") == "O Livro Ingles"
    assert metadata.findtext(f"{{{DC_NS}}}date") == "2024-05-01T10:00:00Z"
    meta = [
        m for m in metadata.findall(f"{{{OPF_NS}}}meta") if m.get("property") == "dcterms:modified"
    ]
    assert meta and meta[0].text == "2024-05-01T10:00:00Z"


def test_metadata_updated_epub3(tmp_path, epub3_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub3_path)
    write_translated(ebook, out, target_lang="pt-BR", modified="2024-05-01T10:00:00Z")
    with zipfile.ZipFile(out) as zf:
        opf = etree.fromstring(zf.read("OEBPS/content.opf"))
    metadata = opf.find(f".//{{{OPF_NS}}}metadata")
    assert metadata.findtext(f"{{{DC_NS}}}language") == "pt-BR"
    meta = [
        m for m in metadata.findall(f"{{{OPF_NS}}}meta") if m.get("property") == "dcterms:modified"
    ]
    assert meta[0].text == "2024-05-01T10:00:00Z"


def test_manifest_and_spine_intact(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    first = ebook.chapters[0].blocks[0]
    write_translated(ebook, out, translations={first.id: "Capitulo Um"}, target_lang="pt-BR")
    with zipfile.ZipFile(out) as zf:
        opf = etree.fromstring(zf.read("OEBPS/content.opf"))
        opf_orig = etree.fromstring(ebook._sources["OEBPS/content.opf"])
    manifest_items = [
        (el.get("id"), el.get("href"), el.get("media-type"))
        for el in opf.findall(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item")
    ]
    manifest_orig = [
        (el.get("id"), el.get("href"), el.get("media-type"))
        for el in opf_orig.findall(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item")
    ]
    spine = [el.get("idref") for el in opf.findall(f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref")]
    spine_orig = [
        el.get("idref") for el in opf_orig.findall(f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref")
    ]
    assert manifest_items == manifest_orig
    assert spine == spine_orig


def test_toc_nav_labels_extract_and_apply(tmp_path, epub3_path):
    ebook = open_ebook(epub3_path)
    assert ebook.toc_labels == ["Chapter One", "Chapter Two"]
    out = tmp_path / "out.epub"
    write_translated(ebook, out, toc_labels=["Capitulo Um", "Capitulo Dois"])
    with zipfile.ZipFile(out) as zf:
        nav = zf.read("OEBPS/nav.xhtml")
    root = lxml.html.document_fromstring(nav)
    links = [(a.text_content(), a.get("href")) for a in root.iter("a")]
    assert links == [
        ("Capitulo Um", "text/ch1.xhtml"),
        ("Capitulo Dois", "text/ch2.xhtml"),
    ]


def test_toc_ncx_labels_extract_and_apply(tmp_path, epub2_path):
    ebook = open_ebook(epub2_path)
    assert ebook.toc_labels == ["Chapter One", "Chapter Two"]
    out = tmp_path / "out.epub"
    write_translated(ebook, out, toc_labels=["Capitulo Um", "Capitulo Dois"])
    with zipfile.ZipFile(out) as zf:
        ncx = zf.read("OEBPS/toc.ncx")
    root = etree.fromstring(ncx)
    texts = [el.text for el in _ncx_label_texts(root)]
    srcs = [el.get("src") for el in root.iter(f"{{{NCX_NS}}}content")]
    assert texts == ["Capitulo Um", "Capitulo Dois"]
    assert srcs == ["text/ch1.xhtml", "text/ch2.xhtml"]


def _ncx_label_texts(root):
    for el in root.iter(f"{{{NCX_NS}}}text"):
        parent = el.getparent()
        if parent is not None and parent.tag == f"{{{NCX_NS}}}navLabel":
            yield el


def test_toc_both_nav_and_ncx(tmp_path):
    path = tmp_path / "both.epub"
    path.write_bytes(builders.build_epub3_with_ncx())
    out = tmp_path / "out.epub"
    ebook = open_ebook(path)
    assert ebook.toc_kind == "nav"
    write_translated(ebook, out, toc_labels=["Um", "Dois"])
    with zipfile.ZipFile(out) as zf:
        nav = zf.read("OEBPS/nav.xhtml")
        ncx = zf.read("OEBPS/toc.ncx")
    assert [a.text_content() for a in lxml.html.document_fromstring(nav).iter("a")] == [
        "Um",
        "Dois",
    ]
    ncx_root = etree.fromstring(ncx)
    assert [el.text for el in _ncx_label_texts(ncx_root)] == ["Um", "Dois"]


def test_toc_label_count_mismatch_raises(tmp_path, epub2_path):
    ebook = open_ebook(epub2_path)
    with pytest.raises(ValueError):
        write_translated(ebook, tmp_path / "out.epub", toc_labels=["so um"])


def test_nav_apply_count_mismatch():
    source = builders.NAV.encode("utf-8")
    with pytest.raises(ValueError):
        apply_nav_labels(source, ["x", "y", "z"])


def test_ncx_apply_count_mismatch():
    source = builders.NCX.encode("utf-8")
    with pytest.raises(ValueError):
        apply_ncx_labels(source, ["x"])


def test_apply_nav_roundtrip():
    source = builders.NAV.encode("utf-8")
    labels = extract_nav_labels(source)
    assert labels == ["Chapter One", "Chapter Two"]
    out = apply_nav_labels(source, ["A", "B"])
    assert extract_nav_labels(out) == ["A", "B"]


def test_apply_nav_labels_with_nested_children():
    source = (
        b'<?xml version="1.0"?>\n<html><body><nav><ol><li>'
        b'<a href="ch1.xhtml">Chapter <span>One</span></a>'
        b"</li></ol></nav></body></html>"
    )
    out = apply_nav_labels(source, ["Capitulo Um"])
    root = lxml.html.document_fromstring(out)
    link = list(root.iter("a"))[0]
    assert link.text == "Capitulo Um"
    assert link.get("href") == "ch1.xhtml"
    assert len(link) == 0


def test_apply_ncx_labels_with_nested_children():
    source = (
        b'<?xml version="1.0" encoding="utf-8"?>\n'
        b'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        b'<navMap><navPoint id="n1" playOrder="1">'
        b"<navLabel><text>Chapter <b>One</b></text></navLabel>"
        b'<content src="ch1.xhtml"/></navPoint></navMap></ncx>'
    )
    out = apply_ncx_labels(source, ["Capitulo Um"])
    root = etree.fromstring(out)
    text_el = next(el for el in root.iter(f"{{{NCX_NS}}}text"))
    assert text_el.text == "Capitulo Um"
    assert len(text_el) == 0


def test_apply_ncx_roundtrip():
    source = builders.NCX.encode("utf-8")
    labels = extract_ncx_labels(source)
    assert labels == ["Chapter One", "Chapter Two"]
    out = apply_ncx_labels(source, ["A", "B"])
    assert extract_ncx_labels(out) == ["A", "B"]


def test_write_does_not_overwrite_original(tmp_path, epub2_path):
    original = epub2_path.read_bytes()
    ebook = open_ebook(epub2_path)
    write_translated(ebook, tmp_path / "out.epub", target_lang="pt-BR")
    assert epub2_path.read_bytes() == original


def test_write_refuses_same_path(tmp_path, epub2_path):
    ebook = open_ebook(epub2_path)
    with pytest.raises(MalformedEpubError):
        write_translated(ebook, epub2_path, target_lang="pt-BR")


def test_output_is_openable(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    write_translated(ebook, out, target_lang="pt-BR", translated_title="Titulo")
    reopened = open_ebook(out)
    assert reopened.container.language == "pt-BR"
    assert reopened.container.title == "Titulo"
    assert reopened.container.spine == ebook.container.spine


def test_metadata_creates_missing_fields():
    opf = builders.OPF2.encode("utf-8")
    out = update_metadata(
        opf, language="pt-BR", title="Novo Titulo", modified="2024-01-01T00:00:00Z"
    )
    root = etree.fromstring(out)
    metadata = root.find(f".//{{{OPF_NS}}}metadata")
    assert metadata.findtext(f"{{{DC_NS}}}language") == "pt-BR"
    assert metadata.findtext(f"{{{DC_NS}}}title") == "Novo Titulo"
    assert metadata.findtext(f"{{{DC_NS}}}date") == "2024-01-01T00:00:00Z"


def test_metadata_updates_after_non_matching_meta():
    source = builders.OPF3.replace(
        '    <meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>\n',
        '    <meta property="rendition:layout">reflowable</meta>\n'
        '    <meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>\n',
    ).encode("utf-8")
    out = update_metadata(source, modified="2024-01-01T00:00:00Z")
    root = etree.fromstring(out)
    metas = root.findall(f".//{{{OPF_NS}}}metadata/{{{OPF_NS}}}meta")
    modified = [m for m in metas if m.get("property") == "dcterms:modified"]
    assert modified[0].text == "2024-01-01T00:00:00Z"
    assert len(metas) == 2


def test_metadata_without_metadata_element_raises():
    with pytest.raises(ValueError):
        update_metadata(b"<package/>", language="pt-BR")


def test_write_zip_gap_between_entries_raises(tmp_path, epub2_path):
    ebook = open_ebook(epub2_path)
    first, _, _ = ebook._spans[0]
    info = zipfile.ZipInfo("gap.txt", (2020, 1, 1, 0, 0, 0))
    with pytest.raises(MalformedEpubError):
        write_zip(ebook._data, [(first, 0, 10), (info, 100, 130)], {}, tmp_path / "gap.epub")


def test_write_zip_span_overflow_raises(tmp_path):
    info = zipfile.ZipInfo("mimetype", (2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    with pytest.raises(MalformedEpubError):
        write_zip(b"PK\x03\x04mimetype", [(info, 0, 999999)], {}, tmp_path / "overflow.epub")


def test_write_zip_unsupported_method_raises(tmp_path):
    path = tmp_path / "bzip2.epub"
    path.write_bytes(builders.build_bzip2_opf())
    ebook = open_ebook(path)
    out = tmp_path / "out.epub"
    with pytest.raises(MalformedEpubError):
        write_translated(ebook, out, target_lang="pt-BR")


def test_write_zip_replaces_mimetype_stored(tmp_path, epub2_path):
    ebook = open_ebook(epub2_path)
    out = tmp_path / "out.epub"
    write_zip(ebook._data, ebook._spans, {"mimetype": b"application/epub+zip"}, out)
    with zipfile.ZipFile(out) as zf:
        assert zf.namelist()[0] == "mimetype"
        assert zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"


def skeleton(root: lxml.html.HtmlElement) -> str:
    """Serializa a estrutura (tags e atributos) sem nenhum texto."""

    def clean(el: lxml.html.HtmlElement) -> str:
        parts = []
        for child in el.iterdescendants():
            if isinstance(child.tag, str):
                attrs = "".join(f"{k}={v!r}" for k, v in sorted(child.attrib.items()))
                parts.append(f"<{child.tag}{attrs}>")
        return "".join(parts)

    return clean(root)
