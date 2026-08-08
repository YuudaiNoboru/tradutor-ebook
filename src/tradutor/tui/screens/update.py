"""Tela modal para gerenciar downloads e aplicação de atualizações."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.worker import Worker, WorkerState

UPDATE_CSS = """
#update-dialog {
    width: 60;
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
    state = reactive("prompt")  # prompt, downloading, downloaded, error

    def __init__(self, update_info: dict[str, str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.update_info = update_info

    def compose(self) -> ComposeResult:
        with Vertical(id="update-dialog"):
            yield Static("Atualização Disponível", classes="update-title")
            yield Static("", id="update-message", classes="update-text")
            with Horizontal(classes="center-row", id="update-buttons"):
                yield Button("Baixar", id="download-btn", variant="primary")
                yield Button("Cancelar", id="cancel-btn")
                yield Button("Reiniciar", id="restart-btn", variant="primary")
                yield Button("Mais tarde", id="later-btn")
                yield Button("Fechar", id="close-btn", variant="primary")

    def watch_state(self, state: str) -> None:
        self.call_after_refresh(self._update_ui)

    def _update_ui(self) -> None:
        msg = self.query_one("#update-message", Static)
        version = self.update_info["version"]

        download_btn = self.query_one("#download-btn")
        cancel_btn = self.query_one("#cancel-btn")
        restart_btn = self.query_one("#restart-btn")
        later_btn = self.query_one("#later-btn")
        close_btn = self.query_one("#close-btn")

        if self.state == "prompt":
            msg.update(
                f"Uma nova versão ({version}) está disponível no GitHub.\n"
                "Deseja realizar o download em segundo plano?"
            )
            download_btn.display = True
            cancel_btn.display = True
            restart_btn.display = False
            later_btn.display = False
            close_btn.display = False
        elif self.state == "downloading":
            msg.update(f"Baixando a versão {version}...\nPor favor, aguarde.")
            download_btn.display = False
            cancel_btn.display = False
            restart_btn.display = False
            later_btn.display = False
            close_btn.display = False
        elif self.state == "downloaded":
            msg.update(
                "Download concluído com sucesso!\n"
                "Deseja reiniciar a aplicação para aplicar a atualização agora?"
            )
            download_btn.display = False
            cancel_btn.display = False
            restart_btn.display = True
            later_btn.display = True
            close_btn.display = False
        elif self.state == "error":
            msg.update("Falha ao baixar a atualização.\nPor favor, tente novamente mais tarde.")
            download_btn.display = False
            cancel_btn.display = False
            restart_btn.display = False
            later_btn.display = False
            close_btn.display = True

    @work(thread=True, name="download-update-work", exit_on_error=False)
    def _run_download(self) -> bool:
        from tradutor.infra.updater import download_update

        return download_update(
            self.update_info["download_url"],
            self.update_info["version"],
            self.update_info["filename"],
        )

    @on(Worker.StateChanged)
    def _on_download_state(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "download-update-work":
            return
        if event.state is WorkerState.SUCCESS:
            if event.worker.result:
                self.state = "downloaded"
            else:
                self.state = "error"
        elif event.state is WorkerState.ERROR:
            self.state = "error"

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "cancel-btn" or btn_id == "later-btn" or btn_id == "close-btn":
            self.dismiss(False)
        elif btn_id == "download-btn":
            self.state = "downloading"
            self._run_download()
        elif btn_id == "restart-btn":
            from tradutor.infra.updater import (
                get_pending_update_paths,
                is_frozen_windows,
                run_helper_and_exit,
            )

            if not is_frozen_windows():
                self.notify(
                    "A reinicialização automática só é suportada no executável Windows compilado.",
                    severity="warning",
                )
                self.dismiss(False)
                return

            pending_exe, pending_json = get_pending_update_paths()
            run_helper_and_exit(pending_exe, pending_json)
