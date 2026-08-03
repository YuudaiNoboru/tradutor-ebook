"""Tela de selecao do livro EPUB.

Valida o arquivo em worker (nunca bloqueia a interface) e segue para a
tela de estimativa; erros de leitura (DRM, EPUB invalido, arquivo
inexistente) caem no modal acionavel da tarefa 9.6.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Static
from textual.worker import Worker, WorkerState

from tradutor.epub.container import Ebook, open_ebook
from tradutor.tui.errors import dump_error_details, friendly_error
from tradutor.tui.runner import book_hash
from tradutor.tui.screens.error import ErrorScreen


class EpubDirectoryTree(DirectoryTree):
    """Arvore de diretorios filtrada para mostrar apenas pastas e arquivos EPUB."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.is_dir() or path.suffix.lower() == ".epub"]


BOOK_CSS = """
#book-form {
    width: 80;
    height: 35;
    align: center middle;
}
#book-path {
    height: 20;
    border: tall $primary;
    background: $panel;
    margin-bottom: 1;
}
"""


class BookScreen(Screen[None]):
    """Entrada do caminho do EPUB a traduzir."""

    CSS = BOOK_CSS

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._test_path: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="book-form"):
            yield Static("Selecionar livro", classes="screen-title")
            yield Static(
                "Navegue no diretorio e selecione o arquivo EPUB. A traducao gera um novo "
                "arquivo '<livro>-<idioma>.epub' ao lado do original.",
                classes="form-hint",
            )
            yield EpubDirectoryTree(Path(".").resolve(), id="book-path")
            with Horizontal(classes="center-row"):
                yield Button("Abrir livro", id="open", variant="primary")
                yield Button("Subir pasta", id="go-up")
        yield Footer()

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
        key = self.app.chain().get(self.app.key_name_for(self.app.env.config.provider))
        log_path = dump_error_details(error, (key,) if key else ())
        if log_path is not None:
            message = f"{message} Detalhes tecnicos em: {log_path}"
        self.app.push_screen(ErrorScreen(title, message))

    @on(DirectoryTree.FileSelected)
    def _on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        if event.path.is_file() and event.path.suffix.lower() == ".epub":
            self._open_book(str(event.path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open":
            if self._test_path:
                self._open_book(self._test_path)
                return
            tree = self.query_one("#book-path", EpubDirectoryTree)
            node = tree.cursor_node
            if node is None or node.data is None or not node.data.path.is_file():
                self.notify("Selecione um arquivo EPUB valido", severity="error")
                return
            self._open_book(str(node.data.path))
        elif event.button.id == "go-up":
            tree = self.query_one("#book-path", EpubDirectoryTree)
            tree.path = tree.path.resolve().parent
