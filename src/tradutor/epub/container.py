"""Leitura de container EPUB: ZIP, mimetype, container.xml, OPF e spine.

``open_ebook`` valida o container (mimetype obrigatorio, primeiro e sem
compressao), detecta DRM, parseia o OPF (manifest/spine/metadados) e
segmenta os capitulos do spine em blocos do dominio. Os dados brutos do
ZIP ficam retidos para a escrita cirurgica byte a byte.
"""

from __future__ import annotations

import io
import posixpath
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from tradutor.domain import Chapter
from tradutor.epub.errors import DrmError, EpubError, MalformedEpubError, NotEpubError
from tradutor.epub.metadata import DC_NS, OPF_NS
from tradutor.epub.segments import parse_chapter
from tradutor.epub.toc import extract_nav_labels, extract_ncx_labels

CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
MIMETYPE = b"application/epub+zip"
XHTML_MEDIA_TYPES = frozenset({"application/xhtml+xml", "text/html"})

Span = tuple[zipfile.ZipInfo, int, int]


@dataclass(frozen=True, slots=True)
class ManifestItem:
    href: str
    media_type: str
    properties: str = ""


@dataclass(frozen=True, slots=True)
class SpineItem:
    idref: str
    path: str
    linear: bool = True


@dataclass(slots=True)
class Container:
    opf_path: str
    opf_dir: str
    manifest: dict[str, ManifestItem] = field(default_factory=dict)
    spine: list[SpineItem] = field(default_factory=list)
    title: str = ""
    language: str | None = None
    modified: str | None = None
    nav_path: str | None = None
    ncx_path: str | None = None


@dataclass(slots=True)
class Ebook:
    """Livro aberto: metadados, capitulos em blocos e dados para escrita."""

    path: Path
    container: Container
    chapters: list[Chapter] = field(default_factory=list)
    toc_labels: list[str] = field(default_factory=list)
    _data: bytes = b""
    _spans: list[Span] = field(default_factory=list)
    _sources: dict[str, bytes] = field(default_factory=dict)
    _comment: bytes = b""

    @property
    def toc_kind(self) -> str | None:
        if self.container.nav_path:
            return "nav"
        if self.container.ncx_path:
            return "ncx"
        return None


def open_ebook(path: str | Path) -> Ebook:
    """Abre e valida um EPUB 2 ou 3, segmentando os capitulos do spine."""
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise EpubError(f"nao foi possivel ler o arquivo: {exc}") from exc
    if not data.startswith(b"PK\x03\x04"):
        raise NotEpubError("o arquivo nao parece ser um EPUB (ZIP invalido)")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise NotEpubError("o arquivo nao parece ser um EPUB (ZIP invalido)") from exc

    entries = zf.infolist()
    if not entries or entries[0].filename != "mimetype":
        raise MalformedEpubError("entrada mimetype ausente ou fora do lugar; tente o modo reparo")
    if entries[0].compress_type != zipfile.ZIP_STORED:
        raise MalformedEpubError("entrada mimetype compactada; tente o modo reparo")
    if zf.read("mimetype").strip() != MIMETYPE:
        raise MalformedEpubError("conteudo da entrada mimetype invalido")
    names = zf.namelist()
    if "META-INF/encryption.xml" in names:
        raise DrmError("o livro parece estar protegido por DRM e nao pode ser traduzido")

    spans: list[Span] = []
    for info in entries:
        if info.flag_bits & 0x1:
            raise DrmError("o livro contem entradas criptografadas (DRM)")
        if info.flag_bits & 0x8:
            raise MalformedEpubError("estrutura ZIP nao suportada; tente o modo reparo")
        start = info.header_offset
        end = start + 30 + len(info.filename) + len(info.extra) + info.compress_size
        if end > len(data):
            raise MalformedEpubError("estrutura ZIP corrompida; tente o modo reparo")
        spans.append((info, start, end))

    container_xml = "META-INF/container.xml"
    if container_xml not in names:
        raise MalformedEpubError("META-INF/container.xml ausente; tente o modo reparo")
    try:
        croot = etree.fromstring(zf.read(container_xml))
    except etree.XMLSyntaxError as exc:
        raise MalformedEpubError("container.xml invalido; tente o modo reparo") from exc
    rootfiles = croot.findall(f".//{{{CONTAINER_NS}}}rootfile")
    if not rootfiles:
        raise MalformedEpubError("container.xml sem rootfile; tente o modo reparo")
    opf_path = rootfiles[0].get("full-path") or ""
    if not opf_path or opf_path not in names:
        raise MalformedEpubError("OPF declarado no container nao existe; tente o modo reparo")

    opf_bytes = zf.read(opf_path)
    container = _parse_opf(opf_bytes, opf_path, posixpath.dirname(opf_path), names)

    for item in container.manifest.values():
        if "encrypted" in item.properties.split():
            raise DrmError("o livro contem conteudo criptografado (DRM)")

    sources: dict[str, bytes] = {container.opf_path: opf_bytes}
    chapters: list[Chapter] = []
    seen: set[str] = set()
    for item in container.spine:
        if item.path in seen:
            continue
        seen.add(item.path)
        chapter_source = zf.read(item.path)
        sources[item.path] = chapter_source
        chapters.append(parse_chapter(chapter_source, path=item.path))
    _renumber(chapters)

    if container.nav_path and container.nav_path in names:
        sources[container.nav_path] = zf.read(container.nav_path)
    if container.ncx_path and container.ncx_path in names:
        sources[container.ncx_path] = zf.read(container.ncx_path)

    toc_labels: list[str] = []
    if container.nav_path:
        toc_labels = extract_nav_labels(sources[container.nav_path])
    elif container.ncx_path:
        toc_labels = extract_ncx_labels(sources[container.ncx_path])

    return Ebook(
        path=source,
        container=container,
        chapters=chapters,
        toc_labels=toc_labels,
        _data=data,
        _spans=spans,
        _sources=sources,
        _comment=zf.comment,
    )


