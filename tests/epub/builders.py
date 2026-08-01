"""Fixtures douradas: livros miniatura EPUB 2 e EPUB 3 deterministicos.

Os livros sao montados com ``zipfile`` com timestamps fixos e ordem de
entradas fixa, garantindo bytes identicos entre execucoes (golden).
"""

from __future__ import annotations

import io
import zipfile

FIXED_DATE = (2020, 1, 2, 3, 4, 6)

CONTAINER_XML = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

CH1 = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter One</title></head>
<body>
<h1>Chapter One</h1>
<p>Hello <b>world</b>! This is the first paragraph.</p>
<p>Inline code: <code>var x = 1;</code> and <code>x + 1</code>.</p>
<pre>def f():
    return 1</pre>
<p>Last line.</p>
</body>
</html>
"""

CH2 = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter Two</title></head>
<body>
<h1>Chapter Two</h1>
<p>Second chapter content.</p>
</body>
</html>
"""

CSS = "body { font-family: serif; }\n"

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

OPF2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="uid">urn:uuid:test-epub2</dc:identifier>
    <dc:title>The English Book</dc:title>
    <dc:language>en</dc:language>
    <dc:date>2020-01-01T00:00:00Z</dc:date>
    <dc:creator>An Author</dc:creator>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="text/ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="text/ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="styles/style.css" media-type="text/css"/>
    <item id="img" href="images/cover.png" media-type="image/png"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>
"""

NCX = """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="urn:uuid:test-epub2"/></head>
  <docTitle><text>The English Book</text></docTitle>
  <navMap>
    <navPoint id="n1" playOrder="1"><navLabel><text>Chapter One</text></navLabel><content src="text/ch1.xhtml"/></navPoint>
    <navPoint id="n2" playOrder="2"><navLabel><text>Chapter Two</text></navLabel><content src="text/ch2.xhtml"/></navPoint>
  </navMap>
</ncx>
"""

OPF3 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:test-epub3</dc:identifier>
    <dc:title>The English Book</dc:title>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ch1" href="text/ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="text/ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="styles/style.css" media-type="text/css"/>
    <item id="img" href="images/cover.png" media-type="image/png"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>
"""

NAV = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Contents</title></head>
<body>
<nav epub:type="toc" id="toc">
  <h1>Contents</h1>
  <ol>
    <li><a href="text/ch1.xhtml">Chapter One</a></li>
    <li><a href="text/ch2.xhtml">Chapter Two</a></li>
  </ol>
