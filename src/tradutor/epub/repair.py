"""Modo reparo: reconstrucao de EPUBs mal formados via ebooklib.

ebooklib e usado APENAS aqui, nunca no caminho feliz: ele reescreve o
livro inteiro e normaliza a estrutura interna — por isso o usuario deve
ser avisado de que a reconstrucao nao preserva os bytes originais.
"""

from __future__ import annotations

from pathlib import Path

from ebooklib import epub

from tradutor.epub.errors import EpubError, MalformedEpubError


def repair_epub(src_path: str | Path, out_path: str | Path) -> Path:
    """Reconstroi ``src_path`` em ``out_path`` como um EPUB valido."""
    src = Path(src_path)
    out = Path(out_path)
    try:
        book = epub.read_epub(str(src), options={"ignore_ncx": True})
    except Exception as exc:
        raise MalformedEpubError(f"nao foi possivel reconstruir o EPUB: {exc}") from exc
    try:
        epub.write_epub(str(out), book)
    except Exception as exc:
        raise EpubError(f"falha ao gravar o EPUB reconstruido: {exc}") from exc
    return out
