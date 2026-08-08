"""Tela de progresso (tarefa 9.4).

Barra por bloco, ETA vivo (vazao medida), logs redigidos e cancelamento
ordenado: a traducao roda em worker; cancelar preserva o progresso no
cache e retorna a tela de estimativa com oferta de retomada.
"""

from __future__ import annotations

import time

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Header, ProgressBar, RichLog, Static
from textual.worker import Worker, WorkerState

from tradutor.domain.events import (
    TranslationEvent,
    TranslationLogEvent,
    TranslationProgressEvent,
    TranslationStartedEvent,
)
from tradutor.infra.redact import redact
from tradutor.translate.orchestrator import TranslationCancelled
from tradutor.translate.pipeline import RunResult, run_translation
from tradutor.tui.errors import dump_error_details, friendly_error
from tradutor.tui.screens.error import ErrorScreen
from tradutor.tui.screens.estimate import fmt_seconds
from tradutor.tui.widgets import VersionFooter


class TranslationEventMessage(Message):
    """Wrapper para permitir tráfego de TranslationEvent no barramento de eventos do Textual."""

    def __init__(self, event: TranslationEvent) -> None:
        super().__init__()
        self.event = event


PROGRESS_CSS = """
#progress-view { width: 90; }
#log { height: 14; border: round $panel; margin-top: 1; }
#counter, #eta { height: 1; }
"""


class ProgressScreen(Screen[None]):
    """Traducao em andamento com ETA vivo e cancelamento ordenado."""

    CSS = PROGRESS_CSS
    BINDINGS = [("ctrl+c", "cancel", "Cancelar")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="progress-view"):
            yield Static("Traduzindo...", classes="screen-title")
            yield ProgressBar(id="bar")
            yield Static("0 de 0 blocos", id="counter")
            yield Static("ETA: calculando...", id="eta")
            yield RichLog(id="log", wrap=True, max_lines=50, markup=False)
            yield Button("Cancelar (Ctrl+C)", id="cancel")
        yield VersionFooter()

    def on_mount(self) -> None:
        self._cancel = False
        self._started = time.monotonic()
        key = self.app.chain().get(self.app.key_name_for(self.app.env.config.provider))
        self._secrets = (key,) if key else ()
        self.run_worker(
            self._run,
            name="traducao",
            thread=True,
            exit_on_error=False,
        )

    def _run(self) -> RunResult:
        session = self.app.session
        assert session.ebook is not None
        assert session.work_dir is not None

        def on_event(event: TranslationEvent) -> None:
            self.post_message(TranslationEventMessage(event))

        def cancel_check() -> bool:
            return self._cancel

        return run_translation(
            ebook=session.ebook,
            provider=self.app.build_provider(),
            token_counter=self.app.token_counter(),
            config=self.app.env.config,
            work_dir=session.work_dir,
            book_hash=session.book_hash,
            reset=session.reset,
            on_event=on_event,
            cancel_check=cancel_check,
        )

    @on(TranslationEventMessage)
    def _on_translation_event(self, msg: TranslationEventMessage) -> None:
        event = msg.event
        if isinstance(event, TranslationStartedEvent):
            bar = self.query_one("#bar", ProgressBar)
            bar.update(total=event.total_blocks, progress=0)
            self.query_one("#counter", Static).update(f"0 de {event.total_blocks} blocos")
        elif isinstance(event, TranslationProgressEvent):
            bar = self.query_one("#bar", ProgressBar)
            bar.update(total=event.total, progress=event.done)
            self.query_one("#counter", Static).update(f"{event.done} de {event.total} blocos")
            elapsed = time.monotonic() - self._started
            if event.done > 0 and elapsed > 0:
                rate = event.done / elapsed
                remaining = (event.total - event.done) / rate
                self.query_one("#eta", Static).update(f"ETA: {fmt_seconds(remaining)}")
            else:
                self.query_one("#eta", Static).update("ETA: calculando...")
        elif isinstance(event, TranslationLogEvent):
            self._on_log(event.message)

    def _on_log(self, message: str) -> None:
        self.query_one("#log", RichLog).write(redact(message, self._secrets))

    @on(Worker.StateChanged)
    def _on_worker(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "traducao":
            return
        if event.state is WorkerState.SUCCESS:
            self.app.session.outcome = event.worker.result
            self.app.switch_screen("report")
        elif event.state is WorkerState.ERROR:
            error = event.worker.error or RuntimeError("falha na traducao")
            self._handle_error(error)

    def _handle_error(self, error: Exception) -> None:
        if isinstance(error, TranslationCancelled):
            self.app.get_screen("estimate").set_notice(
                "Traducao cancelada; o progresso concluido ficou salvo para retomada."
            )
            self.app.switch_screen("estimate")
            return
        title, message = friendly_error(error)
        log_path = dump_error_details(error, self._secrets)
        if log_path is not None:
            message = f"{message} Detalhes tecnicos em: {log_path}"
        self.app.push_screen(
            ErrorScreen(title, message),
            callback=lambda _result: self.app.switch_screen("estimate"),
        )

    def action_cancel(self) -> None:
        if self._cancel:
            return
        self._cancel = True
        self.query_one("#cancel", Button).disabled = True
        self._on_log("cancelamento solicitado; encerrando apos o lote atual...")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.action_cancel()