</nav>
</body>
</html>
"""


def _zinfo(name: str, compress: int = zipfile.ZIP_DEFLATED) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_DATE)
    info.compress_type = compress
    return info


def build_epub2() -> bytes:
    return _build(
        [
            ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
            ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
            ("OEBPS/content.opf", OPF2.encode("utf-8")),
            ("OEBPS/toc.ncx", NCX.encode("utf-8")),
            ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
            ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
            ("OEBPS/styles/style.css", CSS.encode("utf-8")),
            ("OEBPS/images/cover.png", PNG),
        ]
    )


def build_epub3() -> bytes:
    return _build(
        [
            ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
            ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
            ("OEBPS/content.opf", OPF3.encode("utf-8")),
            ("OEBPS/nav.xhtml", NAV.encode("utf-8")),
            ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
            ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
            ("OEBPS/styles/style.css", CSS.encode("utf-8")),
            ("OEBPS/images/cover.png", PNG),
        ]
    )


def build_epub3_with_ncx() -> bytes:
    return _build(
        [
            ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
            ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
            ("OEBPS/content.opf", OPF3_NCX.encode("utf-8")),
            ("OEBPS/nav.xhtml", NAV.encode("utf-8")),
            ("OEBPS/toc.ncx", NCX.encode("utf-8")),
            ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
            ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
            ("OEBPS/styles/style.css", CSS.encode("utf-8")),
            ("OEBPS/images/cover.png", PNG),
        ]
    )


def build_drm_book() -> bytes:
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("META-INF/encryption.xml", ENCRYPTION.encode("utf-8")),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def build_mimetype_not_first() -> bytes:
    entries = [
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_mimetype_compressed() -> bytes:
    entries = [
        ("mimetype", b"application/epub+zip"),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_missing_container_xml() -> bytes:
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def build_not_a_zip() -> bytes:
    return b"isto nao e um epub"


def build_corrupt_zip() -> bytes:
    return b"PK\x03\x04" + b"\x00" * 64


def build_wrong_mimetype_content() -> bytes:
    entries = [
        ("mimetype", b"application/xhtml+xml", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_epub2_without_toc() -> bytes:
    opf = OPF2.replace(
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n', ""
    )
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_invalid_container_xml() -> bytes:
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", b"isto nao e xml"),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def build_container_without_rootfile() -> bytes:
    container = '<?xml version="1.0"?>\n<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"/>'
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", container.encode("utf-8")),
        ("OEBPS/content.opf", OPF2.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def build_opf_missing() -> bytes:
    container = CONTAINER_XML.replace("OEBPS/content.opf", "OEBPS/nao-existe.opf")
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", container.encode("utf-8")),
    ]
    return _build(entries)


def build_corrupt_opf() -> bytes:
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", b"<package>"),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def build_spine_with_extra_items() -> bytes:
    opf = OPF2.replace(
        '  <spine toc="ncx">\n    <itemref idref="ch1"/>\n',
        '  <spine toc="ncx">\n    <itemref idref="img2"/>\n    <itemref idref="ghost"/>\n    <itemref idref="ch1"/>\n',
    )
    opf = opf.replace(
        '    <item id="img" href="images/cover.png" media-type="image/png"/>\n',
        '    <item id="img" href="images/cover.png" media-type="image/png"/>\n'
        '    <item id="img2" href="images/cover.png" media-type="image/png"/>\n',
    )
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_duplicate_spine() -> bytes:
    opf = OPF2.replace(
        '    <itemref idref="ch1"/>\n',
        '    <itemref idref="ch1"/>\n    <itemref idref="ch1"/>\n',
    )
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_epub3_missing_nav_file() -> bytes:
    opf = OPF3.replace('href="nav.xhtml"', 'href="missing.xhtml"')
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_epub3_missing_ncx_file() -> bytes:
    opf = OPF3_NCX.replace('href="toc.ncx"', 'href="missing.ncx"')
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/nav.xhtml", NAV.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_opf_with_extra_meta() -> bytes:
    opf = OPF3.replace(
        '    <meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>\n',
        '    <meta property="rendition:layout">reflowable</meta>\n'
        '    <meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>\n',
    )
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/nav.xhtml", NAV.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
        ("OEBPS/styles/style.css", CSS.encode("utf-8")),
        ("OEBPS/images/cover.png", PNG),
    ]
    return _build(entries)


def build_opf_without_title_language() -> bytes:
    opf = OPF2.replace("    <dc:title>The English Book</dc:title>\n", "")
    opf = opf.replace("    <dc:language>en</dc:language>\n", "")
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", opf.encode("utf-8")),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def build_bzip2_opf() -> bytes:
    entries = [
        ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
        ("META-INF/container.xml", CONTAINER_XML.encode("utf-8")),
        ("OEBPS/content.opf", OPF2.encode("utf-8"), zipfile.ZIP_BZIP2),
        ("OEBPS/toc.ncx", NCX.encode("utf-8")),
        ("OEBPS/text/ch1.xhtml", CH1.encode("utf-8")),
        ("OEBPS/text/ch2.xhtml", CH2.encode("utf-8")),
    ]
    return _build(entries)


def patch_entry_flags(book: bytes, name: str, flags: int) -> bytes:
    """Seta os flag bits de uma entrada (local + central) e devolve os bytes."""
    with zipfile.ZipFile(io.BytesIO(book)) as zf:
        infos = zf.infolist()
    index = next(i for i, info in enumerate(infos) if info.filename == name)
    data = bytearray(book)
    offset = infos[index].header_offset
    data[offset + 6 : offset + 8] = flags.to_bytes(2, "little")
    cd = _cd_offsets(book)[index]
    data[cd + 8 : cd + 10] = flags.to_bytes(2, "little")
    return bytes(data)


def patch_entry_csize(book: bytes, name: str, delta: int) -> bytes:
    """Infla o tamanho comprimido declarado de uma entrada no diretorio central."""
    with zipfile.ZipFile(io.BytesIO(book)) as zf:
        infos = zf.infolist()
    index = next(i for i, info in enumerate(infos) if info.filename == name)
    data = bytearray(book)
    cd = _cd_offsets(book)[index]
    csize = int.from_bytes(data[cd + 20 : cd + 24], "little") + delta
    data[cd + 20 : cd + 24] = csize.to_bytes(4, "little")
    return bytes(data)


def _cd_offsets(book: bytes) -> list[int]:
    with zipfile.ZipFile(io.BytesIO(book)) as zf:
        infos = zf.infolist()
    pos = 0
    for info in infos:
        pos = info.header_offset + 30 + len(info.filename) + len(info.extra) + info.compress_size
    offsets: list[int] = []
    while book[pos : pos + 4] == b"PK\x01\x02":
        offsets.append(pos)
        nlen = int.from_bytes(book[pos + 28 : pos + 30], "little")
        elen = int.from_bytes(book[pos + 30 : pos + 32], "little")
        clen = int.from_bytes(book[pos + 32 : pos + 34], "little")
        pos += 46 + nlen + elen + clen
    return offsets


def _build(entries: list[tuple[str, bytes, int | None] | tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for entry in entries:
            if len(entry) == 2:
                name, data = entry
                compress = zipfile.ZIP_DEFLATED
            else:
                name, data, compress = entry
            zf.writestr(_zinfo(name, compress), data)
    return buf.getvalue()


OPF3_NCX = OPF3.replace(
    '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n',
    '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
    '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n',
)

ENCRYPTION = """<?xml version="1.0" encoding="utf-8"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:enc="http://www.w3.org/2001/04/xmlenc#">
  <enc:EncryptedData><enc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/></enc:EncryptedData>
</encryption>
"""
