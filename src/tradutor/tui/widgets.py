"""Componentes e widgets customizados para a TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Footer, Label

from tradutor import __version__


class VersionFooter(Footer):
    """Rodapé personalizado que exibe os atalhos de teclado e a versão ativa do sistema."""

    def compose(self) -> ComposeResult:
        res = super().compose()
        if res is not None:
            yield from res
        lbl = Label(f"v{__version__}", classes="-version-label")
        lbl.styles.dock = "right"
        lbl.styles.padding = (0, 1)
        lbl.styles.color = "gray"
        yield lbl
