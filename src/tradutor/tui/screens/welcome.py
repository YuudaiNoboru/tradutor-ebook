"""Tela de primeira execucao guiada.

Aparece quando nenhuma chave de API esta configurada: apresenta o app e
os dois modos de traducao (LLM com chave propria ou tradutores
automaticos gratuitos), guiando o usuario para configurar a chave ou
continuar sem ela com um provider gratuito.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Static

from tradutor.tui.widgets import VersionFooter


class WelcomeScreen(Screen[None]):
    """Boas-vindas com atalho para configurar a chave ou seguir sem ela."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="welcome"):
            yield Static("LiberLingua", classes="app-title")
            yield Static(
                "Traduza seus EPUBs para o idioma que você escolher, com a sua "
                "própria chave de API (BYOK) ou com tradutores automáticos "
                "gratuitos. O arquivo original nunca é modificado.",
                classes="welcome-text",
            )
            yield Static(
                "Nenhuma chave de API foi encontrada no sistema. Configure a sua "
                "para usar LLMs ou continue sem chave com um tradutor automático "
                "gratuito (experimental).",
                classes="welcome-hint",
            )
            with Horizontal(classes="center-row"):
                yield Button("Configurar agora", id="configure-key", variant="primary")
                yield Button("Continuar sem chave", id="skip-key")
        yield VersionFooter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "configure-key":
            self.app.push_screen("config")
        elif event.button.id == "skip-key":
            self.app.env.config.family = "machine_translation"
            self.app.push_screen("book")
