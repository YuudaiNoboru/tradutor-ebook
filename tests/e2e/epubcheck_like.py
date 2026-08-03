"""Validador local estilo epubcheck para os testes de integracao (tarefa 10.2).

Confere o essencial do epubcheck sem depender do jar do projeto: ZIP
com ``mimetype`` primeiro e sem compressao, XML bem formado
(container.xml, OPF, XHTML do spine, nav e NCX), manifest integro
(todo item existe no ZIP), spine integro (todo itemref resolve para um
item XHTML existente e bem formado) e metadados minimos (titulo e
idioma). Devolve um ``Report`` com a lista de problemas encontrados.
"""

from __future__ import annotations

import io
import posixpath
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree, html

from tradutor.epub.container import CONTAINER_NS, MIMETYPE
from tradutor.epub.metadata import DC_NS, OPF_NS

XHTML_MEDIA_TYPES = frozenset({"application/xhtml+xml", "text/html"})
NCX_MEDIA_TYPE = "application/x-dtbncx+xml"

OPF_MANIFEST = f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item"
OPF_SPINE = f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref"


@dataclass(frozen=True, slots=True)
class Issue:
    severity: str
    message: str


@dataclass(slots=True)
class Report:
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors()

    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]


def validate_epub(path: str | Path) -> Report:
    """Valida a estrutura de um EPUB e devolve o relatorio de problemas."""
    report = Report()
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        report.issues.append(Issue("error", f"arquivo ilegivel: {exc}"))
        return report
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        report.issues.append(Issue("error", f"ZIP invalido: {exc}"))
        return report

    names = zf.namelist()
    _check_mimetype(zf, names, report)
    opf_path = _check_container(zf, names, report)
    if opf_path is None:
        return report

    root = _parse_xml(zf, opf_path, report, label=f"OPF ({opf_path})")
    if root is None:
        return report
    _check_metadata(root, report)

    manifest, spine, nav_path, ncx_path = _parse_opf(root, posixpath.dirname(opf_path), report)
    if nav_path is not None:
        _parse_xhtml(zf, nav_path, report, label=f"nav ({nav_path})")
    if ncx_path is not None:
        _parse_xml(zf, ncx_path, report, label=f"NCX ({ncx_path})")
    _check_manifest_files(zf, names, manifest, report)
    _check_spine(zf, names, manifest, spine, report)
    return report


def _check_mimetype(zf: zipfile.ZipFile, names: list[str], report: Report) -> None:
    if not names:
        report.issues.append(Issue("error", "ZIP vazio"))
        return
    if names[0] != "mimetype":
        report.issues.append(Issue("error", "entrada mimetype nao e a primeira"))
        return
    info = zf.infolist()[0]
    if info.compress_type != zipfile.ZIP_STORED:
        report.issues.append(Issue("error", "entrada mimetype compactada"))
    if zf.read("mimetype").strip() != MIMETYPE:
        report.issues.append(Issue("error", "conteudo da entrada mimetype invalido"))


def _check_container(zf: zipfile.ZipFile, names: list[str], report: Report) -> str | None:
    if "META-INF/container.xml" not in names:
        report.issues.append(Issue("error", "META-INF/container.xml ausente"))
        return None
    root = _parse_xml(zf, "META-INF/container.xml", report, label="container.xml")
    if root is None:
        return None
    rootfiles = root.findall(f".//{{{CONTAINER_NS}}}rootfile")
    if not rootfiles:
        report.issues.append(Issue("error", "container.xml sem rootfile"))
        return None
    opf_path = rootfiles[0].get("full-path") or ""
    if not opf_path:
        report.issues.append(Issue("error", "rootfile sem full-path"))
        return None
    if opf_path not in names:
        report.issues.append(Issue("error", f"OPF declarado nao existe: {opf_path}"))
        return None
    return opf_path


def _parse_xml(
    zf: zipfile.ZipFile, name: str, report: Report, *, label: str
) -> etree._Element | None:
    try:
        return etree.fromstring(zf.read(name))
    except etree.XMLSyntaxError as exc:
        report.issues.append(Issue("error", f"{label}: XML mal formado ({exc})"))
        return None


def _check_metadata(root: etree._Element, report: Report) -> None:
    title = root.findtext(f".//{{{OPF_NS}}}metadata/{{{DC_NS}}}title")
    if not title:
        report.issues.append(Issue("error", "OPF sem dc:title"))
    language = root.findtext(f".//{{{OPF_NS}}}metadata/{{{DC_NS}}}language")
    if not language:
        report.issues.append(Issue("error", "OPF sem dc:language"))


def _parse_opf(
    root: etree._Element, opf_dir: str, report: Report
) -> tuple[dict[str, str], list[str], str | None, str | None]:
    """Extrai manifest (id -> caminho resolvido), spine e nav/ncx."""
    manifest: dict[str, str] = {}
    for el in root.findall(OPF_MANIFEST):
        item_id = el.get("id", "")
        href = urllib.parse.unquote(el.get("href", ""))
        path = posixpath.normpath(posixpath.join(opf_dir, href))
        manifest[item_id] = path
    nav_path = ncx_path = None
    for el in root.findall(OPF_MANIFEST):
        media_type = el.get("media-type", "")
        path = manifest.get(el.get("id", ""))
        if path is None:
            continue
        if "nav" in (el.get("properties") or "").split() and nav_path is None:
            nav_path = path
        if media_type == NCX_MEDIA_TYPE and ncx_path is None:
            ncx_path = path
    spine: list[str] = []
    for el in root.findall(OPF_SPINE):
        idref = el.get("idref", "")
        if idref not in manifest:
            report.issues.append(Issue("error", f"spine referencia item inexistente: {idref}"))
            continue
        spine.append(manifest[idref])
    return manifest, spine, nav_path, ncx_path


def _parse_xhtml(zf: zipfile.ZipFile, name: str, report: Report, *, label: str) -> None:
    """XHTML do spine/nav: XML estrito ideal; HTML tolerante vira aviso.

    Livros reais frequentemente usam ``<meta>``/``<link>`` sem fechamento
    (HTML, nao XHTML estrito); leitores aceitam. So XML quebrado mesmo
    para o parser tolerante e erro.
    """
    data = zf.read(name)
    try:
        etree.fromstring(data)
        return
    except etree.XMLSyntaxError:
        pass
    try:
        html.fromstring(data)
    except (etree.ParserError, etree.XMLSyntaxError) as exc:
        report.issues.append(
            Issue("error", f"{label}: XHTML ilegivel mesmo em modo tolerante ({exc})")
        )
        return
    report.issues.append(
        Issue("warning", f"{label}: XHTML nao estrito (HTML tolerante, como no original)")
    )


def _check_manifest_files(
    zf: zipfile.ZipFile, names: list[str], manifest: dict[str, str], report: Report
) -> None:
    for path in manifest.values():
        if path not in names:
            report.issues.append(Issue("error", f"item do manifest ausente no ZIP: {path}"))


def _check_spine(
    zf: zipfile.ZipFile,
    names: list[str],
    manifest: dict[str, str],
    spine: list[str],
    report: Report,
) -> None:
    if not spine:
        report.issues.append(Issue("error", "spine vazio"))
        return
    for path in spine:
        if path not in names:
            report.issues.append(Issue("error", f"spine referencia arquivo ausente: {path}"))
            continue
        _parse_xhtml(zf, path, report, label=f"spine XHTML ({path})")
