"""Escrita cirurgica do EPUB de saida.

Reescreve o ZIP preservando a ordem e os metadados de cada entrada:
arquivos intocados sao copiados byte a byte do original (intervalos
brutos do ZIP), e arquivos tocados (capitulos, OPF, sumario) sao
recomprimidos no mesmo lugar. A entrada ``mimetype`` permanece a
primeira e sem compressao. O apendice de glossario (tarefa 5.5) entra
como arquivo novo ao fim do ZIP, com o OPF atualizado (manifest+spine).
"""

from __future__ import annotations

import posixpath
import struct
import zipfile
import zlib
from collections.abc import Mapping, Sequence
from pathlib import Path

from tradutor.epub.appendix import APPENDIX_HREF, add_appendix_to_opf, build_appendix_xhtml
from tradutor.epub.container import Ebook, Span
from tradutor.epub.errors import MalformedEpubError
from tradutor.epub.metadata import update_metadata
from tradutor.epub.segments import render_chapter
from tradutor.epub.toc import (
    apply_nav_labels,
    apply_ncx_labels,
    extract_nav_labels,
    extract_ncx_labels,
)

_LH_FMT = "<4s5H3I2H"
_CD_FMT = "<4s4H2H3I5H2I"
_EOCD_FMT = "<4s4H2IH"
_UNSUPPORTED_METHOD = MalformedEpubError("metodo de compressao nao suportado; tente o modo reparo")


def write_translated(
    ebook: Ebook,
    out_path: str | Path,
    *,
    translations: Mapping[int, str] | None = None,
    toc_labels: Sequence[str] | None = None,
    target_lang: str | None = None,
    translated_title: str | None = None,
    modified: str | None = None,
    appendix_entries: Sequence[tuple[str, str]] | None = None,
) -> Path:
    """Grava ``out_path`` com as traducoes/metadados aplicados.

    Capitulos sem nenhum bloco traduzido sao copiados byte a byte; o
    arquivo original nunca e sobrescrito. ``appendix_entries`` adiciona
    o apendice de glossario ao backmatter do livro de saida. Os rotulos
    do sumario sao aplicados por arquivo (nav/NCX): quando um arquivo tem
    contagem de rotulos diferente da fornecida (nav e NCX divergentes,
    comum em conversoes), ele e mantido no original.
    """
    out = Path(out_path)
    if out.resolve() == ebook.path.resolve():
        raise MalformedEpubError("o arquivo de saida nao pode sobrescrever o original")

    translations = translations or {}
    replacements: dict[str, bytes] = {}
    for chapter in ebook.chapters:
        texts = {
            block.id: text
            for block in chapter.blocks
            if (text := translations.get(block.id)) is not None
        }
        if texts:
            replacements[chapter.path] = render_chapter(
                ebook._sources[chapter.path], chapter.blocks, texts
            )

    if toc_labels is not None:
        labels = list(toc_labels)
        nav_path = ebook.container.nav_path
        ncx_path = ebook.container.ncx_path
        if nav_path and nav_path in ebook._sources:
            source = ebook._sources[nav_path]
            if ebook.toc_kind == "nav" or len(extract_nav_labels(source)) == len(labels):
                replacements[nav_path] = apply_nav_labels(source, labels)
        if ncx_path and ncx_path in ebook._sources:
            source = ebook._sources[ncx_path]
            if ebook.toc_kind == "ncx" or len(extract_ncx_labels(source)) == len(labels):
                replacements[ncx_path] = apply_ncx_labels(source, labels)

    if target_lang is not None or translated_title is not None or modified is not None:
        replacements[ebook.container.opf_path] = update_metadata(
            ebook._sources[ebook.container.opf_path],
            language=target_lang,
            title=translated_title,
            modified=modified,
        )

    new_entries: dict[str, bytes] = {}
    if appendix_entries:
        entries = list(appendix_entries)
        if entries:
            opf = (
                replacements.get(ebook.container.opf_path)
                or ebook._sources[ebook.container.opf_path]
            )
            replacements[ebook.container.opf_path] = add_appendix_to_opf(opf)
            zip_path = posixpath.join(ebook.container.opf_dir, APPENDIX_HREF)
            new_entries[zip_path] = build_appendix_xhtml(entries)

    return write_zip(
        ebook._data,
        ebook._spans,
        replacements,
        out,
        comment=ebook._comment,
        new_entries=new_entries,
    )


