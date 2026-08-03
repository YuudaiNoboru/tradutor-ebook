"""Testes do apendice de glossario no backmatter (tarefa 5.5)."""

import zipfile

import pytest
from lxml import etree

from tests.epub import builders
from tradutor.epub import MalformedEpubError, open_ebook, write_translated
from tradutor.epub.appendix import (
    APPENDIX_HREF,
    APPENDIX_ITEM_ID,
    XHTML_NS,
    add_appendix_to_opf,
    build_appendix_xhtml,
)
from tradutor.epub.metadata import OPF_NS
from tradutor.epub.writer import write_zip

ENTRIES = [("queue", "fila"), ("cache", "cache")]


@pytest.fixture
def epub2_path(tmp_path):
    path = tmp_path / "book.epub"
    path.write_bytes(builders.build_epub2())
    return path


def test_build_appendix_xhtml_contains_entries():
    source = build_appendix_xhtml(ENTRIES)
    root = etree.fromstring(source)
    assert root.tag == f"{{{root.nsmap[None]}}}html"
    terms = [
        (dt.text, dd.text)
        for dt, dd in zip(
            root.iter(f"{{{XHTML_NS}}}dt"), root.iter(f"{{{XHTML_NS}}}dd"), strict=True
        )
    ]
    assert terms == ENTRIES
    title = root.find(f".//{{{XHTML_NS}}}title")
    assert title is not None and title.text == "Glossário"


def test_build_appendix_xhtml_accepts_custom_title():
    root = etree.fromstring(build_appendix_xhtml(ENTRIES, title="Anexo"))
    assert root.findtext(f".//{{{XHTML_NS}}}title") == "Anexo"
    assert root.findtext(f".//{{{XHTML_NS}}}h1") == "Anexo"


def test_add_appendix_to_opf_adds_manifest_and_spine():
    opf = builders.OPF2.encode("utf-8")
    out = add_appendix_to_opf(opf)
    root = etree.fromstring(out)
    item = root.find(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item[@id='{APPENDIX_ITEM_ID}']")
    assert item is not None
    assert item.get("href") == APPENDIX_HREF
    assert item.get("media-type") == "application/xhtml+xml"
    spine = [el.get("idref") for el in root.findall(f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref")]
    assert spine[-1] == APPENDIX_ITEM_ID


def test_add_appendix_to_opf_works_for_epub3():
    root = etree.fromstring(add_appendix_to_opf(builders.OPF3.encode("utf-8")))
    assert (
        root.find(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item[@id='{APPENDIX_ITEM_ID}']") is not None
    )


def test_add_appendix_to_opf_duplicate_id_raises():
    opf = add_appendix_to_opf(builders.OPF2.encode("utf-8"))
    with pytest.raises(ValueError, match="item duplicado"):
        add_appendix_to_opf(opf)


def test_add_appendix_to_opf_missing_manifest_raises():
    with pytest.raises(ValueError, match="manifest"):
        add_appendix_to_opf(b"<package/>")


@pytest.mark.parametrize("builder", [builders.build_epub2, builders.build_epub3])
def test_write_translated_appends_glossary(tmp_path, builder):
    path = tmp_path / "in.epub"
    path.write_bytes(builder())
    out = tmp_path / "out.epub"
    ebook = open_ebook(path)
    write_translated(ebook, out, appendix_entries=ENTRIES)

    with zipfile.ZipFile(out) as zf:
        appendix_path = "OEBPS/" + APPENDIX_HREF
        assert appendix_path in zf.namelist()
        root = etree.fromstring(zf.read(appendix_path))
        assert [
            (dt.text, dd.text)
            for dt, dd in zip(
                root.iter(f"{{{XHTML_NS}}}dt"), root.iter(f"{{{XHTML_NS}}}dd"), strict=True
            )
        ] == ENTRIES
        opf = etree.fromstring(zf.read("OEBPS/content.opf"))
        assert (
            opf.find(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item[@id='{APPENDIX_ITEM_ID}']")
            is not None
        )
        spine = [el.get("idref") for el in opf.findall(f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref")]
        assert spine[-1] == APPENDIX_ITEM_ID
        assert zf.read("mimetype") == b"application/epub+zip"


@pytest.mark.parametrize("builder", [builders.build_epub2, builders.build_epub3])
def test_untouched_entries_identical_with_appendix(tmp_path, builder):
    path = tmp_path / "in.epub"
    path.write_bytes(builder())
    out = tmp_path / "out.epub"
    ebook = open_ebook(path)
    write_translated(ebook, out, appendix_entries=ENTRIES)
    with zipfile.ZipFile(out) as zf, zipfile.ZipFile(path) as zf_orig:
        for name in zf.namelist():
            if name == "OEBPS/content.opf" or name == "OEBPS/" + APPENDIX_HREF:
                continue
            assert zf.read(name) == zf_orig.read(name)


def test_write_translated_without_appendix_keeps_zip_intact(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    write_translated(ebook, out, translations={})
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert "OEBPS/" + APPENDIX_HREF not in names
    assert out.read_bytes() == epub2_path.read_bytes()


def test_output_with_appendix_reopens(tmp_path, epub2_path):
    out = tmp_path / "out.epub"
    ebook = open_ebook(epub2_path)
    write_translated(ebook, out, appendix_entries=ENTRIES)
    reopened = open_ebook(out)
    assert reopened.container.spine[-1].path == "OEBPS/" + APPENDIX_HREF


def test_write_zip_rejects_duplicate_new_entry(tmp_path, epub2_path):
    ebook = open_ebook(epub2_path)
    with pytest.raises(MalformedEpubError, match="entrada ja existente"):
        write_zip(
            ebook._data,
            ebook._spans,
            {},
            tmp_path / "out.epub",
            new_entries={"mimetype": b"application/epub+zip"},
        )
