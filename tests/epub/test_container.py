"""Testes do container: leitura/validacao (tasks 3.1 e 3.6)."""

import zipfile

import pytest

from tests.epub import builders
from tradutor.domain import Block
from tradutor.epub import (
    DrmError,
    EpubError,
    MalformedEpubError,
    NotEpubError,
    open_ebook,
    output_path_for,
)


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


def test_open_epub2(epub2_path):
    ebook = open_ebook(epub2_path)
    container = ebook.container
    assert container.title == "The English Book"
    assert container.language == "en"
    assert container.opf_path == "OEBPS/content.opf"
    assert container.ncx_path == "OEBPS/toc.ncx"
    assert container.nav_path is None
    assert ebook.toc_kind == "ncx"
    assert ebook.toc_labels == ["Chapter One", "Chapter Two"]
    assert [item.path for item in container.spine] == [
        "OEBPS/text/ch1.xhtml",
        "OEBPS/text/ch2.xhtml",
    ]
    assert ebook.path == epub2_path


def test_open_epub3(epub3_path):
    ebook = open_ebook(epub3_path)
    assert ebook.container.nav_path == "OEBPS/nav.xhtml"
    assert ebook.container.ncx_path is None
    assert ebook.toc_kind == "nav"
    assert ebook.toc_labels == ["Chapter One", "Chapter Two"]
    assert ebook.container.modified == "2020-01-01T00:00:00Z"


def test_spine_chapters_in_order(epub2_path):
    ebook = open_ebook(epub2_path)
    assert [chapter.path for chapter in ebook.chapters] == [
        "OEBPS/text/ch1.xhtml",
        "OEBPS/text/ch2.xhtml",
    ]
    assert ebook.chapters[0].title == "Chapter One"
    assert ebook.chapters[1].title == "Chapter Two"


def test_blocks_renumbered_globally(epub2_path):
    ebook = open_ebook(epub2_path)
    ids = [block.id for chapter in ebook.chapters for block in chapter.blocks]
    assert ids == list(range(len(ids)))


def test_manifest_parsed(epub2_path):
    manifest = open_ebook(epub2_path).container.manifest
    assert manifest["ch1"].href == "text/ch1.xhtml"
    assert manifest["ch1"].media_type == "application/xhtml+xml"
    assert manifest["ncx"].media_type == "application/x-dtbncx+xml"
    assert manifest["css"].href == "styles/style.css"


def test_epub3_nav_manifest_properties(epub3_path):
    item = open_ebook(epub3_path).container.manifest["nav"]
    assert item.properties == "nav"
    assert item.href == "nav.xhtml"


def test_not_a_zip(tmp_path):
    path = tmp_path / "fake.epub"
    path.write_bytes(builders.build_not_a_zip())
    with pytest.raises(NotEpubError):
        open_ebook(path)


def test_corrupt_zip_with_pk_magic(tmp_path):
    path = tmp_path / "corrupt.epub"
    path.write_bytes(builders.build_corrupt_zip())
    with pytest.raises(NotEpubError):
        open_ebook(path)


def test_wrong_mimetype_content(tmp_path):
    path = tmp_path / "wrong-mime.epub"
    path.write_bytes(builders.build_wrong_mimetype_content())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_encrypted_entry_flag(tmp_path):
    path = tmp_path / "encrypted-entry.epub"
    path.write_bytes(
        builders.patch_entry_flags(builders.build_epub2(), "META-INF/container.xml", 0x1)
    )
    with pytest.raises(DrmError):
        open_ebook(path)


def test_data_descriptor_flag(tmp_path):
    path = tmp_path / "descriptor.epub"
    path.write_bytes(
        builders.patch_entry_flags(builders.build_epub2(), "META-INF/container.xml", 0x8)
    )
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_corrupt_span(tmp_path):
    path = tmp_path / "corrupt-span.epub"
    path.write_bytes(
        builders.patch_entry_csize(builders.build_epub2(), "OEBPS/images/cover.png", 1000)
    )
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_invalid_container_xml(tmp_path):
    path = tmp_path / "bad-container.epub"
    path.write_bytes(builders.build_invalid_container_xml())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_container_without_rootfile(tmp_path):
    path = tmp_path / "no-rootfile.epub"
    path.write_bytes(builders.build_container_without_rootfile())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_opf_missing_from_container(tmp_path):
    path = tmp_path / "no-opf.epub"
    path.write_bytes(builders.build_opf_missing())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_corrupt_opf(tmp_path):
    path = tmp_path / "bad-opf.epub"
    path.write_bytes(builders.build_corrupt_opf())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_book_without_toc(tmp_path):
    path = tmp_path / "no-toc.epub"
    path.write_bytes(builders.build_epub2_without_toc())
    ebook = open_ebook(path)
    assert ebook.toc_kind is None
    assert ebook.toc_labels == []


