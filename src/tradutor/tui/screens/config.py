"""Tela de configuracao (tarefa 9.2).

Provider, chave sempre mascarada (com teste de conexao), idiomas,
politica de termos e paralelismo. Salvar persiste as configuracoes no
arquivo TOML e a chave no cofre do sistema.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static
from textual.worker import Worker, WorkerState

from tradutor.providers import ConnectionResult

POLICY_OPTIONS = [
    ("Traduzir termos", "traduzir"),
    ("Manter originais", "manter"),
    ("Hibrido (1a com original entre parenteses)", "hibrido"),
]

FORM_CSS = """
#config-form { width: 72; }
Label { margin-top: 1; }
#test-result { margin-top: 1; }
"""


class ConfigScreen(Screen[None]):
    """Formulario de configuracao da traducao."""

    CSS = FORM_CSS

    def compose(self) -> ComposeResult:
        config = self.app.env.config
        provider_names = sorted(set(config.providers) | {"deepseek", "openrouter"})
        with Vertical(id="config-form"):
            yield Static("Configuracao", classes="screen-title")
            yield Label("Provider")
            yield Select(
                [(name, name) for name in provider_names],
                prompt="Selecione o provider",
                value=config.provider if config.provider in provider_names else "deepseek",
                id="provider",
            )
            yield Label("Chave da API (mascarada)")
            yield Input(
                placeholder="digite a chave nova (vazia = manter a atual)",
                password=True,
                id="key",
            )
            yield Static(self._key_hint(), classes="form-hint", id="key-hint")
            yield Label("Idioma de origem ('auto' detecta)")
            yield Input(value=config.translation.source, id="source")
            yield Label("Idioma de destino")
            yield Input(value=config.translation.target, id="target")
            yield Label("Politica de termos tecnicos")
            yield Select(POLICY_OPTIONS, value=config.translation.policy, id="policy")
            yield Label("Paralelismo (lotes em simultaneo)")
            yield Input(
                value=str(config.execution.parallelism),
                type="integer",
                id="parallelism",
            )
            yield Static("", id="test-result")
            with Horizontal(classes="center-row"):
                yield Button("Testar conexao", id="test", variant="primary")
                yield Button("Salvar", id="save")
                yield Button("Voltar", id="back")

    def _key_hint(self) -> str:
        if self.app.has_key():
            return "Ja existe uma chave configurada (variavel de ambiente ou cofre)."
        return "Sem chave configurada. Obtenha uma no painel do provider."

    @work(thread=True, name="teste-conexao", exit_on_error=False)
    def _do_test(self, key: str | None) -> ConnectionResult:
        return self.app.build_provider(key_override=key).test_connection()

    @on(Worker.StateChanged)
    def _on_test_done(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "teste-conexao":
            return
        label = self.query_one("#test-result", Static)
        if event.state is WorkerState.SUCCESS:
            result = event.worker.result
            message = result.message
            if result.models:
                message += f": {', '.join(result.models[:3])}"
            label.update(("OK " if result.ok else "FALHA ") + message)
        elif event.state is WorkerState.ERROR:
            error = event.worker.error
            label.update(f"FALHA ao testar: {error}")

    def _typed_key(self) -> str | None:
        value = self.query_one("#key", Input).value.strip()
        return value or None

    def _parallelism(self) -> int | None:
        try:
            value = int(self.query_one("#parallelism", Input).value.strip())
        except ValueError:
            return None
        return value if value >= 1 else None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test":
            self._run_test()
        elif event.button.id == "save":
            self._save()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _run_test(self) -> None:
        label = self.query_one("#test-result", Static)
        label.update("testando conexao...")
        self._do_test(self._typed_key())

    def _save(self) -> None:
        parallelism = self._parallelism()
        if parallelism is None:
            self.notify("Paralelismo deve ser um numero inteiro >= 1", severity="error")
            return
        provider = self.query_one("#provider", Select).value
        key = self._typed_key()
        if key:
            self.app.save_key(key)
        self.app.save_settings(
            provider=str(provider),
            source=self.query_one("#source", Input).value.strip() or "auto",
            target=self.query_one("#target", Input).value.strip() or "pt-BR",
            policy=str(self.query_one("#policy", Select).value),
            parallelism=parallelism,
        )
        self.notify("Configuracao salva")
        self.app.pop_screen()
