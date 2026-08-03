"""Modal de erro acionavel em pt-BR (tarefa 9.6)."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ErrorScreen(ModalScreen[None]):
    """Dialogo com titulo, orientacao acionavel e botao OK."""

    def __init__(
        self,
        title: str,
        message: str,
        *,
        on_ok: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._on_ok = on_ok

    def compose(self) -> ComposeResult:
        with Vertical(id="error-dialog"):
            yield Static(self._title, classes="error-title")
            yield Static(self._message, classes="error-message")
            with Horizontal(classes="center-row"):
                yield Button("Entendi", id="error-ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "error-ok":
            self.dismiss()
            if self._on_ok is not None:
                self._on_ok()
