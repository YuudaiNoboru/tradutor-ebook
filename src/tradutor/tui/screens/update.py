"""Tela modal para gerenciar downloads e aplicação de atualizações."""

from __future__ import annotations

from typing import Any

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.worker import Worker, WorkerState

UPDATE_CSS = """
#update-dialog {
    width: 62;
    max-width: 90%;
    height: auto;
    border: round $primary;
    background: $panel;
    padding: 1 2;
    align: center middle;
}
.update-title {
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
    text-align: center;
}
.update-text {
    margin-bottom: 2;
    text-align: center;
}
"""


class UpdateModal(ModalScreen[bool]):
    """Modal para aviso, download e reinicialização de atualizações."""

    CSS = UPDATE_CSS
    state = reactive("prompt")  # prompt, downloading, error

    def __init__(
        self, update_info: dict[str, Any], initial_state: str = "prompt", *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.update_info = update_info
        self.state = initial_state

    def compose(self) -> ComposeResult:
        with Vertical(id="update-dialog"):
            yield Static("Atualização Disponível", classes="update-title")
            yield Static("", id="update-message", classes="update-text")
            with Horizontal(classes="center-row", id="update-buttons"):
                yield Button("Baixar e Atualizar", id="download-btn", variant="primary")
                yield Button("Abrir no Navegador", id="browser-btn", variant="primary")
                yield Button("Cancelar", id="cancel-btn")
                yield Button("Fechar", id="close-btn", variant="primary")

    def on_mount(self) -> None:
        self._update_ui()

    def watch_state(self, state: str) -> None:
        self.call_after_refresh(self._update_ui)

    def _update_ui(self) -> None:
        msg = self.query_one("#update-message", Static)
        version = self.update_info.get("version", "")
        is_installed = bool(self.update_info.get("is_installed", False))

        download_btn = self.query_one("#download-btn")
        browser_btn = self.query_one("#browser-btn")
        cancel_btn = self.query_one("#cancel-btn")
        close_btn = self.query_one("#close-btn")

        if self.state == "prompt":
            if is_installed:
                msg.update(
                    f"Uma nova versão ({version}) está disponível no GitHub.\n"
                    "Deseja baixar e executar o instalador oficial agora?"
                )
                download_btn.display = True
                browser_btn.display = False
                cancel_btn.display = True
                close_btn.display = False
            else:
                msg.update(
                    f"Uma nova versão ({version}) está disponível no GitHub.\n"
                    "No modo portátil, baixe a nova versão diretamente pelo navegador."
                )
                download_btn.display = False
                browser_btn.display = True
                cancel_btn.display = False
                close_btn.display = True
        elif self.state == "downloading":
            msg.update(f"Baixando a versão {version}...\nPor favor, aguarde.")
            download_btn.display = False
            browser_btn.display = False
            cancel_btn.display = False
            close_btn.display = False
        elif self.state == "error":
            msg.update("Falha ao baixar a atualização.\nPor favor, tente novamente mais tarde.")
            download_btn.display = False
            browser_btn.display = False
            cancel_btn.display = False
            close_btn.display = True

    @work(thread=True, name="download-update-work", exit_on_error=False)
    def _run_download(self) -> bool:
        from tradutor.infra.updater import download_update

        return download_update(
            self.update_info.get("download_url", ""),
            self.update_info.get("version", ""),
            self.update_info.get("filename", ""),
        )

    @on(Worker.StateChanged)
    def _on_download_state(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "download-update-work":
            return
        if event.state is WorkerState.SUCCESS:
            if event.worker.result:
                from tradutor.infra.updater import (
                    get_installer_path,
                    launch_installer_and_exit,
                )

                filename = self.update_info.get("filename", "")
                installer_path = (
                    get_installer_path(str(filename)) if filename else get_installer_path()
                )
                try:
                    launch_installer_and_exit(installer_path)
                except Exception:
                    self.state = "error"
            else:
                self.state = "error"
        elif event.state is WorkerState.ERROR:
            self.state = "error"

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id in ("cancel-btn", "close-btn"):
            self.dismiss(False)
        elif btn_id == "download-btn":
            self.state = "downloading"
            self._run_download()
        elif btn_id == "browser-btn":
            from tradutor.infra.updater import GITHUB_REPO, open_release_url

            release_url = str(
                self.update_info.get("release_url", "")
                or f"https://github.com/{GITHUB_REPO}/releases"
            )
            open_release_url(release_url)
            self.dismiss(True)