def test_spine_skips_unknown_idref_and_non_xhtml(tmp_path):
    path = tmp_path / "extra-spine.epub"
    path.write_bytes(builders.build_spine_with_extra_items())
    spine = open_ebook(path).container.spine
    assert [item.path for item in spine] == [
        "OEBPS/text/ch1.xhtml",
        "OEBPS/text/ch2.xhtml",
    ]


def test_duplicate_spine_entries_deduped(tmp_path):
    path = tmp_path / "dup-spine.epub"
    path.write_bytes(builders.build_duplicate_spine())
    ebook = open_ebook(path)
    assert [chapter.path for chapter in ebook.chapters] == [
        "OEBPS/text/ch1.xhtml",
        "OEBPS/text/ch2.xhtml",
    ]


def test_nav_href_missing_ignored(tmp_path):
    path = tmp_path / "nav-missing.epub"
    path.write_bytes(builders.build_epub3_missing_nav_file())
    ebook = open_ebook(path)
    assert ebook.container.nav_path is None
    assert ebook.toc_kind is None


def test_ncx_href_missing_ignored(tmp_path):
    path = tmp_path / "ncx-missing.epub"
    path.write_bytes(builders.build_epub3_missing_ncx_file())
    ebook = open_ebook(path)
    assert ebook.container.ncx_path is None
    assert ebook.toc_kind == "nav"


def test_meta_loop_skips_non_modified(tmp_path):
    path = tmp_path / "meta-extra.epub"
    path.write_bytes(builders.build_opf_with_extra_meta())
    assert open_ebook(path).container.modified == "2020-01-01T00:00:00Z"


def test_opf_without_title_or_language(tmp_path):
    path = tmp_path / "bare-opf.epub"
    path.write_bytes(builders.build_opf_without_title_language())
    container = open_ebook(path).container
    assert container.title == ""
    assert container.language is None


def test_missing_file(epub2_path, tmp_path):
    with pytest.raises(EpubError):
        open_ebook(tmp_path / "nao-existe.epub")


def test_missing_mimetype(tmp_path):
    path = tmp_path / "no-mimetype.epub"
    path.write_bytes(
        builders._build(
            [
                ("META-INF/container.xml", builders.CONTAINER_XML.encode("utf-8")),
                ("OEBPS/content.opf", builders.OPF2.encode("utf-8")),
            ]
        )
    )
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_mimetype_not_first(tmp_path):
    path = tmp_path / "bad-order.epub"
    path.write_bytes(builders.build_mimetype_not_first())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_mimetype_compressed(tmp_path):
    path = tmp_path / "bad-mime.epub"
    path.write_bytes(builders.build_mimetype_compressed())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_missing_container_xml(tmp_path):
    path = tmp_path / "no-container.epub"
    path.write_bytes(builders.build_missing_container_xml())
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_drm_via_encryption_xml(tmp_path):
    path = tmp_path / "drm.epub"
    path.write_bytes(builders.build_drm_book())
    with pytest.raises(DrmError):
        open_ebook(path)


def test_drm_via_manifest_properties(tmp_path):
    opf = builders.OPF2.replace(
        'media-type="image/png"/>', 'media-type="image/png" properties="encrypted"/>'
    )
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", builders.CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/toc.ncx", builders.NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", builders.CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", builders.CH2.encode("utf-8")),
    ]
    path = tmp_path / "encrypted-props.epub"
    path.write_bytes(builders._build(entries))
    with pytest.raises(DrmError):
        open_ebook(path)


def test_spine_missing_file(tmp_path):
    opf = builders.OPF2.replace("text/ch2.xhtml", "text/ausente.xhtml")
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", builders.CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/toc.ncx", builders.NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", builders.CH1.encode("utf-8")),
    ]
    path = tmp_path / "broken-spine.epub"
    path.write_bytes(builders._build(entries))
    with pytest.raises(MalformedEpubError):
        open_ebook(path)


def test_output_path_for():
    out = output_path_for("livro.epub", "pt-BR")
    assert out.name == "livro-pt-BR.epub"


def test_spine_linear_flag(epub2_path):
    spine = open_ebook(epub2_path).container.spine
    assert all(item.linear for item in spine)


def test_block_types_exposed(epub2_path):
    chapter = open_ebook(epub2_path).chapters[0]
    assert all(isinstance(block, Block) for block in chapter.blocks)