def output_path_for(path: str | Path, lang: str) -> Path:
    """Caminho do arquivo de saida: ``livro-<idioma>.epub`` ao lado do original."""
    source = Path(path)
    return source.with_name(f"{source.stem}-{lang}.epub")


def _parse_opf(opf_bytes: bytes, opf_path: str, opf_dir: str, names: list[str]) -> Container:
    try:
        root = etree.fromstring(opf_bytes)
    except etree.XMLSyntaxError as exc:
        raise MalformedEpubError("OPF invalido; tente o modo reparo") from exc

    manifest: dict[str, ManifestItem] = {}
    for el in root.findall(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item"):
        manifest[el.get("id", "")] = ManifestItem(
            href=el.get("href", ""),
            media_type=el.get("media-type", ""),
            properties=el.get("properties", ""),
        )

    spine: list[SpineItem] = []
    for el in root.findall(f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref"):
        idref = el.get("idref", "")
        item = manifest.get(idref)
        if item is None or item.media_type not in XHTML_MEDIA_TYPES:
            continue
        resolved = _resolve(opf_dir, item.href)
        if resolved not in names:
            raise MalformedEpubError(f"spine referencia arquivo ausente: {resolved}")
        spine.append(SpineItem(idref=idref, path=resolved, linear=el.get("linear", "yes") != "no"))

    nav_path = ncx_path = None
    for item in manifest.values():
        if "nav" in item.properties.split():
            resolved = _resolve(opf_dir, item.href)
            if resolved in names:
                nav_path = resolved
        if item.media_type == "application/x-dtbncx+xml":
            resolved = _resolve(opf_dir, item.href)
            if resolved in names:
                ncx_path = resolved

    title = root.findtext(f".//{{{OPF_NS}}}metadata/{{{DC_NS}}}title") or ""
    language = root.findtext(f".//{{{OPF_NS}}}metadata/{{{DC_NS}}}language")
    modified = None
    for el in root.findall(f".//{{{OPF_NS}}}metadata/{{{OPF_NS}}}meta"):
        if el.get("property") == "dcterms:modified":
            modified = el.text
            break
    if modified is None:
        modified = root.findtext(f".//{{{OPF_NS}}}metadata/{{{DC_NS}}}date")

    return Container(
        opf_path=opf_path,
        opf_dir=opf_dir,
        manifest=manifest,
        spine=spine,
        title=title,
        language=language,
        modified=modified,
        nav_path=nav_path,
        ncx_path=ncx_path,
    )


def _resolve(opf_dir: str, href: str) -> str:
    href = urllib.parse.unquote(href)
    return posixpath.normpath(posixpath.join(opf_dir, href))


def _renumber(chapters: list[Chapter]) -> None:
    """Renumera os ids dos blocos globalmente, na ordem do spine."""
    next_id = 0
    for chapter in chapters:
        for block in chapter.blocks:
            block.id = next_id
            next_id += 1
