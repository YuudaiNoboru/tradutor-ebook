"""Leitura e escrita cirurgica de EPUBs 2 e 3.

API publica: ``open_ebook`` (leitura/validacao/segmentacao),
``write_translated`` (escrita cirurgica), ``repair_epub`` (modo reparo
via ebooklib) e ``output_path_for`` (nome do arquivo de saida).
"""

from tradutor.epub.container import (
    Container,
    Ebook,
    ManifestItem,
    SpineItem,
    open_ebook,
    output_path_for,
)
from tradutor.epub.errors import DrmError, EpubError, MalformedEpubError, NotEpubError
from tradutor.epub.repair import repair_epub
from tradutor.epub.writer import write_translated

__all__ = [
    "Container",
    "DrmError",
    "Ebook",
    "EpubError",
    "MalformedEpubError",
    "ManifestItem",
    "NotEpubError",
    "SpineItem",
    "open_ebook",
    "output_path_for",
    "repair_epub",
    "write_translated",
]