def write_zip(
    data: bytes,
    spans: Sequence[Span],
    replacements: Mapping[str, bytes],
    out_path: str | Path,
    *,
    comment: bytes = b"",
    new_entries: Mapping[str, bytes] | None = None,
) -> Path:
    """Reescreve o ZIP: copias brutas para intocados, novas para tocados."""
    out = Path(out_path)
    written: list[tuple[zipfile.ZipInfo, int, int, int]] = []
    with open(out, "wb") as f:
        previous_end: int | None = None
        for info, start, end in spans:
            if previous_end is not None and start != previous_end:
                raise MalformedEpubError("estrutura ZIP nao suportada; tente o modo reparo")
            offset = f.tell()
            if info.filename in replacements:
                _write_replaced(f, info, info.filename, replacements[info.filename])
            else:
                if end > len(data):
                    raise MalformedEpubError("ZIP original corrompido")
                f.write(memoryview(data)[start:end])
            written.append((info, offset, info.compress_size, info.file_size))
            previous_end = end
        for name, payload in (new_entries or {}).items():
            if any(info.filename == name for info, _, _ in spans):
                raise MalformedEpubError(f"entrada ja existente: {name}")
            offset = f.tell()
            info = _new_zipinfo(name)
            _write_replaced(f, info, name, payload)
            written.append((info, offset, info.compress_size, info.file_size))
        cd_start = f.tell()
        for info, offset, csize, usize in written:
            f.write(_central_header(info, offset, csize, usize))
        cd_size = f.tell() - cd_start
        f.write(_eocd(len(written), cd_start, cd_size, comment))
    return out


def _new_zipinfo(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info._compresslevel = 6
    return info


def _write_replaced(f, info: zipfile.ZipInfo, name: str, payload: bytes) -> zipfile.ZipInfo:
    """Grava uma entrada tocada, devolvendo o ``ZipInfo`` com campos novos."""
    if name == "mimetype" or info.compress_type == zipfile.ZIP_STORED:
        method = zipfile.ZIP_STORED
        cdata = payload
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        level = getattr(info, "_compresslevel", None) or 6
        compressor = zlib.compressobj(level=level, wbits=-zlib.MAX_WBITS)
        cdata = compressor.compress(payload) + compressor.flush()
        method = zipfile.ZIP_DEFLATED
    else:
        raise _UNSUPPORTED_METHOD
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    info.compress_type = method
    info.flag_bits &= ~0x8
    info.CRC = crc
    info.file_size = len(payload)
    info.compress_size = len(cdata)
    f.write(_local_header(info, crc, len(cdata), len(payload)))
    f.write(cdata)
    return info


def _dos_time(date_time: tuple[int, ...]) -> int:
    return (date_time[3] << 11) | (date_time[4] << 5) | (date_time[5] // 2)


def _dos_date(date_time: tuple[int, ...]) -> int:
    return ((date_time[0] - 1980) << 9) | (date_time[1] << 5) | date_time[2]


def _local_header(info: zipfile.ZipInfo, crc: int, csize: int, usize: int) -> bytes:
    name = info.filename.encode("utf-8")
    return (
        struct.pack(
            _LH_FMT,
            b"PK\x03\x04",
            info.extract_version,
            info.flag_bits & ~0x8,
            info.compress_type,
            _dos_time(info.date_time),
            _dos_date(info.date_time),
            crc & 0xFFFFFFFF,
            csize & 0xFFFFFFFF,
            usize & 0xFFFFFFFF,
            len(name),
            0,
        )
        + name
    )


def _central_header(info: zipfile.ZipInfo, offset: int, csize: int, usize: int) -> bytes:
    name = info.filename.encode("utf-8")
    extra = info.extra
    comment = info.comment or b""
    return (
        struct.pack(
            _CD_FMT,
            b"PK\x01\x02",
            info.create_version,
            info.extract_version,
            info.flag_bits & ~0x8,
            info.compress_type,
            _dos_time(info.date_time),
            _dos_date(info.date_time),
            info.CRC & 0xFFFFFFFF,
            csize & 0xFFFFFFFF,
            usize & 0xFFFFFFFF,
            len(name),
            len(extra),
            len(comment),
            0,
            info.internal_attr,
            info.external_attr,
            offset & 0xFFFFFFFF,
        )
        + name
        + extra
        + comment
    )


def _eocd(count: int, cd_start: int, cd_size: int, comment: bytes) -> bytes:
    return (
        struct.pack(
            _EOCD_FMT,
            b"PK\x05\x06",
            0,
            0,
            count & 0xFFFF,
            count & 0xFFFF,
            cd_size & 0xFFFFFFFF,
            cd_start & 0xFFFFFFFF,
            len(comment),
        )
        + comment
    )
