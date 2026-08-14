"""Componentes e widgets customizados para a TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Footer, Label

from tradutor import __version__


class VersionFooter(Widget):
    """Rodapé personalizado que combina os atalhos de teclado e a versão ativa do sistema."""

    DEFAULT_CSS = """
    VersionFooter {
        layout: horizontal;
        dock: bottom;
        height: 1;
        width: 100%;
        background: $footer-background;
    }
    VersionFooter > Footer {
        dock: none;
        width: 1fr;
        height: 1;
        background: $footer-background;
    }
    VersionFooter > .-version-label {
        dock: none;
        width: auto;
        height: 1;
        margin: 0;
        padding: 0 1;
        background: $footer-background;
        color: $text-muted;
        text-opacity: 85%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Footer(show_command_palette=False)
        yield Label(f"v{__version__}", classes="-version-label")
