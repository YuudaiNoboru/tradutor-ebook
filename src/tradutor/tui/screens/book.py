"""Tela de selecao do livro EPUB.

Valida o arquivo em worker (nunca bloqueia a interface) e segue para a
tela de estimativa; erros de leitura (DRM, EPUB invalido, arquivo
inexistente) caem no modal acionavel da tarefa 9.6.
"""

from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static
from textual.worker import Worker, WorkerState

from tradutor.epub.container import Ebook, open_ebook
from tradutor.providers import DEFAULT_KEY_NAME
from tradutor.tui.errors import dump_error_details, friendly_error
from tradutor.tui.runner import book_hash
from tradutor.tui.screens.error import ErrorScreen


class BookScreen(Screen[None]):
    """Entrada do caminho do EPUB a traduzir."""

    def compose(self) -> ComposeResult:
        with Vertical(id="book-form"):
            yield Static("Selecionar livro", classes="screen-title")
            yield Static(
                "Informe o caminho do arquivo EPUB. A traducao gera um novo "
                "arquivo '<livro>-<idioma>.epub' ao lado do original.",
                classes="form-hint",
            )
            yield Input(placeholder="/caminho/para/livro.epub", id="book-path")
            with Horizontal(classes="center-row"):
                yield Button("Abrir livro", id="open", variant="primary")
                yield Button("Configuracao", id="config")
                yield Button("Sair", id="quit")

    @work(thread=True, name="abrir-livro", exit_on_error=False)
    def _open_book(self, path: str) -> Ebook:
        return open_ebook(Path(path))

    @on(Worker.StateChanged)
    def _on_opened(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "abrir-livro":
            return
        if event.state is WorkerState.SUCCESS:
            self._on_success(event.worker.result)
        elif event.state is WorkerState.ERROR:
            error = event.worker.error or RuntimeError("falha ao abrir o livro")
            self._show_error(error)

    def _on_success(self, ebook: Ebook) -> None:
        session = self.app.session
        session.ebook = ebook
        session.book_hash = book_hash(ebook.path)
        session.work_dir = self.app.env.work_dir_for(ebook.path)
        session.notice = ""
        self.app.push_screen("estimate")

    def _show_error(self, error: Exception) -> None:
        title, message = friendly_error(error)
        key = self.app.chain().get(DEFAULT_KEY_NAME)
        log_path = dump_error_details(error, (key,) if key else ())
        if log_path is not None:
            message = f"{message} Detalhes tecnicos em: {log_path}"
        self.app.push_screen(ErrorScreen(title, message))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open":
            path = self.query_one("#book-path", Input).value.strip()
            if not path:
                self.notify("Informe o caminho do arquivo EPUB", severity="error")
                return
            self._open_book(path)
        elif event.button.id == "config":
            self.app.push_screen("config")
        elif event.button.id == "quit":
            self.app.exit()
