"""Tela de primeira execucao guiada (tarefa 9.1).

Aparece quando nenhuma chave de API esta configurada: apresenta o app,
explica o modelo BYOK e guia o usuario para configurar a chave (com
teste de conexao na tela de configuracao) antes de oferecer a traducao.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static


class WelcomeScreen(Screen[None]):
    """Boas-vindas com atalho para configurar a chave ou seguir sem ela."""

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome"):
            yield Static("tradutor-ebook", classes="app-title")
            yield Static(
                "Traduza seus EPUBs para o portugues com a sua propria chave "
                "de API (BYOK). O arquivo original nunca e modificado.",
                classes="welcome-text",
            )
            yield Static(
                "Nenhuma chave de API foi encontrada no sistema. Sem uma chave, "
                "a traducao nao pode ser executada.",
                classes="welcome-hint",
            )
            with Horizontal(classes="center-row"):
                yield Button("Configurar chave agora", id="configure-key", variant="primary")
                yield Button("Continuar sem chave", id="skip-key")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "configure-key":
            self.app.push_screen("config")
        elif event.button.id == "skip-key":
            self.app.push_screen("book")
