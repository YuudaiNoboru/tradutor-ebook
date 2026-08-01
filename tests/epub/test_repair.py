"""Testes do modo reparo via ebooklib (task 3.7)."""

import zipfile

import pytest

from tests.epub import builders
from tradutor.epub import EpubError, MalformedEpubError, open_ebook, repair_epub


def test_repair_mimetype_not_first(tmp_path):
    src = tmp_path / "broken.epub"
    src.write_bytes(builders.build_mimetype_not_first())
    with pytest.raises(MalformedEpubError):
        open_ebook(src)
    out = tmp_path / "fixed.epub"
    repair_epub(src, out)
    ebook = open_ebook(out)
    assert len(ebook.chapters) == 2
    assert ebook.chapters[0].blocks[0].text == "Chapter One"


def test_repair_mimetype_compressed(tmp_path):
    src = tmp_path / "broken.epub"
    src.write_bytes(builders.build_mimetype_compressed())
    with pytest.raises(MalformedEpubError):
        open_ebook(src)
    out = tmp_path / "fixed.epub"
    repair_epub(src, out)
    with zipfile.ZipFile(out) as zf:
        assert zf.namelist()[0] == "mimetype"
        assert zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"


def test_repair_missing_container_xml_fails(tmp_path):
    src = tmp_path / "broken.epub"
    src.write_bytes(builders.build_missing_container_xml())
    out = tmp_path / "fixed.epub"
    with pytest.raises(MalformedEpubError):
        repair_epub(src, out)


def test_repair_output_is_translatable(tmp_path):
    src = tmp_path / "broken.epub"
    src.write_bytes(builders.build_mimetype_not_first())
    out = tmp_path / "fixed.epub"
    repair_epub(src, out)
    ebook = open_ebook(out)
    assert ebook.toc_labels == ["Chapter One", "Chapter Two"]


def test_repair_write_failure_raises(tmp_path, monkeypatch):
    src = tmp_path / "broken.epub"
    src.write_bytes(builders.build_mimetype_not_first())

    def boom(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr("ebooklib.epub.write_epub", boom)
    with pytest.raises(EpubError):
        repair_epub(src, tmp_path / "fixed.epub")
